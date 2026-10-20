"""拼豆编辑上下文前置校验；预期账号仅作一致性条件，不用于授予权限。"""

from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Query

from ...infrastructure.dependencies import CurrentUserDep


def check_owner(current_user: dict[str, Any], expected: int | None) -> dict[str, Any]:
    """缺少上下文或共享 Cookie 已换号时，在读写作品之前拒绝。"""
    if expected is None:
        raise HTTPException(428, "请刷新拼豆页面后重试，当前请求缺少账号上下文")
    if expected != current_user["id"]:
        raise HTTPException(
            409,
            "登录账号已在其他页面变更，本次操作已取消，请确认账号后重试",
            headers={"X-Bead-Session-Changed": "1", "Cache-Control": "private, no-store"},
        )
    return current_user


async def get_bead_user(
    current_user: CurrentUserDep,
    expected: Annotated[int | None, Header(alias="X-Bead-Owner", ge=1)] = None,
) -> dict[str, Any]:
    """所有拼豆 XHR 绑定发起时的账号，不能被后来替换的 Cookie 静默接管。"""
    return check_owner(current_user, expected)


async def get_thumbnail_user(
    current_user: CurrentUserDep,
    expected: Annotated[int | None, Header(alias="X-Bead-Owner", ge=1)] = None,
    owner: Annotated[int | None, Query(ge=1)] = None,
) -> dict[str, Any]:
    """原生图片标签不能加请求头，使用只作一致性核对的 owner 参数。"""
    return check_owner(current_user, expected if expected is not None else owner)


BeadUserDep = Annotated[dict[str, Any], Depends(get_bead_user)]
ThumbnailUserDep = Annotated[dict[str, Any], Depends(get_thumbnail_user)]
