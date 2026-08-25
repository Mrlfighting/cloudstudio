"""图像画面扩展（扩图）门面的初始化与关闭（接入应用 lifespan）。"""

from .facade import (
    ImageOutpaintingFacade,
    get_image_outpainting_facade,
    set_image_outpainting_facade,
)


def initialize_image_outpainting() -> ImageOutpaintingFacade | None:
    """显式构建门面（等价于惰性构建），供应用启动阶段调用；未启用返回 None。"""
    return get_image_outpainting_facade()


async def close_image_outpainting() -> None:
    """关闭门面（释放 httpx 连接池）并清空单例。"""
    facade = get_image_outpainting_facade()
    if facade is not None:
        await facade.close()
    set_image_outpainting_facade(None)
