"""二级缓存管理器：L1 本地内存（MemoryBackend）+ L2 Redis（RedisBackend）。"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.encoders import jsonable_encoder

from ..logging import get_logger
from .backends.redis import RedisBackend
from .base import CacheBackend

logger = get_logger()


class TwoLevelCacheManager:
    """二级缓存管理器（本地优先，Redis 次之）。

    读路径：L1 命中直接返回；未命中查 L2，命中回填 L1；仍未命中返回 None
    （由 ``get_or_load`` 触达 DB）。Redis 异常时降级为 L1 + DB 直读（fail-open）。

    命中率统计为进程内计数器（local/redis 各自的 hit/miss）。
    """

    def __init__(
        self,
        local: CacheBackend,
        redis: RedisBackend,
        *,
        enabled: bool = True,
        local_ttl: int = 60,
        hot_key_threshold: int = 10,
        hot_key_window: int = 60,
    ) -> None:
        self._local = local
        self._redis = redis
        self._enabled = enabled
        self._local_ttl = local_ttl
        self._hot_key_threshold = hot_key_threshold
        self._hot_key_window = hot_key_window

        self._local_hits = 0
        self._local_misses = 0
        self._redis_hits = 0
        self._redis_misses = 0

        self._locks: dict[str, asyncio.Lock] = {}

    @property
    def enabled(self) -> bool:
        """二级缓存全局开关。"""
        return self._enabled

    # ------------------------------------------------------------------ 读写

    async def get(self, key: str) -> Any | None:
        """L1 → L2 穿透；命中 L2 回填 L1。两级都未命中返回 None（不含 DB）。"""
        value = await self._local.get(key)
        if value is not None:
            self._local_hits += 1
            return value
        self._local_misses += 1

        try:
            value = await self._redis.get(key)
        except Exception as e:
            logger.warning(
                f"Redis 不可用，降级直读（key={key}）: {e}",
                extra={"reason": "redis_unavailable"},
            )
            self._redis_misses += 1
            return None

        if value is not None:
            self._redis_hits += 1
            await self._local.set(key, value, self._local_ttl)
            return value
        self._redis_misses += 1
        return None

    async def put(self, key: str, value: Any, ttl: int) -> None:
        """同时写 L1（统一本地 TTL）与 L2（精确 TTL）。

        L1 存原始对象（内存无需序列化）；L2 写入前用 jsonable_encoder 把
        datetime 等不可 JSON 序列化的类型转成 JSON 兼容值（与 @cache 装饰器一致）。
        """
        await self._local.set(key, value, self._local_ttl)
        try:
            await self._redis.set(key, jsonable_encoder(value), ttl)
        except Exception as e:
            logger.warning(
                f"Redis 不可用，跳过 L2 写入（key={key}）: {e}",
                extra={"reason": "redis_unavailable"},
            )

    async def evict(self, key: str) -> None:
        """同步清除 L1 + L2。"""
        await self._local.delete(key)
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.warning(
                f"Redis 不可用，跳过 L2 删除（key={key}）: {e}",
                extra={"reason": "redis_unavailable"},
            )

    async def invalidate_by_prefix(self, prefix: str) -> None:
        """按前缀批量失效（L1 遍历匹配、L2 用 SCAN）。"""
        await self._local.delete_pattern(prefix)
        try:
            await self._redis.delete_pattern(prefix)
        except Exception as e:
            logger.warning(
                f"Redis 不可用，跳过 L2 批量删除（prefix={prefix}）: {e}",
                extra={"reason": "redis_unavailable"},
            )

    async def get_or_load(
        self,
        key: str,
        loader: Callable[[], Awaitable[Any]],
        ttl: int,
        *,
        track_hot: bool = False,
    ) -> Any:
        """缓存穿透保护：get 未命中 → per-key 锁防击穿 → loader() 查库回填。"""
        value = await self.get(key)
        if value is not None:
            if track_hot:
                await self._maybe_promote(key)
            return value

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            value = await self.get(key)
            if value is not None:
                if track_hot:
                    await self._maybe_promote(key)
                return value
            value = await loader()
            await self.put(key, value, ttl)
            if track_hot:
                await self._maybe_promote(key)
            return value

    # ----------------------------------------------------------- 热key探测

    def _hot_counter_key(self, key: str) -> str:
        return f"pic:hot:{key}"

    async def record_access(self, key: str) -> int:
        """记录一次访问，返回窗口内累计次数（Redis INCR + EXPIRE）。"""
        hot_key = self._hot_counter_key(key)
        try:
            pipe = self._redis.client.pipeline()
            pipe.incr(hot_key)
            pipe.expire(hot_key, self._hot_key_window)
            result = await pipe.execute()
            return int(result[0])
        except Exception as e:
            logger.warning(
                f"热key计数失败（key={key}）: {e}",
                extra={"reason": "redis_unavailable"},
            )
            return 0

    async def is_hot_key(self, key: str) -> bool:
        """判断某 key 当前是否为热点（计数 ≥ 阈值）。"""
        try:
            raw = await self._redis.client.get(self._hot_counter_key(key))
        except Exception as e:
            logger.warning(
                f"读取热key计数失败（key={key}）: {e}",
                extra={"reason": "redis_unavailable"},
            )
            return False
        if raw is None:
            return False
        try:
            return int(raw) >= self._hot_key_threshold
        except (TypeError, ValueError):
            return False

    async def promote_to_local(self, key: str) -> None:
        """从 Redis 读取并写入 L1（供热点提升）。"""
        try:
            value = await self._redis.get(key)
        except Exception as e:
            logger.warning(
                f"Redis 不可用，无法提升热key（key={key}）: {e}",
                extra={"reason": "redis_unavailable"},
            )
            return
        if value is not None:
            await self._local.set(key, value, self._local_ttl)

    async def _maybe_promote(self, key: str) -> None:
        """记录访问，达到阈值则提升到 L1。"""
        count = await self.record_access(key)
        if count >= self._hot_key_threshold:
            await self.promote_to_local(key)

    # ------------------------------------------------------------- 命中率统计

    def stats(self) -> dict[str, Any]:
        """返回 local/redis 各自的 hit、miss 与命中率。"""

        def _rate(hits: int, misses: int) -> float:
            total = hits + misses
            return round(hits / total, 4) if total else 0.0

        return {
            "local": {
                "hit": self._local_hits,
                "miss": self._local_misses,
                "hit_rate": _rate(self._local_hits, self._local_misses),
            },
            "redis": {
                "hit": self._redis_hits,
                "miss": self._redis_misses,
                "hit_rate": _rate(self._redis_hits, self._redis_misses),
            },
        }

    async def close(self) -> None:
        """关闭底层 Redis 连接。"""
        client = getattr(self._redis, "client", None)
        if client is None:
            return
        aclose = getattr(client, "aclose", None)
        if aclose is not None:
            await aclose()
        else:
            close = getattr(client, "close", None)
            if close is not None:
                await close()


# 模块级单例（由 initialize.py 在应用启动时赋值）
_two_level_cache: TwoLevelCacheManager | None = None


def get_cache_manager() -> TwoLevelCacheManager | None:
    """获取当前二级缓存管理器；未初始化时返回 None。"""
    return _two_level_cache


def set_cache_manager(manager: TwoLevelCacheManager | None) -> None:
    """设置 / 清空二级缓存管理器。"""
    global _two_level_cache
    _two_level_cache = manager
