"""空间模块枚举。"""

from enum import IntEnum, StrEnum


class SpaceLevel(IntEnum):
    """空间级别。"""

    NORMAL = 0  # 普通版
    PRO = 1  # 专业版
    FLAGSHIP = 2  # 旗舰版


class SpaceStatus(StrEnum):
    """空间状态。"""

    ACTIVE = "active"
    BANNED = "banned"


class SpaceType(IntEnum):
    """空间类型：私有空间 / 团队空间。"""

    PRIVATE = 0  # 私有空间（每用户一个）
    TEAM = 1  # 团队空间（多人协作）


class SpaceRole(StrEnum):
    """团队空间成员角色。"""

    ADMIN = "admin"  # 管理员（Owner）：全部权限
    EDITOR = "editor"  # 编辑者：上传/删除/编辑/查看图片
    VIEWER = "viewer"  # 查看者：仅查看
