"""空间模块常量：各级别限额。"""

from .enums import SpaceLevel

# 各空间级别的容量上限（字节）与图片数量上限（私有空间）
SPACE_LEVEL_LIMITS: dict[int, dict[str, int]] = {
    SpaceLevel.NORMAL: {"max_size": 500 * 1024 * 1024, "max_count": 100},  # 普通版 500MB / 100张
    SpaceLevel.PRO: {"max_size": 5 * 1024 * 1024 * 1024, "max_count": 1000},  # 专业版 5GB / 1000张
    SpaceLevel.FLAGSHIP: {"max_size": 10 * 1024 * 1024 * 1024, "max_count": 3000},  # 旗舰版 10GB / 3000张
}

# 团队空间各级别容量上限（5× 私有空间）
TEAM_SPACE_LEVEL_LIMITS: dict[int, dict[str, int]] = {
    SpaceLevel.NORMAL: {"max_size": int(2.5 * 1024**3), "max_count": 500},  # 普通版 2.5GB / 500张
    SpaceLevel.PRO: {"max_size": 25 * 1024**3, "max_count": 5000},  # 专业版 25GB / 5000张
    SpaceLevel.FLAGSHIP: {"max_size": 50 * 1024**3, "max_count": 15000},  # 旗舰版 50GB / 15000张
}
