"""真实Session/CSRF与数据库验证：绑定、原子换绑、解绑、注册和兼容性。"""

from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import undefer

from src.interfaces.main import app
from src.modules.email_verification import service
from src.modules.email_verification.crypto import decrypt
from src.modules.email_verification.models import EmailChallenge as Challenge
from src.modules.email_verification.models import EmailOutbox as Job
from src.modules.email_verification.models import now
from src.modules.email_verification.rate_limit import get_mail_limiter
from src.modules.user.models import User

pytestmark = pytest.mark.asyncio
URL = "/api/v1/email"


async def request_code(client, db, path="binding", email="new@example.com"):
    """从仅测试进程可解密的事务载荷取码，不在日志输出。"""
    response = await client.post(f"{URL}/{path}/request", json={"email": email} if path == "binding" else None)
    assert response.status_code == 202, response.text
    request_id = response.json()["request_id"]
    payload = await db.scalar(select(Job.payload).where(Job.challenge_id == UUID(request_id)))
    return request_id, decrypt(payload)["code"]


async def age_requests(db):
    """不等待真实一分钟，使用临时库推进申请时间以测试重发与换绑。"""
    await db.execute(update(Challenge).values(created_at=now() - timedelta(seconds=70)))
    await db.commit()


async def test_bind_change_unbind_and_welcome_once(email_client, db_session, test_user):
    """换绑前保留原地址，确认消费一次，解绑验证当前邮箱，欢迎不重复。"""
    before = test_user["email"]
    request_id, code = await request_code(email_client, db_session, email=" NEW@Example.com ")
    state = (await email_client.get(URL + "/status")).json()
    assert state["email"] == before and state["pending"]["email"] == "new@example.com"
    response = await email_client.post(URL + "/binding/confirm", json={"request_id": request_id, "code": code})
    assert response.status_code == 200, response.text
    assert response.json() == {"email": "new@example.com", "email_verified": True}
    assert (await email_client.post(URL + "/binding/confirm", json={"request_id": request_id, "code": code})).status_code == 400
    await age_requests(db_session)
    next_id, next_code = await request_code(email_client, db_session, email="changed@example.com")
    assert (await email_client.get(URL + "/status")).json()["email"] == "new@example.com"
    assert (
        await email_client.post(URL + "/binding/confirm", json={"request_id": next_id, "code": next_code})
    ).status_code == 200
    await age_requests(db_session)
    unbind_id, unbind_code = await request_code(email_client, db_session, "unbind")
    wrong_purpose = await email_client.post(URL + "/binding/confirm", json={"request_id": unbind_id, "code": unbind_code})
    assert wrong_purpose.status_code == 404
    result = await email_client.post(URL + "/unbind/confirm", json={"request_id": unbind_id, "code": unbind_code})
    assert result.status_code == 200 and result.json() == {"email": None, "email_verified": False}
    assert await db_session.scalar(select(func.count()).select_from(Job).where(Job.kind == "welcome")) == 1


async def test_real_auth_csrf_expected_owner(email_client, client, test_user):
    """失效会话、缺CSRF和旧页账号上下文均不得发起邮件任务。"""
    header = email_client.headers.pop("X-Expected-User-ID")
    assert (await email_client.get(URL + "/status")).status_code == 428
    email_client.headers["X-Expected-User-ID"] = str(test_user["id"] + 999)
    assert (await email_client.post(URL + "/binding/request", json={"email": "new@example.com"})).status_code == 409
    email_client.headers["X-Expected-User-ID"] = header
    csrf = email_client.headers.pop("X-CSRF-Token")
    assert (await email_client.post(URL + "/binding/request", json={"email": "new@example.com"})).status_code == 403
    email_client.headers["X-CSRF-Token"] = csrf
    email_client.cookies.clear()
    assert (await client.get(URL + "/status")).status_code == 401


async def test_wrong_code_counter_persists_and_expires(email_client, db_session):
    """每次400仍提交错误次数，达到5次即使正确码也不放行。"""
    request_id, code = await request_code(email_client, db_session)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        response = await email_client.post(URL + "/binding/confirm", json={"request_id": request_id, "code": wrong})
        assert response.status_code == 400
    await db_session.refresh(await db_session.get(Challenge, UUID(request_id)))
    assert (await db_session.get(Challenge, UUID(request_id))).attempts == 5
    assert (await email_client.post(URL + "/binding/confirm", json={"request_id": request_id, "code": code})).status_code == 400


