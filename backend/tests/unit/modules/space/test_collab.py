"""团队空间图片协同编辑 WebSocket 端点测试（mock 鉴权/锁/DB；broker 不可用走降级回退）。"""

from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi import WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

import src.modules.space.collab as collab_module
from src.infrastructure.auth.setup import auth
from src.infrastructure.image_collab import set_collab_manager
from src.modules.pictures.crud import crud_pictures
from src.modules.pictures.schemas import PictureCreateInternal, PictureRead
from src.modules.space.enums import SpaceRole
from src.modules.space.service import SpaceService


class FakeWebSocket:
    """模拟 Starlette WebSocket：cookies / accept / receive / send / close。"""

    def __init__(self, cookies: dict, incoming: list[dict]):
        self.cookies = cookies
        self._incoming = list(incoming)
        self.sent: list[dict] = []
        self.closed: int | None = None
        self.accepted = False

    async def close(self, code: int = 1000) -> None:
        self.closed = code

    async def accept(self) -> None:
        self.accepted = True

    async def receive_json(self) -> dict:
        if self._incoming:
            return self._incoming.pop(0)
        raise WebSocketDisconnect(code=1000)

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


class FakeLock:
    """内存版编辑锁，替代 Redis 锁。"""

    def __init__(self) -> None:
        self.holder: int | None = None

    async def try_acquire(self, space_id: int, picture_id: int, user_id: int) -> bool:
        if self.holder is None or self.holder == user_id:
            self.holder = user_id
            return True
        return False

    async def release(self, space_id: int, picture_id: int, user_id: int) -> bool:
        if self.holder == user_id:
            self.holder = None
            return True
        return False

    async def get_holder(self, space_id: int, picture_id: int) -> int | None:
        return self.holder


@pytest.fixture
def collab_env(monkeypatch, db_session: AsyncSession, test_user: dict, test_user_2: dict):
    """准备团队+图片+成员；替换 DB 会话 / 锁 / broker（broker 不可用→降级回退）。"""
    set_collab_manager(None)
    fake_lock = FakeLock()

    async def _setup():
        service = SpaceService()
        team = await service.create_team(db_session, "团队", test_user)  # test_user = admin
        await service.add_member(db_session, team["id"], test_user_2["id"], SpaceRole.EDITOR)
        pic = await crud_pictures.create(
            db=db_session,
            object=PictureCreateInternal(
                url="https://example.com/pic.png",
                name="图片",
                user_id=test_user["id"],
                status="approved",
                space_id=team["id"],
            ),
            schema_to_select=PictureRead,
        )
        return team, pic

    @asynccontextmanager
    async def _fake_local_session():
        yield db_session

    monkeypatch.setattr(collab_module, "local_session", _fake_local_session)
    monkeypatch.setattr(collab_module, "get_collab_lock", lambda: fake_lock)
    monkeypatch.setattr(collab_module, "get_collab_broker", lambda: None)
    return _setup


@pytest.mark.asyncio
async def test_unauthenticated_closed(collab_env, monkeypatch):
    """未登录（无有效会话）→ 关闭 4401。"""
    async def _no_session(session_id, update_activity=True):
        return None

    monkeypatch.setattr(auth.sessions, "validate_session", _no_session)
    ws = FakeWebSocket(cookies={}, incoming=[])
    await collab_module.collab_websocket(ws, space_id=1, picture_id=1)
    assert ws.closed == 4401
    assert not ws.accepted


@pytest.mark.asyncio
async def test_viewer_rejected(collab_env, monkeypatch, db_session, test_user, test_user_2):
    """viewer（无编辑权限）→ 关闭 4403。"""
    team, pic = await collab_env()
    await SpaceService().update_member_role(db_session, team["id"], test_user_2["id"], SpaceRole.VIEWER)

    async def _fake_validate_session(session_id, update_activity=True):
        return SimpleNamespace(user_id=test_user_2["id"])

    monkeypatch.setattr(auth.sessions, "validate_session", _fake_validate_session)
    ws = FakeWebSocket(cookies={"session_id": "s"}, incoming=[])
    await collab_module.collab_websocket(ws, space_id=team["id"], picture_id=pic["id"])
    assert ws.closed == 4403
    assert not ws.accepted


@pytest.mark.asyncio
async def test_editor_flow(collab_env, monkeypatch, db_session, test_user):
    """editor：进入编辑→操作广播→保存落库→退出。"""
    team, pic = await collab_env()

    async def _fake_validate_session(session_id, update_activity=True):
        return SimpleNamespace(user_id=test_user["id"])

    monkeypatch.setattr(auth.sessions, "validate_session", _fake_validate_session)
    incoming = [
        {"type": "ENTER_EDIT"},
        {"type": "EDIT_ACTION", "edit_action": "ROTATE_LEFT", "edit_state": {"rotation": 90, "zoom": 1.0, "crop": None}},
        {"type": "SAVE", "edit_state": {"rotation": 90, "zoom": 1.0, "crop": None}},
        {"type": "EXIT_EDIT"},
    ]
    ws = FakeWebSocket(cookies={"session_id": "s"}, incoming=incoming)
    await collab_module.collab_websocket(ws, space_id=team["id"], picture_id=pic["id"])

    assert ws.accepted is True
    assert ws.closed is None
    # 保存落库（非破坏性参数，不含 zoom）
    saved = await crud_pictures.get(db=db_session, id=pic["id"], is_deleted=False)
    assert saved["edit_state"] == {"rotation": 90, "crop": None}
    # 广播了 ENTER_EDIT / EDIT_ACTION / 保存 INFO / EXIT_EDIT
    types = [m["type"] for m in ws.sent]
    assert "ENTER_EDIT" in types
    assert "EDIT_ACTION" in types
    assert "EXIT_EDIT" in types


@pytest.mark.asyncio
async def test_readonly_rejected_edit_action(collab_env, monkeypatch, test_user, test_user_2):
    """他人持锁时，第二个编辑者的 EDIT_ACTION 被拒（只读）。"""
    team, pic = await collab_env()

    async def _fake_a(session_id, update_activity=True):
        return SimpleNamespace(user_id=test_user["id"])

    monkeypatch.setattr(auth.sessions, "validate_session", _fake_a)
    ws_a = FakeWebSocket(cookies={"session_id": "a"}, incoming=[{"type": "ENTER_EDIT"}])
    await collab_module.collab_websocket(ws_a, space_id=team["id"], picture_id=pic["id"])

    async def _fake_b(session_id, update_activity=True):
        return SimpleNamespace(user_id=test_user_2["id"])

    monkeypatch.setattr(auth.sessions, "validate_session", _fake_b)
    ws_b = FakeWebSocket(cookies={"session_id": "b"}, incoming=[{"type": "EDIT_ACTION", "edit_action": "ZOOM_IN"}])
    await collab_module.collab_websocket(ws_b, space_id=team["id"], picture_id=pic["id"])

    errors = [m for m in ws_b.sent if m["type"] == "ERROR"]
    assert errors, "只读用户执行操作应收到 ERROR"
