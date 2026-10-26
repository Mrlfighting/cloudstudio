"""协同命令在原连接完成鉴权和串行处理，RabbitMQ 只广播已经处理的结果。"""

import asyncio
import time
from contextlib import suppress
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from ...infrastructure.auth.setup import auth
from ...infrastructure.config.settings import get_settings
from ...infrastructure.database.session import local_session
from ...infrastructure.image_collab import (
    PictureEditMessageType,
    PictureEditRequestMessage,
    PictureEditResponseMessage,
    PictureEditState,
    get_collab_broker,
    get_collab_lock,
    get_collab_manager,
    process_message,
)
from ..pictures.models import Picture
from ..user.models import User
from .enums import SpaceRole, SpaceStatus, SpaceType
from .models import Space, SpaceUser
from .rbac import WRITE, has_permission

router = APIRouter(tags=["Spaces"])


class _Denied(Exception):
    """只携带关闭码，不向客户端透露他人的资源详情。"""

    def __init__(self, code: int) -> None:
        self.code = code


def _allowed_origin(websocket: WebSocket) -> bool:
    """浏览器必须提供明确允许的 Origin，通配符不授权任意站点。"""
    origin = websocket.headers.get("origin", "")
    parsed = urlsplit(str(websocket.url))
    same_origin = f"{'https' if parsed.scheme == 'wss' else 'http'}://{parsed.netloc}"
    return bool(origin and origin in {same_origin, *get_settings().CORS_ORIGINS_LIST} and origin != "*")


async def _authorize(db, session_id: str | None, space_id: int, picture_id: int, *, locked: bool = False):
    """逐次校验会话、用户、空间和成员；写入时锁住授权相关行以免检查后被撤权。"""
    session = await auth.sessions.validate_session(session_id) if session_id else None
    if session is None:
        raise _Denied(4401)
    query: Any = select(User).where(User.id == session.user_id, User.is_deleted.is_(False))
    user = (await db.execute(query.with_for_update() if locked else query)).scalar_one_or_none()
    if user is None:
        raise _Denied(4401)
    query = select(Space).where(
        Space.id == space_id,
        Space.is_deleted.is_(False),
        Space.space_type == SpaceType.TEAM,
        Space.status == SpaceStatus.ACTIVE.value,
    )
    space = (await db.execute(query.with_for_update() if locked else query)).scalar_one_or_none()
    if space is None:
        raise _Denied(4403)
    query = select(SpaceUser).where(SpaceUser.space_id == space_id, SpaceUser.user_id == session.user_id)
    member = (await db.execute(query.with_for_update() if locked else query)).scalar_one_or_none()
    if member is None or not has_permission(SpaceRole(member.space_role), WRITE):
        raise _Denied(4403)
    query = select(Picture).where(Picture.id == picture_id, Picture.space_id == space_id, Picture.is_deleted.is_(False))
    picture = (await db.execute(query.with_for_update() if locked else query)).scalar_one_or_none()
    if picture is None:
        raise _Denied(4404)
    return user, picture


class _Responses:
    """缓冲单条命令的响应，数据库提交后才向客户端宣告成功。"""

    def __init__(self, state) -> None:
        self.state = state
        self.events: list[tuple[int | None, Any]] = []

    def get_state(self, space_id, picture_id):
        """命令状态独立于异步到达的广播，避免旧事件覆盖正在计算的新状态。"""
        return self.state

    def update_state(self, space_id, picture_id, state):
        """仅在本条命令的缓冲区更新。"""
        self.state = state
        return state

    async def broadcast(self, space_id, picture_id, message):
        """记录房间广播。"""
        self.events.append((None, message))

    async def send_to(self, space_id, picture_id, user_id, message):
        """记录定向错误，不将个人提示广播给他人。"""
        self.events.append((user_id, message))


