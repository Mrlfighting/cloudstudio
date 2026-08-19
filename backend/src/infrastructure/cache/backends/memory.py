"""进程内内存缓存后端（二级缓存 L1 层），基于 cachetools.TTLCache。"""

from typing import Any

from cachetools import TTLCache

from ..base import CacheBackend


class MemoryBackend(CacheBackend):
    """进程内内存缓存后端，用于二级缓存中的 L1 层。

    基于 cachetools.TTLCache：线程安全，maxsize 限制最大条目数，全局 TTL 过期。

    注意：TTLCache 只支持全局 TTL（构造时指定），不支持逐 key 单独过期；
    因此 ``set`` 的 ``expiration`` 参数在本后端被忽略，L1 条目统一按构造时的
    ``ttl`` 过期（默认取 CACHE_LOCAL_TTL）。逐 key 精确 TTL 由 L2（Redis）负责。
    """

    def __init__(self, maxsize: int = 1000, ttl: int = 60) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=maxsize, ttl=ttl)

    async def get(self, key: str) -> Any | None:
        try:
            return self._cache[key]
        except KeyError:
            return None

    async def set(self, key: str, value: Any, expiration: int = 3600) -> None:
        # TTLCache 全局 TTL，expiration 被忽略（见类 docstring）。
        self._cache[key] = value

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    async def delete_pattern(self, pattern: str) -> None:
        prefix = pattern.rstrip("*")
        for key in [k for k in self._cache.keys() if k.startswith(prefix)]:
            self._cache.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._cache

    async def clear(self) -> None:
        self._cache.clear()

    async def ping(self) -> bool:
        return True
