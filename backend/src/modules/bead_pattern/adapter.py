"""私有空间只读适配器：沿用原有查询权限，不直接访问 ORM。"""

from typing import Any

from fastapi import HTTPException

from ...infrastructure.dependencies import AsyncSessionDep, CurrentUserDep
from ..common.utils.error_handler import handle_exception
from ..space.dependencies import SpaceServiceDep


async def get_private_picture(
    picture_id: int,
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    space_service: SpaceServiceDep,
) -> dict[str, Any]:
    """通过既有只读查询取得本人图片，工具侧额外拒绝封禁空间。"""
    try:
        space = await space_service.get_my(db, current_user)
        if space["status"] == "banned":
            raise HTTPException(status_code=403, detail="空间已被封禁，无法导入图片")
        return await space_service.get_picture(db, current_user, picture_id)
    except Exception as error:
        mapped = handle_exception(error)
        if mapped is not None:
            raise mapped from error
        raise
