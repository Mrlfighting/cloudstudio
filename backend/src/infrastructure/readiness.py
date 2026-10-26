"""就绪检查只暴露可用状态，不向匿名客户端泄露依赖地址或异常详情。"""

import asyncio
from typing import Any, cast

import asyncpg  # type: ignore[import-untyped]  # 上游未提供 py.typed，探针只使用公开连接接口。
import redis.asyncio as aioredis
from starlette.responses import JSONResponse

from .config.settings import get_settings
from .database.session import engine


async def _database() -> None:
    """独立短连接探测，避免业务池在取消查询时的优雅关闭拖延健康检查。"""
    dsn = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    connection = await asyncpg.connect(dsn, timeout=1, command_timeout=1)
    try:
        await connection.fetchval("SELECT 1")
    finally:
        # 探针不复用连接，直接断开而非等待故障服务器回应关闭/取消请求。
        connection.terminate()


async def _sessions() -> None:
    """会话 Redis 是鉴权关键依赖，必须能完成读写。"""
    settings = get_settings()
    if settings.SESSION_BACKEND != "redis":
        return
    client = aioredis.Redis(
        host=settings.CACHE_REDIS_HOST,
        port=settings.CACHE_REDIS_PORT,
        db=settings.CACHE_REDIS_DB,
        password=settings.CACHE_REDIS_PASSWORD,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        await cast(Any, client.ping())
    finally:
        await client.aclose()


async def readiness_response() -> JSONResponse:
    """并行探测，每个探测最多两秒，失败返回 503 供部署健康检查使用。"""

    async def check(probe) -> bool:
        try:
            async with asyncio.timeout(2):
                await probe()
            return True
        except Exception:
            return False

    database, sessions = await asyncio.gather(check(_database), check(_sessions))
    ready = database and sessions
    return JSONResponse(
        {"status": "ready" if ready else "not_ready", "checks": {"database": database, "sessions": sessions}},
        status_code=200 if ready else 503,
        headers={"Cache-Control": "no-store"},
    )
