"""图像画面扩展（扩图）门面：单例 + 便捷入口。"""

import threading

from ..config.settings import get_settings
from .client import BailianOutpaintingClient
from .models import CreateTaskResponse, OutpaintingParameters, QueryTaskResponse


class ImageOutpaintingFacade:
    """扩图门面：封装百炼客户端，对外暴露 create_task / query_task。"""

    def __init__(self, client: BailianOutpaintingClient) -> None:
        self._client = client

    async def create_task(
        self, image_url: str, parameters: OutpaintingParameters
    ) -> CreateTaskResponse:
        """创建扩图任务（失败抛 ImageOutpaintingException）。"""
        return await self._client.create_task(image_url, parameters)

    async def query_task(self, task_id: str) -> QueryTaskResponse:
        """查询扩图任务（失败抛 ImageOutpaintingException）。"""
        return await self._client.query_task(task_id)

    async def close(self) -> None:
        """关闭底层 httpx 连接池。"""
        await self._client.close()


# 模块级单例（惰性构建）
_facade: ImageOutpaintingFacade | None = None
_build_lock = threading.Lock()


def get_image_outpainting_facade() -> ImageOutpaintingFacade | None:
    """获取门面单例；未初始化时惰性构建（幂等），未启用/未配置返回 None。"""
    global _facade
    facade = _facade
    if facade is not None:
        return facade

    settings = get_settings()
    if not settings.IMAGE_OUTPAINTING_ENABLED:
        return None
    if not settings.IMAGE_OUTPAINTING_API_KEY or not settings.IMAGE_OUTPAINTING_WORKSPACE_ID:
        return None

    with _build_lock:
        facade = _facade
        if facade is None:
            client = BailianOutpaintingClient(
                base_url=settings.IMAGE_OUTPAINTING_BASE_URL,
                api_key=settings.IMAGE_OUTPAINTING_API_KEY,
                timeout=settings.IMAGE_OUTPAINTING_TIMEOUT,
                max_retries=settings.IMAGE_OUTPAINTING_RETRY,
            )
            facade = ImageOutpaintingFacade(client=client)
            _facade = facade
    return facade


def set_image_outpainting_facade(facade: ImageOutpaintingFacade | None) -> None:
    """设置 / 清空门面单例（测试注入用）。"""
    global _facade
    _facade = facade


async def create_outpainting_task(
    image_url: str, parameters: OutpaintingParameters
) -> CreateTaskResponse | None:
    """门面级便捷入口：未启用/未配置返回 None，否则创建任务（失败抛异常）。"""
    facade = get_image_outpainting_facade()
    if facade is None:
        return None
    return await facade.create_task(image_url, parameters)


async def query_outpainting_task(task_id: str) -> QueryTaskResponse | None:
    """门面级便捷入口：未启用/未配置返回 None，否则查询任务（失败抛异常）。"""
    facade = get_image_outpainting_facade()
    if facade is None:
        return None
    return await facade.query_task(task_id)
