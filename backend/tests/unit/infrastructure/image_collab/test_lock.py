"""Redis 分布式编辑锁单元测试（mock redis）。"""

from unittest.mock import AsyncMock

import pytest

from src.infrastructure.image_collab import CollabLock


@pytest.fixture
def lock() -> CollabLock:
    return CollabLock(redis=AsyncMock(), ttl=30)


@pytest.mark.asyncio
async def test_try_acquire_success(lock: CollabLock):
    lock._redis.get.return_value = None
    lock._redis.set.return_value = True
    assert await lock.try_acquire(1, 1, 100) is True


@pytest.mark.asyncio
async def test_try_acquire_conflict(lock: CollabLock):
    lock._redis.get.return_value = "200"
    lock._redis.set.return_value = None  # SET NX 未设置（键已存在）
    assert await lock.try_acquire(1, 1, 100) is False


@pytest.mark.asyncio
async def test_try_acquire_idempotent(lock: CollabLock):
    """已是持有者：刷新 TTL 并返回 True。"""
    lock._redis.get.return_value = "100"
    assert await lock.try_acquire(1, 1, 100) is True
    lock._redis.expire.assert_awaited_once()


@pytest.mark.asyncio
async def test_release(lock: CollabLock):
    lock._redis.eval.return_value = 1
    assert await lock.release(1, 1, 100) is True


@pytest.mark.asyncio
async def test_get_holder(lock: CollabLock):
    lock._redis.get.return_value = "100"
    assert await lock.get_holder(1, 1) == 100


@pytest.mark.asyncio
async def test_memory_fallback(lock: CollabLock):
    """Redis 异常时回退内存锁，语义与 Redis 一致（获取/查询/释放都正确）。"""
    lock._redis.get.side_effect = Exception("redis down")
    lock._redis.set.side_effect = Exception("redis down")
    lock._redis.eval.side_effect = Exception("redis down")
    assert await lock.try_acquire(1, 1, 100) is True
    assert await lock.get_holder(1, 1) == 100
    assert await lock.release(1, 1, 100) is True
    assert await lock.get_holder(1, 1) is None
