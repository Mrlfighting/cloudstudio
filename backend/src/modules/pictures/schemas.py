from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import PictureCategory


class PictureRead(BaseModel):
    """图片完整信息（详情）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    name: str
    introduction: str | None = None
    category: str | None = None
    tags: list[str] = []
    pic_size: int | None = None
    pic_width: int | None = None
    pic_height: int | None = None
    pic_scale: float | None = None
    pic_format: str | None = None
    color_mode: str | None = None
    primary_color: int | None = None
    user_id: int
    space_id: int | None = None
    status: str
    review_reason: str | None = None
    download_count: int = 0
    edit_state: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PictureListItemRead(BaseModel):
    """列表项（精简字段）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    name: str
    category: str | None = None
    tags: list[str] = []
    pic_width: int | None = None
    pic_height: int | None = None
    pic_format: str | None = None
    primary_color: int | None = None
    status: str
    review_reason: str | None = None
    user_id: int
    space_id: int | None = None
    download_count: int = 0
    created_at: datetime | None = None


class PictureCreateInternal(BaseModel):
    """内部创建 Schema（含自动解析字段）。"""

    url: str
    name: str
    introduction: str | None = None
    category: str | None = None
    tags: list[str] = []
    pic_size: int | None = None
    pic_width: int | None = None
    pic_height: int | None = None
    pic_scale: float | None = None
    pic_format: str | None = None
    color_mode: str | None = None
    primary_color: int | None = None
    user_id: int
    space_id: int | None = None
    status: str = "pending"


class PictureUpdate(BaseModel):
    """编辑图片元信息（不含文件）。"""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[str | None, Field(min_length=1, max_length=128)] = None
    introduction: Annotated[str | None, Field(max_length=512)] = None
    category: PictureCategory | None = None
    tags: list[str] | None = None


class PictureStatusUpdate(BaseModel):
    """管理员审核图片。拒绝时 review_reason 必填。"""

    model_config = ConfigDict(extra="forbid")

    status: Literal["approved", "rejected"]
    review_reason: Annotated[str | None, Field(max_length=512)] = None

    @model_validator(mode="after")
    def _validate_reject_reason(self) -> "PictureStatusUpdate":
        """拒绝时必须有理由。"""
        if self.status == "rejected" and (self.review_reason is None or not self.review_reason.strip()):
            raise ValueError("拒绝时必须填写拒绝理由")
        return self
