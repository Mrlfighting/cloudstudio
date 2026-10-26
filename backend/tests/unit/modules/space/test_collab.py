"""团队空间图片协同编辑 WebSocket 端点测试（模拟会话、共享锁与广播；授权数据使用临时 PostgreSQL）。"""

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import src.modules.space.collab as collab_module
from src.infrastructure.auth.setup import auth
from src.infrastructure.image_collab import set_collab_manager
from src.interfaces.main import app
from src.modules.pictures.crud import crud_pictures
from src.modules.pictures.schemas import PictureCreateInternal, PictureRead
from src.modules.space.enums import SpaceRole
from src.modules.space.service import SpaceService


class FakeWebSocket:
    """模拟 Starlette WebSocket：cookies / accept / receive / send / close。"""

    def __init__(self, cookies: dict, incoming: list[dict]):
        self.cookies = cookies
        self.headers = {"origin": "https://test"}
        self.url = "wss://test/api/v1/spaces/1/pictures/1/collab"
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

    async def receive_text(self) -> str:
        """生产入口按文本字节长度检查消息。"""
        return json.dumps(await self.receive_json())

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


class FakeLock:
    """内存版编辑锁，替代 Redis 锁。"""

    def __init__(self) -> None:
        self.holder: int | None = None
        self.state = None
        self.revision = 0

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

    @asynccontextmanager
    async def serialized(self, *args):
        """单连接测试的命令串行临界区。"""
        yield

    async def get_state(self, *args):
        """模拟共享工作状态。"""
        return self.state

    async def set_state(self, space_id, picture_id, state):
        """保留工作状态供下一条命令读取。"""
        self.state = state

    async def next_revision(self, *args):
        """模拟共享广播序号。"""
        self.revision += 1
        return self.revision


class FakeBroker:
    """只广播已经处理的事件，不消费或再次执行客户端命令。"""

    available = True

    async def ensure_connected(self):
        """模拟可用依赖。"""

    async def subscribe(self, space_id, picture_id, handler):
        """注册结果订阅。"""
        self.handler = handler

    async def publish(self, space_id, picture_id, payload):
        """本实例也会收到消息，序号保证仅投递一次。"""
        await self.handler(payload)

    async def unsubscribe(self, *args):
        """模拟回收专属订阅。"""


@pytest.fixture
def collab_env(monkeypatch, db_session: AsyncSession, test_user: dict, test_user_2: dict):
    """准备团队+图片+成员；替换 DB 会话 / 锁 / broker（原连接执行命令，broker 只转发事件）。"""
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
    monkeypatch.setattr(collab_module, "get_collab_broker", lambda: FakeBroker())
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
async def test_untrusted_origin_rejected(collab_env):
    """携带 Cookie 的跨站连接仍必须被拒绝。"""
    ws = FakeWebSocket(cookies={"session_id": "s"}, incoming=[])
    ws.headers["origin"] = "https://evil.invalid"
    await collab_module.collab_websocket(ws, space_id=1, picture_id=1)
    assert ws.closed == 4403 and not ws.accepted


@pytest.mark.asyncio
async def test_removed_editor_cannot_save_existing_connection(collab_env, monkeypatch, db_session, test_user, test_user_2):
    """连接后被移除的成员不能使用旧连接继续保存。"""
    team, pic = await collab_env()

    async def session(*args, **kwargs):
        """模拟仍未过期的会话，验证撤权检查独立生效。"""
        return SimpleNamespace(user_id=test_user_2["id"])

    monkeypatch.setattr(auth.sessions, "validate_session", session)

    class RevokedSocket(FakeWebSocket):
        """在 ENTER_EDIT 后、SAVE 前由团队管理员撤销成员资格。"""

        async def receive_text(self):
            if self._incoming and self._incoming[0]["type"] == "SAVE":
                await SpaceService().remove_member(db_session, team["id"], test_user_2["id"])
            return await super().receive_text()

    ws = RevokedSocket({"session_id": "s"}, [{"type": "ENTER_EDIT"}, {"type": "SAVE", "edit_state": {"rotation": 90}}])
    await collab_module.collab_websocket(ws, team["id"], pic["id"])
    assert ws.closed == 4403
    saved = await crud_pictures.get(db=db_session, id=pic["id"])
    assert not saved.get("edit_state")


@pytest.mark.asyncio
async def test_mounted_websocket_has_no_http_only_dependencies(collab_env, monkeypatch, test_db_url, test_user):
    """通过实际挂载的 ASGI WebSocket 路由保存，防止误接 HTTP Request/CSRF 依赖。"""
    team, pic = await collab_env()

    @asynccontextmanager
    async def independent_session():
        """TestClient 使用另一个事件循环，连接不能从测试主循环复用。"""
        engine = create_async_engine(test_db_url, poolclass=NullPool)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                yield db
        finally:
            await engine.dispose()

    async def session(*args, **kwargs):
        """测试会话仅用于隔离网络依赖，资源授权仍读取临时数据库。"""
        return SimpleNamespace(user_id=test_user["id"])

    monkeypatch.setattr(collab_module, "local_session", independent_session)
    monkeypatch.setattr(auth.sessions, "validate_session", session)
    client = TestClient(app)
    with client.websocket_connect(f"/api/v1/spaces/{team['id']}/pictures/{pic['id']}/collab",
                                  headers={"origin": "http://testserver", "cookie": "session_id=test"}) as socket:
        assert socket.receive_json()["type"] == "INFO"
        socket.send_json({"type": "ENTER_EDIT"})
        assert socket.receive_json()["type"] == "ENTER_EDIT"
        socket.send_json({"type": "SAVE", "edit_state": {"rotation": 90}})
        assert socket.receive_json()["message"] == "已保存"


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
