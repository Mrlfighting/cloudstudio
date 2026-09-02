"""空间模块 Pydantic schema。"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from ..pictures.schemas import PictureListItemRead
from .enums import SpaceLevel, SpaceRole


class SpaceCreate(BaseModel):
    """用户创建空间（仅名称）。"""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=128)]


class SpaceCreateInternal(BaseModel):
    """内部创建空间（service 层填充级别/配额/所属用户）。"""

    name: str
    space_type: int = 0
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
    space_type: int = 0
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
    space_type: int = 0
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
    space_type: int = 0
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


class SpaceMemberCreate(BaseModel):
    """邀请成员（管理员）：目标用户 + 角色。"""

    model_config = ConfigDict(extra="forbid")

    user_id: int
    space_role: SpaceRole = SpaceRole.VIEWER


class SpaceUserCreateInternal(BaseModel):
    """内部创建成员关联（service 填充 space_id）。"""

    space_id: int
    user_id: int
    space_role: str = "viewer"


class SpaceMemberUpdate(BaseModel):
    """设置成员角色（管理员）。"""

    model_config = ConfigDict(extra="forbid")

    space_role: SpaceRole


class SpaceMemberRead(BaseModel):
    """成员信息（含用户展示字段 + 角色）。"""

    user_id: int
    username: str
    name: str
    space_role: str
    created_at: datetime | None = None


class TeamSpaceListItemRead(BaseModel):
    """我加入（含我创建）的团队空间列表项（含我的角色）。"""

    id: int
    name: str
    space_role: str
    space_level: int
    total_count: int
    total_size: int
    max_count: int
    max_size: int
    created_at: datetime | None = None
