"""图库上传的有界读取与解码，避免大文件和压缩图片阻塞事件循环。"""

import asyncio
import warnings
from dataclasses import dataclass
from io import BytesIO
from weakref import WeakKeyDictionary

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from ..modules.common.exceptions import ValidationError

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_PIXELS = 25_000_000
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}
CONTENT_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif"}
_decode_slots: WeakKeyDictionary = WeakKeyDictionary()


@dataclass
class UploadImage:
    """保留真实元数据与小尺寸主色调工作图，不跨请求持有完整解码缓冲。"""

    data: bytes
    width: int
    height: int
    format: str
    mode: str
    preview: Image.Image


def _decode(data: bytes) -> UploadImage:
    """先限制格式和像素，再校验完整性并只解码静态首帧。"""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data), formats=list(ALLOWED_FORMATS)) as image:
                width, height = image.size
                if width * height > MAX_PIXELS:
                    raise ValidationError("图片像素不能超过 2500 万")
                image.verify()
            with Image.open(BytesIO(data), formats=list(ALLOWED_FORMATS)) as image:
                image.load()
                image_format, mode = str(image.format), image.mode
                image.thumbnail((256, 256))
                preview = image.copy()
        return UploadImage(data, width, height, image_format, mode, preview)
    except ValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValidationError("无法解析该图片，仅支持完整的 JPEG/PNG/WebP/GIF，且不超过 2500 万像素") from exc


async def read_upload_image(file: UploadFile) -> UploadImage:
    """多读一字节识别超限；每个事件循环最多并发解码两张图片。"""
    data = await file.read(MAX_FILE_SIZE + 1)
    if not data:
        raise ValidationError("图片文件为空")
    if len(data) > MAX_FILE_SIZE:
        raise ValidationError("图片大小不能超过 10MB")
    loop = asyncio.get_running_loop()
    limiter = _decode_slots.setdefault(loop, asyncio.Semaphore(2))
    async with limiter:
        return await run_in_threadpool(_decode, data)
