"""邮箱API只对已登录本人开放，验证码校验错误不能进入全局明文输入日志。"""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from ...infrastructure.dependencies import AsyncSessionDep
from . import service
from .config import get_mail_settings
from .dependencies import expected_user
from .rate_limit import MailLimiter, get_mail_limiter
from .schemas import BindingRequest, Confirmation


class PrivateInputRoute(APIRoute):
    """在现有全局参数错误日志之前截断敏感入参，不修改原认证错误处理。"""

    def get_route_handler(self):
        """验证失败只返回固定消息，不记录原始body、验证码或参数异常。"""
        original = super().get_route_handler()

        async def safe(request: Request):
            try:
                return await original(request)
            except RequestValidationError:
                raise HTTPException(422, "邮箱请求参数不正确") from None

        return safe


class RegistrationInputRoute(PrivateInputRoute):
    """旧用户路由仅在注册参数错误时启用脱敏，不改变其他资料接口错误流程。"""

    def get_route_handler(self):
        """可选邮箱注册也不能让密码或完整输入进入全局参数错误日志。"""
        if self.path.endswith("/register"):
            return super().get_route_handler()
        return APIRoute.get_route_handler(self)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动只检查配置，不连接SMTP或RabbitMQ，不拖慢API请求。"""
    get_mail_settings()
    yield


router = APIRouter(tags=["邮箱验证"], route_class=PrivateInputRoute, lifespan=lifespan)
Owner = Annotated[dict, Depends(expected_user)]
Limiter = Annotated[MailLimiter, Depends(get_mail_limiter)]


@router.get("/status")
async def get_status(db: AsyncSessionDep, user: Owner, response: Response) -> dict:
    """本人状态禁止浏览器或代理缓存。"""
    response.headers["Cache-Control"] = "private, no-store"
    return await service.status(db, user["id"])


@router.post("/binding/request", status_code=202)
async def binding_request(body: BindingRequest, request: Request, db: AsyncSessionDep, user: Owner, limiter: Limiter) -> dict:
    """申请绑定/换绑，新申请使旧验证码失效。"""
    return await service.request_binding(db, user["id"], body.email, request, limiter)


@router.post("/binding/confirm")
async def binding_confirm(body: Confirmation, request: Request, db: AsyncSessionDep, user: Owner, limiter: Limiter) -> dict:
    """登录、CSRF和账号上下文校验后才允许消费验证码。"""
    service.require_enabled()
    await limiter.confirm(request, user["id"])
    return await service.confirm(db, user["id"], body.request_id, body.code, "binding")


@router.post("/unbind/request", status_code=202)
async def unbind_request(request: Request, db: AsyncSessionDep, user: Owner, limiter: Limiter) -> dict:
    """原邮箱验证，不接受指定收件人。"""
    return await service.request_unbind(db, user["id"], request, limiter)


@router.post("/unbind/confirm")
async def unbind_confirm(body: Confirmation, request: Request, db: AsyncSessionDep, user: Owner, limiter: Limiter) -> dict:
    """解绑消费原邮箱验证码，与换绑使用相互隔离的用途。"""
    service.require_enabled()
    await limiter.confirm(request, user["id"])
    return await service.confirm(db, user["id"], body.request_id, body.code, "unbind")
