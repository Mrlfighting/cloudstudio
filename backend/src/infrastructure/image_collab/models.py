"""图片协同编辑的消息模型与编辑状态（基础设施层，与业务解耦）。

消息流（客户端 ↔ 服务端）：
- ENTER_EDIT / EXIT_EDIT：进入 / 退出编辑态（编辑锁的获取与释放）
- EDIT_ACTION：执行编辑操作（放大/缩小/左旋/右旋/裁剪）
- SAVE：保存当前编辑状态（落库，非破坏性）
- INFO / ERROR：通知 / 错误
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class PictureEditMessageType(StrEnum):
    """图片编辑消息类型。"""

    INFO = "INFO"
    ERROR = "ERROR"
    ENTER_EDIT = "ENTER_EDIT"
    EXIT_EDIT = "EXIT_EDIT"
    EDIT_ACTION = "EDIT_ACTION"
    SAVE = "SAVE"


class PictureEditAction(StrEnum):
    """图片编辑动作。"""

    ZOOM_IN = "ZOOM_IN"
    ZOOM_OUT = "ZOOM_OUT"
    ROTATE_LEFT = "ROTATE_LEFT"
    ROTATE_RIGHT = "ROTATE_RIGHT"
    CROP = "CROP"


class CropRect(BaseModel):
    """裁剪矩形（坐标语义由前端约定，通常为相对原图的像素坐标）。"""

    x: int
    y: int
    width: int
    height: int


class PictureEditState(BaseModel):
    """图片编辑状态：旋转角度 + 缩放（仅视图）+ 裁剪框。"""

    rotation: int = 0  # 0 / 90 / 180 / 270
    zoom: float = 1.0  # 仅视图变换，不落库
    crop: CropRect | None = None

    def to_persisted(self) -> dict[str, Any]:
        """转成落库的编辑参数（非破坏性，不含 zoom）。"""
        return {
            "rotation": self.rotation,
            "crop": self.crop.model_dump() if self.crop else None,
        }


class PictureEditRequestMessage(BaseModel):
    """客户端 → 服务端的编辑请求消息。"""

    type: PictureEditMessageType
    edit_action: PictureEditAction | None = None
    edit_state: PictureEditState | None = None


class PictureEditResponseMessage(BaseModel):
    """服务端 → 客户端的编辑响应消息。"""

    type: PictureEditMessageType
    message: str | None = None
    edit_action: PictureEditAction | None = None
    edit_state: PictureEditState | None = None
    user: dict[str, Any] | None = None
