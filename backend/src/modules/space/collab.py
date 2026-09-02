"""团队空间图片协同编辑 WebSocket 端点。

鉴权：复用 crudauth Session Cookie（握手时从 ``websocket.cookies`` 取 session_id）。
权限：仅团队空间内拥有编辑权限（admin/editor）的成员可连接。

消息流：接收 → 发布到 RabbitMQ（薄生产者）；RabbitMQ 不可用时降级为同步处理。
广播/锁/落库由进程内消费者（或降级路径）经 RoomManager / Redis 锁完成。
"""

from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...infrastructure.auth.setup import auth
from ...infrastructure.database.session import local_session
from ...infrastructure.image_collab import (
    PictureEditMessageType,
    PictureEditRequestMessage,
    PictureEditResponseMessage,
    get_collab_broker,
    get_collab_lock,
    get_collab_manager,
    make_room_handler,
    process_message,
)
from ..pictures.crud import crud_pictures
from ..user.crud import crud_users
from .dependencies import _get_team_member_role
from .rbac import WRITE, has_permission
from .service import SpaceService

router = APIRouter(tags=["Spaces"])


def _user_brief(user: dict[str, Any]) -> dict[str, Any]:
    """从用户 dict 提取广播用的简要信息。"""
    return {"id": user["id"], "name": user.get("name"), "username": user.get("username")}


async def _persist_edit_state(picture_id: int, edit_state: dict[str, Any]) -> None:
    """保存协同编辑参数（落库回调，注入给 process_message）。"""
    async with local_session() as db:
        await SpaceService().save_picture_edit_state(db, picture_id, edit_state)


@router.websocket("/{space_id}/pictures/{picture_id}/collab")
async def collab_websocket(websocket: WebSocket, space_id: int, picture_id: int) -> None:
    """图片协同编辑：鉴权 + 编辑权限 + 发布消息（RabbitMQ 或降级同步）。"""
    # 1. 鉴权：session cookie → validate_session → user_id
    session_id = websocket.cookies.get(auth.sessions.session_cookie_name)
    session = await auth.sessions.validate_session(session_id) if session_id else None
    if session is None:
        await websocket.close(code=4401)
        return

    async with local_session() as db:
        user = await crud_users.get(db=db, id=session.user_id, is_deleted=False)
    if not user:
        await websocket.close(code=4401)
        return

    # 2. 权限：图片存在且属于该空间 + 用户有编辑权限（admin/editor）
    async with local_session() as db:
        picture = await crud_pictures.get(db=db, id=picture_id, is_deleted=False)
    if not picture or picture.get("space_id") != space_id:
        await websocket.close(code=4404)
        return

    async with local_session() as db:
        role = await _get_team_member_role(db, space_id, session.user_id)
    if role is None or not has_permission(role, WRITE):
        await websocket.close(code=4403)
        return

    await websocket.accept()

    manager = get_collab_manager()
    lock = get_collab_lock()
    broker = get_collab_broker()
    brief = _user_brief(user)
    user_id = session.user_id

    # 3. 入房；首个连接则为该房间订阅 broker 消费者
    state, is_first = await manager.join(space_id, picture_id, websocket, {**brief, "can_edit": True}, can_edit=True)
    if is_first and broker is not None and broker.available and lock is not None:
        await broker.subscribe(
            space_id, picture_id, make_room_handler(manager, lock, space_id, picture_id, _persist_edit_state)
        )

    # 4. 初始同步（直接发送，不经 broker）
    holder = await lock.get_holder(space_id, picture_id) if lock is not None else None
    await manager.broadcast(
        space_id,
        picture_id,
        PictureEditResponseMessage(type=PictureEditMessageType.INFO, message="有成员加入", edit_state=state, user=brief),
    )
    sync_msg = "当前已有成员正在编辑，你处于只读模式" if (holder is not None and holder != user_id) else "已连接"
    await websocket.send_json(
        PictureEditResponseMessage(
            type=PictureEditMessageType.INFO,
            message=sync_msg,
            edit_state=state,
        ).model_dump(mode="json")
    )

    try:
        while True:
            raw = await websocket.receive_json()
            try:
                msg = PictureEditRequestMessage.model_validate(raw)
            except Exception:
                await websocket.send_json(
                    PictureEditResponseMessage(
                        type=PictureEditMessageType.ERROR,
                        message="消息格式错误",
                    ).model_dump(mode="json")
                )
                continue

            if broker is not None and broker.available and lock is not None:
                # 薄生产者：发布到 RabbitMQ，由进程内消费者异步处理
                await broker.publish(
                    space_id,
                    picture_id,
                    {"user_id": user_id, "user": brief, "message": msg.model_dump(mode="json")},
                )
            elif lock is not None:
                # 降级回退：RabbitMQ 不可用时同步处理
                await process_message(manager, lock, space_id, picture_id, user_id, brief, msg, _persist_edit_state)

    except WebSocketDisconnect:
        pass
    finally:
        # 断连：若持有锁则释放并广播 EXIT_EDIT
        if lock is not None:
            released = await lock.release(space_id, picture_id, user_id)
            if released:
                await manager.broadcast(
                    space_id,
                    picture_id,
                    PictureEditResponseMessage(
                        type=PictureEditMessageType.EXIT_EDIT,
                        message="编辑者已离开，编辑锁已释放",
                        user=brief,
                    ),
                )
        # 离开房间；最后一个连接则取消订阅
        is_last = await manager.leave(space_id, picture_id, websocket)
        if is_last and broker is not None and broker.available:
            await broker.unsubscribe(space_id, picture_id)
