"""TwoLevelCacheManager 单元测试。"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.cache.backends.memory import MemoryBackend
from src.infrastructure.cache.two_level import TwoLevelCacheManager


def make_manager(local: MemoryBackend | None = None, redis=None, **kwargs) -> TwoLevelCacheManager:
    local = local or MemoryBackend(maxsize=100, ttl=60)
    redis = redis or AsyncMock()
    return TwoLevelCacheManager(local=local, redis=redis, **kwargs)


# --------------------------------------------------------------------------- 读写

@pytest.mark.asyncio
async def test_local_hit_skips_redis():
    redis = AsyncMock()
    local = MemoryBackend()
    await local.set("k", "from_local", 60)
    manager = make_manager(local=local, redis=redis)
    assert await manager.get("k") == "from_local"
    redis.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_redis_hit_backfills_local():
    local = MemoryBackend()
    redis = AsyncMock()
    redis.get = AsyncMock(return_value="from_redis")
    manager = make_manager(local=local, redis=redis)
    assert await manager.get("k") == "from_redis"
    assert await local.get("k") == "from_redis"


@pytest.mark.asyncio
async def test_full_miss_returns_none():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    manager = make_manager(redis=redis)
    assert await manager.get("k") is None


@pytest.mark.asyncio
async def test_get_or_load_uses_loader_on_miss():
    local = MemoryBackend()
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    manager = make_manager(local=local, redis=redis)

    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        return {"data": []}

    value = await manager.get_or_load("k", loader, 300)
    assert value == {"data": []}
    assert calls == 1
    # 回填到 L1
    assert await local.get("k") == {"data": []}


@pytest.mark.asyncio
async def test_get_or_load_single_flight_anti_stampede():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    manager = make_manager(redis=redis)

    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return "v"

    results = await asyncio.gather(*(manager.get_or_load("k", loader, 300) for _ in range(10)))
    assert all(r == "v" for r in results)
    # 防击穿：并发同 key 只回源一次
    assert calls == 1


@pytest.mark.asyncio
async def test_put_serializes_datetime_for_redis():
    """写 L2 前应把 datetime 转成 JSON 兼容值（回归：Object of type datetime is not JSON serializable）。"""
    local = MemoryBackend()
    redis = AsyncMock()
    manager = make_manager(local=local, redis=redis)
    await manager.put("k", {"created_at": datetime(2026, 1, 1, 12, 0, 0)}, 300)
    # redis.set 收到的值必须能被 json.dumps 序列化（datetime 已被转成 ISO 字符串）
    called_value = redis.set.await_args.args[1]
    json.dumps(called_value)


@pytest.mark.asyncio
async def test_evict_clears_both_levels():
    local = MemoryBackend()
    redis = AsyncMock()
    manager = make_manager(local=local, redis=redis)
    await local.set("k", "v", 60)
    await manager.evict("k")
    assert await local.get("k") is None
    redis.delete.assert_awaited_once_with("k")


@pytest.mark.asyncio
async def test_invalidate_by_prefix():
    local = MemoryBackend()
    redis = AsyncMock()
    manager = make_manager(local=local, redis=redis)
    await local.set("pic:list:a", 1, 60)
    await local.set("pic:detail:1", 2, 60)
    await manager.invalidate_by_prefix("pic:list:")
    assert await local.get("pic:list:a") is None
    assert await local.get("pic:detail:1") == 2
    redis.delete_pattern.assert_awaited_once_with("pic:list:")


# --------------------------------------------------------------------------- 降级

@pytest.mark.asyncio
async def test_redis_down_degrades_to_loader():
    local = MemoryBackend()
    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=ConnectionError("down"))
    redis.set = AsyncMock(side_effect=ConnectionError("down"))
    manager = make_manager(local=local, redis=redis)

    # get 降级返回 None（不抛异常）
    assert await manager.get("k") is None

    # get_or_load 走 loader 并回填 L1
    async def loader():
        return "loaded"

    assert await manager.get_or_load("k", loader, 300) == "loaded"
    assert await local.get("k") == "loaded"


# --------------------------------------------------------------------------- 命中率统计

@pytest.mark.asyncio
async def test_stats_counts():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    manager = make_manager(redis=redis)
    await manager.get("k")
    stats = manager.stats()
    assert stats["local"]["miss"] == 1
    assert stats["redis"]["miss"] == 1
    assert stats["local"]["hit_rate"] == 0.0


# --------------------------------------------------------------------------- 热key探测

def make_hot_manager() -> tuple[TwoLevelCacheManager, MemoryBackend, MagicMock]:
    local = MemoryBackend()
    redis = AsyncMock()
    client = MagicMock()
    pipe = MagicMock()
    client.pipeline.return_value = pipe
    pipe.incr.return_value = pipe
    pipe.expire.return_value = pipe
    pipe.execute = AsyncMock(return_value=[5, True])
    redis.client = client
    manager = TwoLevelCacheManager(local=local, redis=redis, hot_key_threshold=10, hot_key_window=60)
    return manager, local, client


@pytest.mark.asyncio
async def test_record_access_returns_count():
    manager, _, _ = make_hot_manager()
    count = await manager.record_access("pic:detail:1")
    assert count == 5


@pytest.mark.asyncio
async def test_promote_to_local():
    manager, local, _ = make_hot_manager()
    manager._redis.get = AsyncMock(return_value="detail")  # noqa: SLF001
    await manager.promote_to_local("pic:detail:1")
    assert await local.get("pic:detail:1") == "detail"


@pytest.mark.asyncio
async def test_is_hot_key_threshold():
    manager, _, client = make_hot_manager()
    client.get = AsyncMock(return_value=b"12")  # >= 阈值 10
    assert await manager.is_hot_key("pic:detail:1") is True
    client.get = AsyncMock(return_value=b"3")
    assert await manager.is_hot_key("pic:detail:1") is False
