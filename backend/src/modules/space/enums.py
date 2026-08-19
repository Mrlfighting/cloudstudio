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
