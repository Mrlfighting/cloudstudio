"""图片协同编辑门面：房间管理器 / Redis 锁 / RabbitMQ broker 的惰性单例。"""

import threading

import redis.asyncio as aioredis

from ..config.settings import get_settings
from .broker import CollabBroker
from .lock import CollabLock
from .manager import RoomManager

_manager: RoomManager | None = None
_lock: CollabLock | None = None
_broker: CollabBroker | None = None
_build_lock = threading.Lock()


def get_collab_manager() -> RoomManager:
    """获取房间管理器单例（惰性构建，幂等）。"""
    global _manager
    if _manager is None:
        with _build_lock:
            if _manager is None:
                _manager = RoomManager()
    return _manager


def get_collab_lock() -> CollabLock | None:
    """获取 Redis 编辑锁单例；未启用返回 None。"""
    global _lock
    if _lock is None:
        settings = get_settings()
        if not settings.IMAGE_COLLAB_ENABLED:
            return None
        with _build_lock:
            if _lock is None:
                redis = aioredis.Redis(
                    host=settings.CACHE_REDIS_HOST,
                    port=settings.CACHE_REDIS_PORT,
                    db=settings.CACHE_REDIS_DB,
                    password=settings.CACHE_REDIS_PASSWORD,
                    decode_responses=True,
                )
                _lock = CollabLock(redis=redis, ttl=settings.COLLAB_LOCK_TTL)
    return _lock


def get_collab_broker() -> CollabBroker | None:
    """获取 RabbitMQ broker 单例（未连接）；未启用返回 None。"""
    global _broker
    if _broker is None:
        settings = get_settings()
        if not settings.IMAGE_COLLAB_ENABLED:
            return None
        with _build_lock:
            if _broker is None:
                _broker = CollabBroker(url=settings.COLLAB_RABBITMQ_URL)
    return _broker


def set_collab_manager(manager: RoomManager | None) -> None:
    global _manager
    _manager = manager


def set_collab_lock(lock: CollabLock | None) -> None:
    global _lock
    _lock = lock


def set_collab_broker(broker: CollabBroker | None) -> None:
    global _broker
    _broker = broker
