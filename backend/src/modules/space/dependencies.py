from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.dependencies import AsyncSessionDep, CurrentUserDep
from ..common.exceptions import PermissionDeniedError
from .enums import SpaceRole
from .models import SpaceUser
from .rbac import has_permission
from .service import SpaceService


def get_space_service() -> SpaceService:
    return SpaceService()


SpaceServiceDep = Annotated[SpaceService, Depends(get_space_service)]


async def _get_team_member_role(db: AsyncSession, space_id: int, user_id: int) -> SpaceRole | None:
    """查询用户在指定空间的成员角色；非成员返回 None。"""
    stmt = select(SpaceUser.space_role).where(
        SpaceUser.space_id == space_id,
        SpaceUser.user_id == user_id,
    )
    role = (await db.execute(stmt)).scalar_one_or_none()
    return SpaceRole(role) if role else None


def require_team_permission(*permissions: str):
    """团队空间权限依赖：要求当前用户在指定空间具备任一权限（OR）。

    用法：``dependencies=[Depends(require_team_permission(WRITE))]``。
    非成员或权限不足抛 PermissionDeniedError（→403）。
    """
    async def dependency(
        space_id: int,
        db: AsyncSessionDep,
        current_user: CurrentUserDep,
    ) -> None:
        role = await _get_team_member_role(db, space_id, current_user["id"])
        if role is None or not any(has_permission(role, p) for p in permissions):
            raise PermissionDeniedError("您不是该团队成员，或没有执行此操作的权限")

    return dependency
