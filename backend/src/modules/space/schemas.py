"""空间模块 Pydantic schema。"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from ..pictures.schemas import PictureListItemRead
from .enums import SpaceLevel


class SpaceCreate(BaseModel):
    """用户创建空间（仅名称）。"""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=128)]


class SpaceCreateInternal(BaseModel):
    """内部创建空间（service 层填充级别/配额/所属用户）。"""

    name: str
    space_level: int
    max_size: int
    max_count: int
    user_id: int
    status: str = "active"


class SpaceRead(BaseModel):
    """空间完整信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    space_level: int
    max_size: int
    max_count: int
    total_size: int
    total_count: int
    user_id: int
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SpaceListRead(BaseModel):
    """空间列表项（管理员）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    space_level: int
    max_size: int
    max_count: int
    total_size: int
    total_count: int
    user_id: int
    status: str
    created_at: datetime | None = None


class SpaceUpdate(BaseModel):
    """管理员编辑空间（名称 / 级别）。"""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[str | None, Field(min_length=1, max_length=128)] = None
    space_level: SpaceLevel | None = None


class SpaceLevelUpdate(BaseModel):
    """用户升级/降级空间级别。"""

    model_config = ConfigDict(extra="forbid")

    space_level: SpaceLevel


class SpaceInfoRead(BaseModel):
    """用户空间信息（含剩余量；超限时剩余量为负）。"""

    id: int
    name: str
    space_level: int
    max_size: int
    max_count: int
    total_size: int
    total_count: int
    status: str
    remaining_size: int
    remaining_count: int
    created_at: datetime | None = None


class ColorSearchItem(PictureListItemRead):
    """按颜色搜索的结果项：图片列表项 + 颜色距离（越小越相近）。"""

    color_distance: float
