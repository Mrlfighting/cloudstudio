"""邮箱测试只使用根fixture创建的临时PostgreSQL，不发真实邮件。"""

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.interfaces.main import app
from src.modules.email_verification.config import get_mail_settings
from src.modules.email_verification.rate_limit import MailLimiter, get_mail_limiter


@pytest.fixture
def mail_env(monkeypatch):
    """测试凭据仅存在测试进程，实际.env保持不变。"""
    cfg = get_mail_settings()
    for field, value in {
        "enabled": True,
        "smtp_host": "127.0.0.1",
        "smtp_username": "sender@example.com",
        "smtp_from": "sender@example.com",
        "smtp_password": SecretStr("test-only-not-a-real-password"),
        "token_secret": SecretStr("test-only-email-token-secret-32-bytes"),
        "payload_encryption_key": SecretStr(Fernet.generate_key().decode()),
    }.items():
        monkeypatch.setattr(cfg, field, value)
    return cfg


@pytest_asyncio.fixture
async def mail_limits(client, mail_env):
    """只替换本模块限流，不让测试消耗开发环境计数。"""
    limiter = AsyncMock(spec=MailLimiter)
    app.dependency_overrides[get_mail_limiter] = lambda: limiter
    return limiter


@pytest_asyncio.fixture(autouse=True)
async def install_mail_limits(mail_limits):
    """注册扩展与邮箱接口使用相同的隔离限流依赖。"""
    yield


@pytest_asyncio.fixture
async def email_client(client, test_user, mail_env):
    """真实登录和CSRF，只替换邮件限流以隔离已有开发Redis。"""
    limiter = AsyncMock(spec=MailLimiter)
    app.dependency_overrides[get_mail_limiter] = lambda: limiter
    response = await client.post(
        "/api/v1/auth/login", data={"username": test_user["username"], "password": test_user["password"]}
    )
    assert response.status_code == 200, response.text
    client.headers.update({"X-CSRF-Token": response.json()["csrf_token"], "X-Expected-User-ID": str(test_user["id"])})
    return client
