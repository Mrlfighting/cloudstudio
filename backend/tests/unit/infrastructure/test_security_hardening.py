"""安全边界、故障隔离及管理后台的独立回归测试。"""

import asyncio
import time
from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from fastapi import APIRouter, FastAPI, UploadFile
from httpx import ASGITransport, AsyncClient
from PIL import Image

from src.infrastructure import images, readiness
from src.infrastructure.app_factory import create_application
from src.infrastructure.config.settings import EnvironmentOption, get_settings
from src.infrastructure.image_collab import CollabLock
from src.interfaces.admin.initialize import create_admin_interface
from src.modules.common.exceptions import ValidationError

pytestmark = pytest.mark.asyncio


async def test_database_failure_changes_readiness_not_liveness(monkeypatch):
    """就绪检查拒绝流量，且不泄露连接串；恢复后自动变为就绪。"""
    database = AsyncMock(side_effect=OSError("private-db-password"))
    monkeypatch.setattr(readiness, "_database", database)
    monkeypatch.setattr(readiness, "_sessions", AsyncMock())
    response = await readiness.readiness_response()
    assert response.status_code == 503 and b"private-db-password" not in response.body
    database.side_effect = None
    assert (await readiness.readiness_response()).status_code == 200


async def test_production_docs_cannot_shadow_authorization():
    """生产文档开启后仍须管理员会话，不存在先匹配的公开副本。"""
    settings = get_settings().model_copy(update={"ENVIRONMENT": EnvironmentOption.PRODUCTION, "RATE_LIMITER_ENABLED": False})
    app = create_application(router=APIRouter(), settings=settings, enable_docs_in_production=True)
    paths = [getattr(route, "path", None) for route in app.routes]
    assert paths.count("/docs") == 1 and paths.count("/openapi.json") == 1
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert (await client.get(path)).status_code == 401


async def test_admin_csrf_cache_cookie_and_logout(monkeypatch):
    """覆盖跨站写入、令牌缺失、合法登录及安全 Cookie，不连接真实数据库。"""
    settings = get_settings()
    for key, value in {
        "ADMIN_ENABLED": True,
        "ADMIN_USERNAME": "test-admin",
        "ADMIN_PASSWORD": "test-only-password",
        "SESSION_SECURE_COOKIES": True,
    }.items():
        monkeypatch.setattr(settings, key, value)
    monkeypatch.setattr("src.interfaces.admin.auth.increment_and_check", AsyncMock(return_value=(1, False)))
    app = FastAPI()
    create_admin_interface(app)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        page = await client.get("/admin/login")
        assert page.status_code == 200 and "no-store" in page.headers["cache-control"]
        token = client.cookies.get("atelier_admin_csrf")
        credentials = {"username": "test-admin", "password": "test-only-password"}
        assert (await client.post("/admin/login", data=credentials)).status_code == 403
        credentials["csrf_token"] = token
        assert (
            await client.post("/admin/login", data=credentials, headers={"Origin": "https://evil.invalid"})
        ).status_code == 403
        login = await client.post("/admin/login", data=credentials, headers={"Origin": "https://test"})
        assert login.status_code == 302
        session_cookies = [
            value for value in login.headers.get_list("set-cookie") if value.startswith("atelier_admin_session=")
        ]
        assert len(session_cookies) == 1
        assert "secure" in session_cookies[0].lower() and "httponly" in session_cookies[0].lower()
        assert (await client.get("/admin/logout")).status_code == 403
        assert (
            await client.get("/admin/logout", headers={"Referer": "https://test/admin/", "X-Admin-CSRF": token})
        ).status_code == 302


async def test_redis_failure_never_grants_edit_lock():
    """两个进程都必须拒绝编辑，不可各自退回内存锁。"""
    for _ in range(2):
        redis = AsyncMock()
        redis.eval.side_effect = redis.get.side_effect = OSError("redis down")
        lock = CollabLock(redis, ttl=30)
        for action in (lock.try_acquire(1, 1, 1), lock.get_holder(1, 1), lock.release(1, 1, 1)):
            with pytest.raises(OSError):
                await action


def png_data():
    """创建可丢弃的小图片字节。"""
    buffer = BytesIO()
    Image.new("RGB", (4, 4)).save(buffer, "PNG")
    return buffer.getvalue()


async def test_image_limits_and_actual_format(monkeypatch):
    """实际格式、字节上限、像素上限及损坏数据均在上传存储前拒绝。"""
    with pytest.raises(ValidationError):
        await images.read_upload_image(UploadFile(BytesIO(b"not an image")))
    data = png_data()
    monkeypatch.setattr(images, "MAX_PIXELS", 1)
    with pytest.raises(ValidationError):
        await images.read_upload_image(UploadFile(BytesIO(data)))
    monkeypatch.setattr(images, "MAX_PIXELS", 25_000_000)
    monkeypatch.setattr(images, "MAX_FILE_SIZE", len(data) - 1)
    with pytest.raises(ValidationError):
        await images.read_upload_image(UploadFile(BytesIO(data)))


async def test_decode_does_not_block_event_loop(monkeypatch):
    """慢解码发生在线程池，主事件循环仍能调度其他任务。"""
    decode = images._decode

    def slow(data):
        time.sleep(0.15)
        return decode(data)

    monkeypatch.setattr(images, "_decode", slow)
    pending = asyncio.create_task(images.read_upload_image(UploadFile(BytesIO(png_data()))))
    await asyncio.sleep(0.03)
    assert not pending.done()
    image = await pending
    assert image.format == "PNG"
    image.preview.close()
