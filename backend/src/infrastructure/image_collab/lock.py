"""Redis 负责跨实例编辑锁与临时状态；不可用时拒绝编辑，不退回进程锁。"""

from contextlib import asynccontextmanager
from typing import Any, cast

import redis.asyncio as aioredis

from .models import PictureEditState

_ACQUIRE = """
local holder = redis.call('get', KEYS[1])
if not holder or holder == ARGV[1] then
    redis.call('set', KEYS[1], ARGV[1], 'EX', ARGV[2])
    return 1
end
return 0
"""
_RELEASE = """
if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) end
return 0
"""


class CollabUnavailable(RuntimeError):
    """共享协调服务不可用，调用方必须停止写入。"""


class CollabLock:
    """用户锁和命令串行锁分离，避免跨 API 实例同时修改同一图片。"""

    def __init__(self, redis: aioredis.Redis, ttl: int) -> None:
        self._redis = redis
        self._ttl = ttl

    @staticmethod
    def _key(space_id: int, picture_id: int) -> str:
        return f"collab:lock:{space_id}:{picture_id}"

    async def try_acquire(self, space_id: int, picture_id: int, user_id: int) -> bool:
        """Lua 原子获取或续期，不误续已转移的锁。"""
        return bool(await cast(Any, self._redis.eval(_ACQUIRE, 1, self._key(space_id, picture_id), str(user_id), self._ttl)))

    async def release(self, space_id: int, picture_id: int, user_id: int) -> bool:
        """仅持有者可释放，Redis 错误直接上抛。"""
        return bool(await cast(Any, self._redis.eval(_RELEASE, 1, self._key(space_id, picture_id), str(user_id))))

    async def get_holder(self, space_id: int, picture_id: int) -> int | None:
        """返回共享锁持有者，不在故障时猜测锁状态。"""
        value = await self._redis.get(self._key(space_id, picture_id))
        return int(value) if value is not None else None

    @asynccontextmanager
    async def serialized(self, space_id: int, picture_id: int):
        """命令有五秒执行预算，小于十五秒租期；未取得锁则拒绝执行。"""
        mutex = self._redis.lock(f"collab:command:{space_id}:{picture_id}", timeout=15, blocking_timeout=2)
        if not await mutex.acquire():
            raise CollabUnavailable("协同操作繁忙，请重试")
        try:
            yield
        finally:
            await mutex.release()

    async def get_state(self, space_id: int, picture_id: int) -> PictureEditState | None:
        """新连接获取共享工作状态，不限于最后一次保存的快照。"""
        value = await self._redis.get(f"collab:state:{space_id}:{picture_id}")
        return PictureEditState.model_validate_json(value) if value else None

    async def set_state(self, space_id: int, picture_id: int, state: PictureEditState) -> None:
        """临时工作状态有界保留，不替代显式保存。"""
        await self._redis.set(f"collab:state:{space_id}:{picture_id}", state.model_dump_json(), ex=86400)

    async def next_revision(self, space_id: int, picture_id: int) -> int:
        """广播事件使用共享递增序号，不依赖单个进程的时间戳。"""
        key = f"collab:revision:{space_id}:{picture_id}"
        value = await self._redis.incr(key)
        await self._redis.expire(key, 172800)
        return int(value)

    async def close(self) -> None:
        """关闭共享 Redis 连接池。"""
        await self._redis.aclose()
