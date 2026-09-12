"""图片协同编辑的房间管理（纯内存）：连接注册表 + 编辑状态 + 广播/定向发送。

每个 ``(space_id, picture_id)`` 对应一个房间（Room），房间内维护：
- 在线连接（WebSocket → 用户信息）
- 当前编辑状态（旋转 / 缩放 / 裁剪，纯内存；保存由消息处理层落库）

编辑锁已迁到 Redis 分布式锁（见 lock.py），此处不再维护 lock_holder。
"""

from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from .models import PictureEditResponseMessage, PictureEditState


@dataclass
class Room:
    """协同房间：连接集合 + 编辑状态。"""

    key: str
    # WebSocket → {"user_id", "name", "username", "can_edit"}
    connections: dict[WebSocket, dict[str, Any]] = field(default_factory=dict)
    state: PictureEditState = field(default_factory=PictureEditState)

    def is_empty(self) -> bool:
        return not self.connections


class RoomManager:
    """房间管理器：管理连接注册表、编辑状态与广播/定向发送（纯内存单例）。"""

    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    @staticmethod
    def _key(space_id: int, picture_id: int) -> str:
        return f"{space_id}:{picture_id}"

    def _get_or_create_room(self, key: str) -> Room:
        room = self._rooms.get(key)
        if room is None:
            room = Room(key=key)
            self._rooms[key] = room
        return room

    async def join(
        self,
        space_id: int,
        picture_id: int,
        ws: WebSocket,
        user: dict[str, Any],
        can_edit: bool,
        initial_state: PictureEditState | None = None,
    ) -> tuple[PictureEditState, bool]:
        """加入房间；返回 (当前编辑状态, 是否为该房间首个连接)。

        首次创建房间时，可用 ``initial_state``（来自落库 ``pictures.edit_state``）初始化编辑状态，
        避免已保存的旋转/裁剪在刷新后新连接收到默认态。
        """
        key = self._key(space_id, picture_id)
        is_first = key not in self._rooms
        room = self._get_or_create_room(key)
        if is_first and initial_state is not None:
            room.state = initial_state
        room.connections[ws] = {
            "user_id": user["id"],
            "name": user.get("name"),
            "username": user.get("username"),
            "can_edit": can_edit,
        }
        return room.state, is_first

    async def leave(self, space_id: int, picture_id: int, ws: WebSocket) -> bool:
        """离开房间；返回是否为该房间最后一个连接（房间已空被回收）。"""
        key = self._key(space_id, picture_id)
        room = self._rooms.get(key)
        if room is None:
            return False
        room.connections.pop(ws, None)
        if room.is_empty():
            self._rooms.pop(key, None)
            return True
        return False

    def get_state(self, space_id: int, picture_id: int) -> PictureEditState | None:
        room = self._rooms.get(self._key(space_id, picture_id))
        return room.state if room else None

    def update_state(self, space_id: int, picture_id: int, state: PictureEditState) -> PictureEditState | None:
        """更新房间编辑状态，返回新状态。"""
        room = self._rooms.get(self._key(space_id, picture_id))
        if room is None:
            return None
        room.state = state
        return room.state

    async def broadcast(self, space_id: int, picture_id: int, message: PictureEditResponseMessage) -> None:
        """向房间内所有连接广播消息（发送失败忽略，由断连清理）。"""
        room = self._rooms.get(self._key(space_id, picture_id))
        if room is None:
            return
        data = message.model_dump(mode="json")
        for ws in list(room.connections.keys()):
            try:
                await ws.send_json(data)
            except Exception:
                continue

    async def send_to(
        self, space_id: int, picture_id: int, user_id: int, message: PictureEditResponseMessage
    ) -> None:
        """定向发送给房间内指定用户的所有连接（用于 ERROR/INFO 等个人响应）。"""
        room = self._rooms.get(self._key(space_id, picture_id))
        if room is None:
            return
        data = message.model_dump(mode="json")
        for ws, conn in list(room.connections.items()):
            if conn["user_id"] == user_id:
                try:
                    await ws.send_json(data)
                except Exception:
                    continue

    async def close_all(self) -> None:
        """关闭时清空所有房间（应用 shutdown 调用）。"""
        self._rooms.clear()
