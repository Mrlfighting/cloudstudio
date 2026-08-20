"""以图搜图门面的初始化与关闭（可选接入应用 lifespan）。"""

from .facade import ImageSearchFacade, get_image_search_facade, set_image_search_facade


def initialize_image_search() -> ImageSearchFacade | None:
    """显式构建门面（等价于惰性构建），供应用启动阶段调用；总开关关闭返回 None。

    也可不调用本函数，直接依赖 ``get_image_search_facade()`` 的惰性构建。
    """
    return get_image_search_facade()


async def close_image_search() -> None:
    """关闭门面（释放 httpx 连接池）并清空单例。"""
    facade = get_image_search_facade()
    if facade is not None:
        await facade.close()
    set_image_search_facade(None)
