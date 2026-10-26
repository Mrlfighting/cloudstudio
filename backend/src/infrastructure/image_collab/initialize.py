"""图片协同编辑的初始化与关闭（接入应用 lifespan）。"""

from ...infrastructure.logging import get_logger
from .facade import (
    get_collab_broker,
    get_collab_lock,
    get_collab_manager,
    set_collab_broker,
    set_collab_lock,
    set_collab_manager,
)

logger = get_logger()


async def initialize_image_collab() -> None:
    """预连接 RabbitMQ；失败时暂停协同，后续 WebSocket 连接会重试。"""
    broker = get_collab_broker()
    if broker is None:
        return
    try:
        await broker.connect()
    except Exception:
        logger.warning("RabbitMQ 连接失败，图片协同编辑暂不可用，后续连接将重试")


async def close_image_collab() -> None:
    """关闭 broker / 锁，清空房间并重置单例。"""
    manager = get_collab_manager()
    await manager.close_all()

    broker = get_collab_broker()
    if broker is not None:
        await broker.close()

    lock = get_collab_lock()
    if lock is not None:
        await lock.close()

    set_collab_manager(None)
    set_collab_broker(None)
    set_collab_lock(None)
