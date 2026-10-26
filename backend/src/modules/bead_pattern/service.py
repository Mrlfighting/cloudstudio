"""有界同源取图服务：仅访问配置中的 COS 图片，不缓存或修改原图。"""

import asyncio
from io import BytesIO
from urllib.parse import unquote, urlsplit

import httpx
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 25_000_000
FORMAT_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif"}


def validate_source_url(url: str, base_url: str) -> None:
    """校验精确来源与图片路径，拒绝任意 URL、凭据、重定向和路径穿越。"""
    try:
        source, base = urlsplit(url), urlsplit(base_url)
        prefix = base.path.rstrip("/") + "/pictures/"
        path = unquote(source.path)
        valid = (
            source.scheme == base.scheme == "https"
            and source.hostname == base.hostname
            and source.port in (None, 443)
            and base.port in (None, 443)
            and not source.username
            and not source.password
            and not source.query
            and not source.fragment
            and path.startswith(prefix)
            and ".." not in path.split("/")
            and "\\" not in path
        )
    except ValueError:
        valid = False
    if not valid:
        raise HTTPException(422, "图片来源不受信任，请重新上传本地图片")


def inspect_image(data: bytes) -> str:
    """以真实文件内容校验格式、像素数和完整性，不依赖上游 MIME。"""
    try:
        with Image.open(BytesIO(data)) as image:
            mime = FORMAT_MIME.get(image.format or "")
            if mime is None:
                raise HTTPException(415, "仅支持 JPEG、PNG、WebP 和 GIF")
            if image.width * image.height > MAX_PIXELS:
                raise HTTPException(413, "图片超过 2500 万像素，请先缩小")
            image.verify()
            return mime
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(415, "图片文件无效或已损坏") from error


class BeadSourceService:
    """仅负责下载已通过归属校验的图片，传输实现可注入以便测试。"""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """默认使用真实 HTTPS，测试使用内存传输。"""
        self.transport = transport

    async def read(self, url: str, base_url: str) -> tuple[bytes, str]:
        """在总超时和字节上限内读取并验证图片。"""
        validate_source_url(url, base_url)
        try:
            async with asyncio.timeout(15):
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(10, connect=5), follow_redirects=False,
                    transport=self.transport, trust_env=False,
                ) as client:
                    async with client.stream("GET", url) as response:
                        if response.status_code != 200:
                            raise HTTPException(502, "原图暂时无法读取，请重试或使用本地图片")
                        length = response.headers.get("content-length")
                        if length and length.isdigit() and int(length) > MAX_BYTES:
                            raise HTTPException(413, "图片不能超过 10MB")
                        data = bytearray()
                        async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                            if len(data) + len(chunk) > MAX_BYTES:
                                raise HTTPException(413, "图片不能超过 10MB")
                            data.extend(chunk)
            content = bytes(data)
            mime = await run_in_threadpool(inspect_image, content)
            return content, mime
        except (TimeoutError, httpx.TimeoutException) as error:
            raise HTTPException(504, "读取原图超时，请稍后重试") from error
        except httpx.HTTPError as error:
            raise HTTPException(502, "原图下载失败，请稍后重试") from error
