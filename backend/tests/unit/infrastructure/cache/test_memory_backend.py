"""MemoryBackend 单元测试。"""

import pytest

from src.infrastructure.cache.backends.memory import MemoryBackend


@pytest.mark.asyncio
async def test_set_get_delete():
    backend = MemoryBackend(maxsize=10, ttl=60)
    await backend.set("k", {"a": 1}, 60)
    assert await backend.get("k") == {"a": 1}
    await backend.delete("k")
    assert await backend.get("k") is None


@pytest.mark.asyncio
async def test_exists():
    backend = MemoryBackend()
    await backend.set("k", "v", 60)
    assert await backend.exists("k") is True
    assert await backend.exists("missing") is False


@pytest.mark.asyncio
async def test_delete_pattern_prefix_match():
    backend = MemoryBackend()
    await backend.set("pic:list:a", 1, 60)
    await backend.set("pic:list:b", 2, 60)
    await backend.set("pic:detail:1", 3, 60)
    await backend.delete_pattern("pic:list:")
    assert await backend.get("pic:list:a") is None
    assert await backend.get("pic:list:b") is None
    # 非前缀命中项不受影响
    assert await backend.get("pic:detail:1") == 3


@pytest.mark.asyncio
async def test_clear_and_ping():
    backend = MemoryBackend()
    await backend.set("k", "v", 60)
    await backend.clear()
    assert await backend.get("k") is None
    assert await backend.ping() is True


@pytest.mark.asyncio
async def test_maxsize_eviction():
    backend = MemoryBackend(maxsize=2, ttl=60)
    await backend.set("a", 1, 60)
    await backend.set("b", 2, 60)
    await backend.set("c", 3, 60)
    # 超过 maxsize，最久未访问的 "a" 被淘汰（TTLCache 继承 LRU）
    assert await backend.get("a") is None
    assert await backend.get("b") == 2
    assert await backend.get("c") == 3
