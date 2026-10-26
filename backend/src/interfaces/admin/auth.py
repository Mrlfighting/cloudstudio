"""Authentication backend for SQLAdmin."""

import asyncio
import secrets

from crudauth.utils import get_client_ip
from sqladmin.authentication import AuthenticationBackend
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from ...infrastructure.config.settings import get_settings
from ...infrastructure.rate_limit.provider import increment_and_check
from .security import AdminCSRFMiddleware


class AdminAuth(AuthenticationBackend):
    """Session-based authentication for the admin interface."""

    async def login(self, request: Request) -> bool:
        """Validate login credentials and create session."""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        settings = get_settings()
        # 登录失败计数跨实例共享；限流依赖故障时拒绝后台登录，不放开暴力尝试。
        try:
            async with asyncio.timeout(3):
                count, limited = await increment_and_check(
                    f"admin:login:{get_client_ip(request, settings.TRUSTED_PROXY_HOPS)}",
                    10,
                    60,
                    fail_open=False,
                )
            if limited and count == 0:
                raise RuntimeError("请求保护服务暂不可用")
        except Exception:
            raise HTTPException(status_code=503, detail="后台登录暂时不可用")
        if limited:
            raise HTTPException(status_code=429, detail="登录尝试过于频繁", headers={"Retry-After": "60"})
        if (
            isinstance(username, str)
            and isinstance(password, str)
            and secrets.compare_digest(username.encode("utf-8"), settings.ADMIN_USERNAME.encode("utf-8"))
            and secrets.compare_digest(password.encode("utf-8"), settings.ADMIN_PASSWORD.encode("utf-8"))
        ):
            request.session.clear()
            request.session.update({"admin_authenticated": True})
            return True

        return False

    async def logout(self, request: Request) -> bool:
        """Clear the admin session."""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Check if the current request is authenticated."""
        return bool(request.session.get("admin_authenticated", False))

    def __init__(self, secret_key: str) -> None:
        """仅在后台子应用安装一份会话中间件，独立 Cookie 并跟随生产安全配置。"""
        settings = get_settings()
        self.middlewares = [
            Middleware(
                SessionMiddleware,
                secret_key=secret_key,
                session_cookie="atelier_admin_session",
                https_only=settings.SESSION_SECURE_COOKIES,
                same_site="strict",
                max_age=3600,
            ),
            Middleware(AdminCSRFMiddleware),
        ]
