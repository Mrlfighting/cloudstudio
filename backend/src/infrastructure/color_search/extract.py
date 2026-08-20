"""主色调提取：CI imageAve 优先，失败降级 Pillow 本地平均色。"""

import httpx
from PIL import Image

from ..config.settings import settings
from ..logging import get_logger

logger = get_logger()

# CI imageAve 请求超时（秒）
_IMAGE_AVE_TIMEOUT = 10.0


def extract_primary_color(key: str, img: Image.Image | None) -> int | None:
    """提取图片主色调，返回 0xRRGGBB 整数；全部失败返回 None。

    1. 优先调腾讯云数据万象 imageAve（`GET <key>?imageAve` → `{"RGB":"0x736246"}`）；
    2. 失败降级 Pillow 本地平均色；
    3. 再失败返回 None（颜色搜索时排除该图）。
    """
    color = _extract_via_ci(key)
    if color is not None:
        return color

    color = _extract_via_pillow(img)
    if color is not None:
        return color
    return None


def _extract_via_ci(key: str) -> int | None:
    """调数据万象 imageAve 获取主色调（同步，需调用方放入线程池）。"""
    try:
        url = f"{settings.COS_BASE_URL}/{key}?imageAve"
        resp = httpx.get(url, timeout=_IMAGE_AVE_TIMEOUT)
        resp.raise_for_status()
        rgb_hex = resp.json().get("RGB")
        if rgb_hex:
            return int(rgb_hex, 16)
        return None
    except Exception as e:
        logger.warning(
            f"CI imageAve 提取主色调失败，降级 Pillow: {e}",
            extra={"reason": "ci_imageave_failed"},
        )
        return None


def _extract_via_pillow(img: Image.Image | None) -> int | None:
    """Pillow 本地计算平均色（resize 到 1x1 取像素）。"""
    if img is None:
        return None
    try:
        pixel = img.convert("RGB").resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
        if isinstance(pixel, tuple) and len(pixel) >= 3:
            r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
            return (r << 16) | (g << 8) | b
        return None
    except Exception as e:
        logger.warning(
            f"Pillow 提取主色调失败: {e}", extra={"reason": "pillow_color_failed"}
        )
        return None
