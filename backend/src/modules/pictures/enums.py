"""图片模块枚举。"""

from enum import StrEnum


class PictureStatus(StrEnum):
    """审核状态。"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PictureCategory(StrEnum):
    """预置分类列表。"""

    LANDSCAPE = "风景"
    PEOPLE = "人物"
    ANIMAL = "动物"
    ARCHITECTURE = "建筑"
    FOOD = "美食"
    TECHNOLOGY = "科技"
    ILLUSTRATION = "插画"
    OTHER = "其他"


class PictureFormat(StrEnum):
    """允许的图片格式。"""

    JPEG = "JPEG"
    PNG = "PNG"
    WEBP = "WEBP"
    GIF = "GIF"
