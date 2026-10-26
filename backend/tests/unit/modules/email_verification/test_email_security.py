"""邮件配置、密码学边界、模板和限流故障的纯单元回归。"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from pydantic import SecretStr, ValidationError

from src.modules.email_verification.config import MailSettings, get_mail_settings
from src.modules.email_verification.crypto import decrypt, digest, encrypt, new_code
from src.modules.email_verification.mail import render
from src.modules.email_verification.rate_limit import MailLimiter
from src.modules.email_verification.schemas import EmailRegistrationRequest, normalize_email


@pytest.fixture
def config(monkeypatch):
    """只在进程内配置测试密钥，禁止真实SMTP连接。"""
    cfg = get_mail_settings()
    monkeypatch.setattr(cfg, "token_secret", SecretStr("test-key-for-email-hmac-over-32-bytes"))
    monkeypatch.setattr(cfg, "payload_encryption_key", SecretStr(Fernet.generate_key().decode()))
    monkeypatch.setattr(cfg, "smtp_from", "sender@example.com")
    return cfg


def test_crypto_context_and_encrypted_payload(config):
    """账号/用途/申请ID不同摘要不同；加密密钥错误不能解密。"""
    request = uuid4()
    code = new_code()
    assert len(code) == 6 and code.isascii() and code.isdigit()
    original = digest(request, 1, "binding", code)
    assert original != digest(request, 2, "binding", code)
    assert original != digest(request, 1, "unbind", code)
    assert original != digest(uuid4(), 1, "binding", code)
    sealed = encrypt({"code": code})
    assert code.encode() not in sealed and decrypt(sealed) == {"code": code}
    config.payload_encryption_key = SecretStr(Fernet.generate_key().decode())
    with pytest.raises(InvalidToken):
        decrypt(sealed)


@pytest.mark.parametrize(
    "field,value",
    [
        ("smtp_password", ""),
        ("smtp_from", "invalid"),
        ("token_secret", "short"),
        ("payload_encryption_key", "not-a-key"),
        ("public_base_url", "http://unsafe.example.com"),
        ("smtp_start_tls", True),
    ],
)
def test_enabled_config_rejects_insecure(field, value):
    """启用时校验凭据、独立密钥与TLS组合；错误消息不包含真实授权码。"""
    data = dict(
        enabled=True,
        smtp_from="sender@example.com",
        smtp_username="sender@example.com",
        smtp_password="test-only-not-real",
        token_secret="x" * 32,
        payload_encryption_key=Fernet.generate_key().decode(),
    )
    data[field] = value
    with pytest.raises(ValidationError) as caught:
        MailSettings(_env_file=None, **data)
    assert "test-only-not-real" not in str(caught.value)


def test_email_normalization_and_compatibility():
    """可选邮箱不改变原账号和密码规则，规范化邮箱不接受头部注入。"""
    assert normalize_email(" NAME@Example.com ") == "name@example.com"
    payload = dict(account="tester", password="Test-only-123!", confirm_password="Test-only-123!")
    assert EmailRegistrationRequest(**payload).email is None
    assert EmailRegistrationRequest(**payload, email=" ").email is None
    with pytest.raises(ValueError):
        normalize_email("test@example.com\r\nBcc:other@example.com")


@pytest.mark.parametrize("kind", ["welcome", "binding", "unbind"])
def test_multipart_templates_escape_and_links(config, kind):
    """HTML与纯文本齐全，邮件不依赖脚本，模板变量不能注入HTML。"""
    message = render(kind, "to@example.com", {"code": "<script>bad()</script>", "expires_at": "2030-01-01"}, uuid4())
    html = message.get_body(preferencelist=("html",)).get_content()
    plain = message.get_body(preferencelist=("plain",)).get_content()
    assert "<script>bad()" not in html and plain
    assert "To" in message and "Message-ID" in message
    if kind == "welcome":
        assert "https://cloudatelier.online/pictures" in html
        assert "https://cloudatelier.online/pixel-beads" in plain
    else:
        assert "&lt;script&gt;" in html


@pytest.mark.asyncio
async def test_rate_limit_fail_closed(config):
    """Redis连接失败返回503，不能悄悄无限发送。"""
    with patch("src.modules.email_verification.rate_limit.Redis") as redis:
        redis.return_value.__aenter__ = AsyncMock(side_effect=OSError("test"))
        with pytest.raises(HTTPException) as caught:
            await MailLimiter().check([("private@example.com", 5, 3600)])
        assert caught.value.status_code == 503
