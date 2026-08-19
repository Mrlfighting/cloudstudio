"""@cached 方法级装饰器单元测试。"""

from unittest.mock import AsyncMock

import pytest

from src.infrastructure.cache.backends.memory import MemoryBackend
from src.infrastructure.cache.method_cache import cached
from src.infrastructure.cache.two_level import TwoLevelCacheManager, set_cache_manager


class Service:
    def __init__(self) -> None:
        self.calls = 0

    @cached(key_prefix="svc", ttl=300, key_builder=lambda self, x: f"svc:{x}")
    async def fetch(self, x: int) -> dict[str, int]:
        self.calls += 1
        return {"x": x}


@pytest.fixture(autouse=True)
def _reset_manager():
    set_cache_manager(None)
    yield
    set_cache_manager(None)


@pytest.mark.asyncio
async def test_falls_back_to_direct_execution_when_manager_none():
    svc = Service()
    assert await svc.fetch(1) == {"x": 1}
    assert svc.calls == 1


@pytest.mark.asyncio
async def test_caches_when_manager_set():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    set_cache_manager(TwoLevelCacheManager(local=MemoryBackend(), redis=redis))

    svc = Service()
    r1 = await svc.fetch(1)
    r2 = await svc.fetch(1)
    assert r1 == {"x": 1}
    assert r2 == {"x": 1}
    # 第二次命中 L1，未回源
    assert svc.calls == 1
