"""图片协同编辑房间管理器单元测试。"""

from unittest.mock import AsyncMock

import pytest

from src.infrastructure.image_collab import (
    PictureEditMessageType,
    PictureEditResponseMessage,
    PictureEditState,
    RoomManager,
)


@pytest.fixture
def manager() -> RoomManager:
    return RoomManager()


def _ws() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_join_leave_returns_flags(manager: RoomManager):
    """join 返回 (state, is_first)；leave 返回 is_last。"""
    ws1 = _ws()
    ws2 = _ws()

    state, is_first = await manager.join(1, 1, ws1, {"id": 100}, can_edit=True)
    assert is_first is True
    assert isinstance(state, PictureEditState)

    _, not_first = await manager.join(1, 1, ws2, {"id": 200}, can_edit=True)
    assert not_first is False

    assert await manager.leave(1, 1, ws1) is False
    assert await manager.leave(1, 1, ws2) is True


@pytest.mark.asyncio
async def test_update_and_get_state(manager: RoomManager):
    ws = _ws()
    await manager.join(1, 1, ws, {"id": 100}, can_edit=True)
    state = PictureEditState(rotation=90, zoom=1.5)
    assert manager.update_state(1, 1, state) == state
    assert manager.get_state(1, 1) == state


@pytest.mark.asyncio
async def test_broadcast_to_all(manager: RoomManager):
    ws1 = _ws()
    ws2 = _ws()
    await manager.join(1, 1, ws1, {"id": 100}, can_edit=True)
    await manager.join(1, 1, ws2, {"id": 200}, can_edit=True)

    await manager.broadcast(1, 1, PictureEditResponseMessage(type=PictureEditMessageType.INFO, message="hi"))

    ws1.send_json.assert_awaited()
    ws2.send_json.assert_awaited()


@pytest.mark.asyncio
async def test_send_to_specific_user(manager: RoomManager):
    """send_to 只发给指定用户，不影响其他用户。"""
    ws1 = _ws()
    ws2 = _ws()
    await manager.join(1, 1, ws1, {"id": 100}, can_edit=True)
    await manager.join(1, 1, ws2, {"id": 200}, can_edit=True)

    await manager.send_to(1, 1, 100, PictureEditResponseMessage(type=PictureEditMessageType.ERROR, message="只读"))

    ws1.send_json.assert_awaited()
    ws2.send_json.assert_not_awaited()


@pytest.mark.asyncio
async def test_room_empty_after_all_leave(manager: RoomManager):
    ws = _ws()
    await manager.join(1, 1, ws, {"id": 100}, can_edit=True)
    assert await manager.leave(1, 1, ws) is True
    # 空房间被回收：状态不存在
    assert manager.get_state(1, 1) is None
