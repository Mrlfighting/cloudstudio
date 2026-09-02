"""图片协同编辑工具包（基础设施层）。

提供房间管理、Redis 编辑锁、RabbitMQ 消息缓冲、消息模型，与业务代码解耦。
"""

from .broker import CollabBroker
from .consumer import make_room_handler, process_message
from .facade import (
    get_collab_broker,
    get_collab_lock,
    get_collab_manager,
    set_collab_broker,
    set_collab_lock,
    set_collab_manager,
)
from .lock import CollabLock
from .manager import RoomManager
from .models import (
    CropRect,
    PictureEditAction,
    PictureEditMessageType,
    PictureEditRequestMessage,
    PictureEditResponseMessage,
    PictureEditState,
)

__all__ = [
    "RoomManager",
    "CollabLock",
    "CollabBroker",
    "CropRect",
    "PictureEditAction",
    "PictureEditMessageType",
    "PictureEditRequestMessage",
    "PictureEditResponseMessage",
    "PictureEditState",
    "process_message",
    "make_room_handler",
    "get_collab_manager",
    "set_collab_manager",
    "get_collab_lock",
    "set_collab_lock",
    "get_collab_broker",
    "set_collab_broker",
]
