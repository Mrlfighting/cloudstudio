"""图片协同编辑的消息处理逻辑（由 RabbitMQ 消费者或降级回退路径调用）。

承载原 collab.py 消息分支：抢锁 / 更新状态 / 落库 / 广播 / 定向发送。
落库通过注入的 ``persist`` 回调完成，保持基础设施与业务层解耦。
"""

from collections.abc import Awaitable, Callable
from typing import Any

from .broker import Handler
from .lock import CollabLock
from .manager import RoomManager
from .models import (
    PictureEditMessageType,
    PictureEditRequestMessage,
    PictureEditResponseMessage,
)

Persist = Callable[[int, dict[str, Any]], Awaitable[None]]


async def process_message(
    manager: RoomManager,
    lock: CollabLock,
    space_id: int,
    picture_id: int,
    user_id: int,
    user_brief: dict[str, Any],
    msg: PictureEditRequestMessage,
    persist: Persist,
) -> None:
    """处理一条协同编辑消息：抢锁 / 更新状态 / 落库 / 广播 / 定向发送。"""

    if msg.type == PictureEditMessageType.ENTER_EDIT:
        if await lock.try_acquire(space_id, picture_id, user_id):
            await manager.broadcast(
                space_id,
                picture_id,
                PictureEditResponseMessage(
                    type=PictureEditMessageType.ENTER_EDIT,
                    message="开始编辑",
                    edit_state=manager.get_state(space_id, picture_id),
                    user=user_brief,
                ),
            )
        else:
            await manager.send_to(
                space_id,
                picture_id,
                user_id,
                PictureEditResponseMessage(
                    type=PictureEditMessageType.ERROR,
                    message="当前已有成员正在编辑，你处于只读模式",
                ),
            )

    elif msg.type == PictureEditMessageType.EDIT_ACTION:
        if await lock.get_holder(space_id, picture_id) != user_id:
            await manager.send_to(
                space_id,
                picture_id,
                user_id,
                PictureEditResponseMessage(
                    type=PictureEditMessageType.ERROR,
                    message="你不是当前编辑者，无法执行操作",
                ),
            )
            return
        if msg.edit_action is None:
            return
        if msg.edit_state is not None:
            manager.update_state(space_id, picture_id, msg.edit_state)
        await manager.broadcast(
            space_id,
            picture_id,
            PictureEditResponseMessage(
                type=PictureEditMessageType.EDIT_ACTION,
                edit_action=msg.edit_action,
                edit_state=manager.get_state(space_id, picture_id),
                user=user_brief,
            ),
        )

    elif msg.type == PictureEditMessageType.SAVE:
        if await lock.get_holder(space_id, picture_id) != user_id:
            await manager.send_to(
                space_id,
                picture_id,
                user_id,
                PictureEditResponseMessage(
                    type=PictureEditMessageType.ERROR,
                    message="你不是当前编辑者，无法保存",
                ),
            )
            return
        if msg.edit_state is None:
            return
        # 落库（非破坏性，覆盖式，仅 rotation + crop，不含 zoom）
        await persist(picture_id, msg.edit_state.to_persisted())
        await manager.broadcast(
            space_id,
            picture_id,
            PictureEditResponseMessage(
                type=PictureEditMessageType.INFO,
                message="已保存",
                edit_state=msg.edit_state,
                user=user_brief,
            ),
        )

    elif msg.type == PictureEditMessageType.EXIT_EDIT:
        if await lock.release(space_id, picture_id, user_id):
            await manager.broadcast(
                space_id,
                picture_id,
                PictureEditResponseMessage(
                    type=PictureEditMessageType.EXIT_EDIT,
                    message="结束编辑",
                    user=user_brief,
                ),
            )


def make_room_handler(
    manager: RoomManager,
    lock: CollabLock,
    space_id: int,
    picture_id: int,
    persist: Persist,
) -> Handler:
    """构造房间的 RabbitMQ 消息处理器：解包信封并调用 process_message。"""

    async def handler(payload: dict[str, Any]) -> None:
        user_id = payload["user_id"]
        user_brief = payload["user"]
        msg = PictureEditRequestMessage.model_validate(payload["message"])
        await process_message(manager, lock, space_id, picture_id, user_id, user_brief, msg, persist)

    return handler
