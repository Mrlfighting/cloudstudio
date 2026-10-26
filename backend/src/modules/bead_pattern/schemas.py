"""独立验证浏览器项目协议；不信任客户端色卡索引与文件声明。"""

import json
from datetime import datetime
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, model_validator

PALETTE_REVISION = "178dafbc9e77d3de556550dbd058270200129186"
# 与固定 MIT 色卡过滤后的顺序/数量一致，测试核对前后端清单。
PALETTE_COUNTS = {"mard-291-github": 291, "coco-291": 289, "manman-278": 277, "panpan-289": 285, "mixiaowo-290": 286}


class Parameters(BaseModel):
    """参数命名保持首版 JSON 协议不变。"""

    model_config = ConfigDict(extra="forbid", strict=True)
    longEdge: int = Field(ge=20, le=200)
    maxColors: int = Field(ge=2, le=128)
    removeBackground: bool
    backgroundColor: str | None = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    tolerance: float = Field(ge=0, le=40, allow_inf_nan=False)
    denoise: Literal[0, 1, 2]


class Grid(BaseModel):
    """按行的一维色卡索引，-1 为空格。"""

    model_config = ConfigDict(extra="forbid", strict=True)
    width: int = Field(ge=1, le=200)
    height: int = Field(ge=1, le=200)
    cells: list[StrictInt] = Field(max_length=40_000)


class Project(BaseModel):
    """支持既有 v1 备份，云端不接受嵌入 URL、令牌或原图。"""

    model_config = ConfigDict(extra="forbid", strict=True)
    format: Literal["cloudatelier-bead-pattern"]
    version: Literal[1]
    engineVersion: Literal["ciede2000-lanczos3-v1"]
    paletteRevision: Literal["178dafbc9e77d3de556550dbd058270200129186"]
    paletteId: str
    name: str = Field(min_length=1, max_length=128)
    updatedAt: str
    params: Parameters
    pattern: Grid

    @model_validator(mode="before")
    @classmethod
    def reject_boolean_literals(cls, data):
        """JSON 布尔不能利用 Python 的 True == 1 绕过版本/去杂枚举。"""
        if isinstance(data, dict):
            if type(data.get("version")) is not int:
                raise ValueError("版本必须是整数")
            params = data.get("params")
            if isinstance(params, dict) and type(params.get("denoise")) is not int:
                raise ValueError("去杂选项必须是整数")
        return data

    @model_validator(mode="after")
    def validate_grid(self) -> "Project":
        """同时验证长度、索引、颜色硬上限以及名称/时间。"""
        count = PALETTE_COUNTS.get(self.paletteId)
        if count is None or not self.name.strip():
            raise ValueError("未知色卡或空名称")
        datetime.fromisoformat(self.updatedAt.replace("Z", "+00:00"))
        cells = self.pattern.cells
        if len(cells) != self.pattern.width * self.pattern.height:
            raise ValueError("网格长度不匹配")
        if any(i < -1 or i >= count for i in cells) or len({i for i in cells if i >= 0}) > self.params.maxColors:
            raise ValueError("颜色索引或数量无效")
        self.name = self.name.strip()
        return self


def parse_project(raw: str) -> dict:
    """在解析前限制 JSON 大小，拒绝非有限数及未知协议。"""
    if len(raw.encode("utf-8")) > 1024 * 1024:
        raise HTTPException(413, "项目数据不能超过 1MB")
    try:
        return Project.model_validate(json.loads(raw)).model_dump()
    except (ValidationError, ValueError, TypeError, RecursionError) as error:
        raise HTTPException(422, "图纸协议、参数或网格无效") from error


class RenameRequest(BaseModel):
    """重命名也必须携带读取时的版本。"""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=128)
    revision: int = Field(ge=1)
