from importlib.util import find_spec

from .backends.memory import MemoryBackend
from .base import CacheBackend
from .decorator import cache
from .method_cache import cached
from .provider import cache_provider, clear, delete, delete_pattern, exists, get, set
from .two_level import TwoLevelCacheManager, get_cache_manager, set_cache_manager

MEMCACHED_INSTALLED = find_spec("aiomcache") is not None
REDIS_INSTALLED = find_spec("redis.asyncio") is not None

if MEMCACHED_INSTALLED:
    from .backends.memcached import MemcachedBackend, MemcachedSettings
else:
    MemcachedBackend = None  # type: ignore
    MemcachedSettings = None  # type: ignore

if REDIS_INSTALLED:
    from .backends.redis import RedisBackend, RedisSettings
else:
    RedisBackend = None  # type: ignore
    RedisSettings = None  # type: ignore

__all__ = [
    "CacheBackend",
    "MemcachedBackend",
    "MemoryBackend",
    "RedisBackend",
    "MemcachedSettings",
    "RedisSettings",
    "TwoLevelCacheManager",
    "cache",
    "cached",
    "cache_provider",
    "get",
    "set",
    "delete",
    "delete_pattern",
    "exists",
    "clear",
    "get_cache_manager",
    "set_cache_manager",
    "REDIS_INSTALLED",
    "MEMCACHED_INSTALLED",
]