@router.websocket("/{space_id}/pictures/{picture_id}/collab")
async def collab_websocket(websocket: WebSocket, space_id: int, picture_id: int) -> None:
    """限制消息尺寸、速率和执行时长；共享依赖故障时暂停协同写入。"""
    if not _allowed_origin(websocket):
        await websocket.close(code=4403)
        return
    session_id = websocket.cookies.get(auth.sessions.session_cookie_name)
    manager, lock, broker = get_collab_manager(), get_collab_lock(), get_collab_broker()
    joined = False
    user_id: int | None = None
    heartbeat = None

    async def still_authorized() -> bool:
        """所有出站消息发送前重新检查，撤权或退出后不继续接收私有编辑内容。"""
        try:
            async with local_session() as db:
                await _authorize(db, session_id, space_id, picture_id)
            return True
        except Exception:
            return False

    async def deliver(payload):
        """跨实例事件只更新视图，不重复执行命令和数据库写入。"""
        await manager.deliver(space_id, picture_id, payload)

    async def maintain_lease():
        """空闲连接也检查撤权并为当前编辑者续租，避免操作数十秒后突然不能保存。"""
        try:
            while True:
                await asyncio.sleep(max(0.1, min(10, get_settings().COLLAB_LOCK_TTL / 3)))
                async with asyncio.timeout(3):
                    if not await still_authorized():
                        await websocket.close(code=4403)
                        return
                    if lock is not None and user_id is not None and await lock.get_holder(space_id, picture_id) == user_id:
                        await lock.try_acquire(space_id, picture_id, user_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            with suppress(Exception):
                await websocket.close(code=1013)

    async def emit(target, response):
        """先发布再本地投递，重复的本地队列消息由共享序号去重。"""
        if lock is None or broker is None:
            raise RuntimeError("协同依赖不可用")
        payload = {
            "revision": await lock.next_revision(space_id, picture_id),
            "target_user_id": target,
            "response": response.model_dump(mode="json"),
        }
        await broker.publish(space_id, picture_id, payload)
        await manager.deliver(space_id, picture_id, payload)

    try:
        async with asyncio.timeout(5):
            async with local_session() as db:
                user, picture = await _authorize(db, session_id, space_id, picture_id)
                user_id = user.id
                brief = {"id": user.id, "name": user.name, "username": user.username}
                persisted = PictureEditState.model_validate(picture.edit_state or {})
            if lock is None or broker is None:
                raise RuntimeError("协同依赖未启用")
            await broker.ensure_connected()
            await broker.subscribe(space_id, picture_id, deliver)
            async with lock.serialized(space_id, picture_id):
                initial = await lock.get_state(space_id, picture_id) or persisted
                await websocket.accept()
                state, _ = await manager.join(
                    space_id, picture_id, websocket, brief, can_edit=True, initial_state=initial, authorize=still_authorized
                )
                joined = True
        await websocket.send_json({"type": "INFO", "message": "已连接", "edit_state": state.model_dump()})
        heartbeat = asyncio.create_task(maintain_lease())
        window_start, count = time.monotonic(), 0
        while True:
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > 16_384:
                await websocket.close(code=1009)
                break
            now = time.monotonic()
            if now - window_start >= 1:
                window_start, count = now, 0
            count += 1
            if count > 30:
                await websocket.close(code=4429)
                break
            try:
                message = PictureEditRequestMessage.model_validate_json(raw)
            except (ValueError, TypeError):
                await websocket.send_json({"type": "ERROR", "message": "消息格式错误"})
                continue
            async with asyncio.timeout(5):
                await broker.ensure_connected()
                async with lock.serialized(space_id, picture_id):
                    async with local_session() as db:
                        _, latest_picture = await _authorize(db, session_id, space_id, picture_id, locked=True)
                        current = await lock.get_state(space_id, picture_id) or PictureEditState.model_validate(
                            latest_picture.edit_state or {}
                        )
                        responses = _Responses(current)

                        async def persist(pid, edit_state):
                            """授权行锁仍在当前事务内，保存失败不发送成功事件。"""
                            picture = await db.get(Picture, pid)
                            if picture is None:
                                raise _Denied(4404)
                            picture.edit_state = edit_state
                            await db.flush()

                        await process_message(responses, lock, space_id, picture_id, user_id, brief, message, persist)
                        await db.commit()
                    updated = responses.state
                    if updated is not None:
                        await lock.set_state(space_id, picture_id, updated)
                    for target, response in responses.events:
                        await emit(target, response)
    except _Denied as exc:
        await websocket.close(code=exc.code)
    except WebSocketDisconnect:
        pass
    except Exception:
        # 不广播底层连接串或异常消息；客户端重连后重新取共享/落库状态。
        await websocket.close(code=1013)
    finally:
        if heartbeat is not None:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
        if joined and lock is not None and broker is not None and user_id is not None:
            try:
                if await lock.release(space_id, picture_id, user_id):
                    await emit(
                        None,
                        PictureEditResponseMessage(
                            type=PictureEditMessageType.EXIT_EDIT, message="编辑者已离开", user={"id": user_id}
                        ),
                    )
            except Exception:
                pass
            if await manager.leave(space_id, picture_id, websocket):
                try:
                    await broker.unsubscribe(space_id, picture_id)
                except Exception:
                    pass
