"""process_message 消息处理单元测试（mock manager/lock/persist）。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.image_collab import (
    PictureEditAction,
    PictureEditMessageType,
    PictureEditRequestMessage,
    PictureEditState,
    process_message,
)


@pytest.fixture
def manager() -> MagicMock:
    m = MagicMock()
    m.get_state.return_value = PictureEditState()
    m.broadcast = AsyncMock()
    m.send_to = AsyncMock()
    return m


@pytest.fixture
def lock() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def persist() -> AsyncMock:
    return AsyncMock()


BRIEF = {"id": 100, "name": "A", "username": "a"}


@pytest.mark.asyncio
async def test_enter_edit_acquires(manager, lock, persist):
    lock.try_acquire.return_value = True
    await process_message(
        manager, lock, 1, 1, 100, BRIEF, PictureEditRequestMessage(type=PictureEditMessageType.ENTER_EDIT), persist
    )
    manager.broadcast.assert_awaited_once()


@pytest.mark.asyncio
async def test_enter_edit_readonly(manager, lock, persist):
    lock.try_acquire.return_value = False
    await process_message(
        manager, lock, 1, 1, 100, BRIEF, PictureEditRequestMessage(type=PictureEditMessageType.ENTER_EDIT), persist
    )
    manager.send_to.assert_awaited_once()
    manager.broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_action(manager, lock, persist):
    lock.get_holder.return_value = 100
    msg = PictureEditRequestMessage(
        type=PictureEditMessageType.EDIT_ACTION,
        edit_action=PictureEditAction.ROTATE_LEFT,
        edit_state=PictureEditState(rotation=90),
    )
    await process_message(manager, lock, 1, 1, 100, BRIEF, msg, persist)
    manager.update_state.assert_called_once()
    manager.broadcast.assert_awaited_once()


@pytest.mark.asyncio
async def test_edit_action_readonly(manager, lock, persist):
    lock.get_holder.return_value = 200
    msg = PictureEditRequestMessage(
        type=PictureEditMessageType.EDIT_ACTION, edit_action=PictureEditAction.ZOOM_IN
    )
    await process_message(manager, lock, 1, 1, 100, BRIEF, msg, persist)
    manager.send_to.assert_awaited_once()
    manager.broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_save_persists(manager, lock, persist):
    lock.get_holder.return_value = 100
    msg = PictureEditRequestMessage(type=PictureEditMessageType.SAVE, edit_state=PictureEditState(rotation=90))
    await process_message(manager, lock, 1, 1, 100, BRIEF, msg, persist)
    persist.assert_awaited_once_with(1, {"rotation": 90, "crop": None})


@pytest.mark.asyncio
async def test_exit_edit(manager, lock, persist):
    lock.release.return_value = True
    await process_message(
        manager, lock, 1, 1, 100, BRIEF, PictureEditRequestMessage(type=PictureEditMessageType.EXIT_EDIT), persist
    )
    manager.broadcast.assert_awaited_once()