async def test_resend_invalidates_old_code_and_unbind(email_client, db_session):
    """重发撤销旧码和待投递邮件，旧解绑码不能清除新邮箱。"""
    old_id, old_code = await request_code(email_client, db_session, "unbind")
    assert (await email_client.post(URL + "/binding/request", json={"email": "new@example.com"})).status_code == 429
    await age_requests(db_session)
    request_id, code = await request_code(email_client, db_session)
    assert (await email_client.post(URL + "/unbind/confirm", json={"request_id": old_id, "code": old_code})).status_code == 400
    assert (await email_client.post(URL + "/binding/confirm", json={"request_id": request_id, "code": code})).status_code == 200
    old_job = await db_session.scalar(select(Job).options(undefer(Job.payload)).where(Job.challenge_id == UUID(old_id)))
    assert old_job.status == "cancelled" and old_job.payload is None
    await age_requests(db_session)
    newer_id, newer_code = await request_code(email_client, db_session, email="newer@example.com")
    await db_session.execute(
        update(Challenge).where(Challenge.id == UUID(newer_id)).values(expires_at=now() - timedelta(seconds=1))
    )
    await db_session.commit()
    assert (
        await email_client.post(URL + "/binding/confirm", json={"request_id": newer_id, "code": newer_code})
    ).status_code == 400


async def test_other_account_and_soft_deleted_address(email_client, db_session, test_user, test_user_2):
    """申请归属和邮箱占用都包含完整数据库约束。"""
    request_id, code = await request_code(email_client, db_session)
    email_client.headers["X-Expected-User-ID"] = str(test_user_2["id"])
    # 真实换号而不是只改变预期头。
    login = await email_client.post(
        "/api/v1/auth/login", data={"username": test_user_2["username"], "password": test_user_2["password"]}
    )
    email_client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    assert (await email_client.post(URL + "/binding/confirm", json={"request_id": request_id, "code": code})).status_code == 404
    await db_session.execute(
        update(User).where(User.id == test_user["id"]).values(is_deleted=True, email="Retained@Example.com")
    )
    await db_session.commit()
    response = await email_client.post(URL + "/binding/request", json={"email": "retained@example.com"})
    assert response.status_code == 409


async def test_legacy_profile_and_public_privacy(email_client, db_session, test_user):
    """旧前端原样提交邮箱继续修改资料，匿名名片不再泄漏邮箱与认证资料。"""
    path = "/api/v1/users/" + test_user["username"]
    response = await email_client.patch(path, json={"email": test_user["email"], "name": "新的昵称"})
    assert response.status_code == 200, response.text
    assert (await email_client.patch(path, json={"email": "bypass@example.com"})).status_code == 409
    assert (await email_client.patch(path, json={"email_verified": True})).status_code == 422
    email_client.cookies.clear()
    public = (await email_client.get(path)).json()
    assert public["name"] == "新的昵称" and "email" not in public and "email_verified" not in public
    assert "oauth_provider" not in public and "is_superuser" not in public


async def test_registration_atomic_optional_and_duplicate(client, db_session, mail_env, monkeypatch):
    """注册返回前不访问SMTP/队列，账号、验证码与两封邮件任务同事务落盘。"""
    payload = {"account": "mailnew", "password": "Test-only-123!", "confirm_password": "Test-only-123!"}
    response = await client.post("/api/v1/users/register", json=payload)
    assert response.status_code == 201 and response.json()["email"] is None
    assert await db_session.scalar(select(func.count()).select_from(Job)) == 0
    # 仅带邮箱注册替换限流，任务入库不依赖消息中间件。
    app.dependency_overrides[get_mail_limiter] = lambda: AsyncMock()
    payload.update(account="withmail", email="New@Example.com")
    response = await client.post("/api/v1/users/register", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["email"] is None and not response.json()["email_verified"]
    assert response.json()["email_verification"]["delivery_status"] == "queued"
    assert await db_session.scalar(select(func.count()).select_from(Job)) == 2
    # 模拟任务写入失败，必须连账号一起回滚。
    monkeypatch.setattr(service, "welcome", AsyncMock(side_effect=RuntimeError("测试事务失败")))
    payload.update(account="rollback", email="rollback@example.com")
    assert (await client.post("/api/v1/users/register", json=payload)).status_code == 500
    assert await db_session.scalar(select(User.id).where(User.username == "rollback")) is None


async def test_registration_occupied_case_and_disabled(client, db_session, test_user, mail_env):
    """大小写变体也不可注册；关闭邮件功能不影响无邮箱注册。"""
    payload = {
        "account": "duplicate",
        "password": "Test-only-123!",
        "confirm_password": "Test-only-123!",
        "email": test_user["email"].upper(),
    }
    assert (await client.post("/api/v1/users/register", json=payload)).status_code == 409
    assert await db_session.scalar(select(User.id).where(User.username == "duplicate")) is None
    mail_env.enabled = False
    payload.update(account="disabled", email="valid@example.com")
    assert (await client.post("/api/v1/users/register", json=payload)).status_code == 503
    payload.pop("email")
    assert (await client.post("/api/v1/users/register", json=payload)).status_code == 201


async def test_invalid_body_does_not_log_code(email_client, caplog):
    """包括UUID和类型错误在内，验证码不能出现在全局ValidationError日志中。"""
    marker = "secret-code-never-log"
    response = await email_client.post(URL + "/binding/confirm", json={"request_id": "invalid", "code": marker})
    assert response.status_code == 422 and marker not in caplog.text
    response = await email_client.post(
        "/api/v1/users/register",
        json={"account": "invalidmail", "password": marker, "confirm_password": "mismatch", "email": "invalid"},
    )
    assert response.status_code == 422 and marker not in caplog.text
