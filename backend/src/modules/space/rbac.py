"""团队空间 RBAC：角色 → 权限矩阵（自建轻量，无三方依赖）。

权限动作：
- read            查看图片
- write           上传 / 编辑图片
- delete          删除图片
- manage_members  成员管理（邀请/移除/设角色/列表）
- manage_settings 空间设置（改名/升级级别）
"""

from .enums import SpaceRole

READ = "read"
WRITE = "write"
DELETE = "delete"
MANAGE_MEMBERS = "manage_members"
MANAGE_SETTINGS = "manage_settings"

_ALL = frozenset({READ, WRITE, DELETE, MANAGE_MEMBERS, MANAGE_SETTINGS})

# 角色 → 权限集合
ROLE_PERMISSIONS: dict[SpaceRole, frozenset[str]] = {
    SpaceRole.ADMIN: _ALL,  # 管理员：全部权限
    SpaceRole.EDITOR: frozenset({READ, WRITE, DELETE}),  # 编辑者：图片增删改查
    SpaceRole.VIEWER: frozenset({READ}),  # 查看者：仅查看
}


def has_permission(role: SpaceRole, permission: str) -> bool:
    """判断某角色是否具备某权限。"""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
