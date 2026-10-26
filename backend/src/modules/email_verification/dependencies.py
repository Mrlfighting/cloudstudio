"""邮箱请求绑定真实会话，公开资料更新不能绕过验证。"""

from typing import Annotated, Any

from fastapi import Header, HTTPException

from ...infrastructure.dependencies import CurrentUserDep
from ..user.models import User
from ..user.schemas import UserUpdate
from .schemas import normalize_email


async def expected_user(
    current_user: CurrentUserDep,
    expected: Annotated[int | None, Header(alias="X-Expected-User-ID", ge=1)] = None,
) -> dict[str, Any]:
    """预期账号是前置条件，不接受客户端指定账号作为授权依据。"""
    if expected is None:
        raise HTTPException(428, "请携带X-Expected-User-ID账号上下文")
    if current_user["id"] != expected:
        raise HTTPException(
            409,
            "登录账号已变更，请确认当前账号后重新操作",
            headers={"Cache-Control": "private, no-store", "X-Email-Session-Changed": "1"},
        )
    return current_user


def protect_profile(values: UserUpdate, user: dict | User) -> None:
    """兼容旧前端原样提交当前邮箱，拒绝借资料PATCH改变绑定和认证状态。"""
    data = values.model_dump(exclude_unset=True)
    if "email_verified" in data:
        raise HTTPException(422, "邮箱认证状态只能由验证流程修改")
    if "email" in data:
        existing = user.get("email") if isinstance(user, dict) else user.email
        submitted = normalize_email(str(data["email"])) if data["email"] is not None else None
        current = normalize_email(existing) if existing is not None else None
        if submitted != current:
            raise HTTPException(409, "请通过邮箱验证接口绑定、换绑或解绑邮箱")
        # 从更新模型移除原样提交字段，避免旧接口改写邮箱大小写或绕过原子流程。
        values.__pydantic_fields_set__.discard("email")
