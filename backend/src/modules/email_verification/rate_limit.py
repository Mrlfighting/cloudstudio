"""邮件专用共享限流；基础设施故障时拒绝发送，不能退化为无限发信。"""

import hashlib
import hmac
import logging
import time
from collections.abc import Awaitable
from typing import Any, cast

from crudauth.utils import get_client_ip
from fastapi import HTTPException, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from ...infrastructure.config.settings import get_settings
from .config import get_mail_settings

logger = logging.getLogger(__name__)
SCRIPT = """
for i,key in ipairs(KEYS) do
  if tonumber(redis.call('GET', key) or '0') >= tonumber(ARGV[i*2-1]) then
    return math.max(1, redis.call('TTL', key))
  end
end
for i,key in ipairs(KEYS) do
  local n = redis.call('INCR', key)
  if n == 1 then redis.call('EXPIRE', key, ARGV[i*2]) end
end
return 0
"""


class MailLimiter:
    """Redis保存摘要形式的限流标识，不把邮箱明文作为key。"""

    async def check(self, limits: list[tuple[str, int, int]]) -> None:
        """同一Lua脚本先检查全部窗口再计数，避免并发绕过。"""
        cfg = get_mail_settings()
        keys, args = [], []
        for identity, count, seconds in limits:
            digest = hmac.new(cfg.token_secret.get_secret_value().encode(), identity.encode(), hashlib.sha256).hexdigest()
            keys.append(f"mail:limit:{digest}:{int(time.time()) // seconds}")
            args.extend([count, seconds])
        settings = get_settings()
        try:
            async with Redis(
                host=settings.RATE_LIMITER_REDIS_HOST,
                port=settings.RATE_LIMITER_REDIS_PORT,
                db=settings.RATE_LIMITER_REDIS_DB,
                password=settings.RATE_LIMITER_REDIS_PASSWORD,
                socket_connect_timeout=2,
                socket_timeout=2,
            ) as redis:
                retry = int(await cast(Awaitable[Any], redis.eval(SCRIPT, len(keys), *keys, *args)))
        except (RedisError, OSError):
            logger.warning("邮件限流服务不可用")
            raise HTTPException(503, "邮件服务暂不可用，请稍后重试") from None
        if retry:
            raise HTTPException(429, "邮件操作过于频繁，请稍后重试", headers={"Retry-After": str(retry)})

    async def request(self, request: Request, email: str, user_id: int | None = None) -> None:
        """注册和发送共享收件人/IP额度，不能通过创建多个账号绕过。"""
        cfg = get_mail_settings()
        ip = get_client_ip(request, get_settings().TRUSTED_PROXY_HOPS)
        limits = [(f"request/ip/{ip}", cfg.ip_hour_limit, 3600), (f"request/email/{email}", cfg.address_hour_limit, 3600)]
        if user_id is not None:
            limits.append((f"request/user/{user_id}", cfg.account_hour_limit, 3600))
        await self.check(limits)

    async def confirm(self, request: Request, user_id: int) -> None:
        """账号与IP同时限制，错误验证码仍由数据库持久计数。"""
        ip = get_client_ip(request, get_settings().TRUSTED_PROXY_HOPS)
        await self.check([(f"confirm/user/{user_id}", 30, 60), (f"confirm/ip/{ip}", 60, 60)])

    async def sending(self) -> None:
        """发送端限速对所有worker共享，保护个人QQ邮箱。"""
        await self.check([("smtp/global", get_mail_settings().send_per_minute, 60)])


def get_mail_limiter() -> MailLimiter:
    """可在隔离测试中替换，不更改全站默认限流行为。"""
    return MailLimiter()
