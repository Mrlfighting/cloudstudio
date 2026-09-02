"""图片协同编辑的 Redis 分布式编辑锁（跨实例一致，未来多实例可复用）。"""

from typing import Any, cast

import redis.asyncio as aioredis

# 释放锁的 Lua 脚本：仅当值匹配（持有者）时才删除，保证「仅持有者可释放」的原子性
_RELEASE_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class CollabLock:
    """Redis 分布式锁：编辑锁的获取 / 释放 / 查询。"""

    def __init__(self, redis: aioredis.Redis, ttl: int) -> None:
        self._redis = redis
        self._ttl = ttl

    @staticmethod
    def _key(space_id: int, picture_id: int) -> str:
        return f"collab:lock:{space_id}:{picture_id}"

    async def try_acquire(self, space_id: int, picture_id: int, user_id: int) -> bool:
        """尝试获取锁；成功或已是持有者返回 True，他人持锁返回 False。"""
        key = self._key(space_id, picture_id)
        try:
            holder = await self._redis.get(key)
            if holder is not None and int(holder) == user_id:
                # 已是持有者（幂等）：刷新 TTL 并返回 True
                await self._redis.expire(key, self._ttl)
                return True
            result = await self._redis.set(key, str(user_id), nx=True, ex=self._ttl)
            return bool(result)
        except Exception:
            # Redis 不可用 fail-open：视为可获取，避免编辑功能瘫痪
            return True

    async def release(self, space_id: int, picture_id: int, user_id: int) -> bool:
        """释放锁（仅持有者可释放）。"""
        key = self._key(space_id, picture_id)
        try:
            result = await cast(Any, self._redis.eval(_RELEASE_LUA, 1, key, str(user_id)))
            return bool(result)
        except Exception:
            return False

    async def get_holder(self, space_id: int, picture_id: int) -> int | None:
        """查询当前锁持有者 user_id，无则 None。"""
        key = self._key(space_id, picture_id)
        try:
            value = await self._redis.get(key)
            return int(value) if value is not None else None
        except Exception:
            return None

    async def close(self) -> None:
        await self._redis.aclose()
