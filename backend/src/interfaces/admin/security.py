"""SQLAdmin 独立 CSRF 防护，覆盖登录、表单、AJAX 删除及退出。"""

import secrets
from urllib.parse import urlsplit

from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ...infrastructure.config.settings import get_settings

COOKIE = "atelier_admin_csrf"


class AdminCSRFMiddleware(BaseHTTPMiddleware):
    """签名双提交令牌与同源校验共同阻止跨站写入，不依赖 SameSite 默认行为。"""

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        signer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="sqladmin-csrf-v1")
        token = request.cookies.get(COOKIE, "")
        valid = False
        if token:
            try:
                signer.loads(token, max_age=3600)
                valid = True
            except BadSignature:
                pass
        mutating = request.method not in {"GET", "HEAD", "OPTIONS"} or request.url.path.endswith("/logout")
        if mutating:
            origin = request.headers.get("origin")
            expected_origin = f"{request.url.scheme}://{request.url.netloc}"
            referer = request.headers.get("referer", "")
            if origin:
                same_origin = origin == expected_origin
            else:
                parsed = urlsplit(referer)
                same_origin = f"{parsed.scheme}://{parsed.netloc}" == expected_origin
            if not same_origin or not valid:
                return JSONResponse({"detail": "后台安全令牌失效，请刷新页面重试"}, status_code=403)
            supplied = request.headers.get("x-admin-csrf", "")
            if not supplied and request.method == "POST":
                # 先缓存完整消息体再解析，避免中间件消费后下游表单读不到内容。
                body = await request.body()
                if len(body) > 10 * 1024 * 1024:
                    return JSONResponse({"detail": "后台表单过大"}, status_code=413)
                form = await request.form()
                supplied = str(form.get("csrf_token", ""))
            if not secrets.compare_digest(supplied.encode("utf-8"), token.encode("utf-8")):
                return JSONResponse({"detail": "后台安全令牌失效，请刷新页面重试"}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "private, no-store"
        if not valid and not mutating:
            response.set_cookie(
                COOKIE,
                signer.dumps(secrets.token_urlsafe(32)),
                max_age=3600,
                path="/admin",
                secure=settings.SESSION_SECURE_COOKIES,
                httponly=False,
                samesite="strict",
            )
        return response
