"""验证码摘要与队列载荷加密，密钥与认证会话密钥相互独立。"""

import hashlib
import hmac
import json
import secrets
from uuid import UUID

from cryptography.fernet import Fernet

from .config import get_mail_settings


def new_code() -> str:
    """保留前导零，使用密码学安全随机源。"""
    return f"{secrets.randbelow(1_000_000):06d}"


def digest(request_id: UUID, user_id: int, purpose: str, code: str) -> str:
    """将账号、用途和申请ID一起绑定，数据库泄漏不能离线枚举短验证码。"""
    key = get_mail_settings().token_secret.get_secret_value().encode()
    return hmac.new(key, f"{request_id}/{user_id}/{purpose}/{code}".encode(), hashlib.sha256).hexdigest()


def encrypt(payload: dict) -> bytes:
    """RabbitMQ只传任务ID，敏感载荷在数据库中加密保存。"""
    key = get_mail_settings().payload_encryption_key.get_secret_value().encode()
    return Fernet(key).encrypt(json.dumps(payload, ensure_ascii=False).encode())


def decrypt(payload: bytes) -> dict:
    """仅发送worker解密，错误不能携带载荷进入日志。"""
    key = get_mail_settings().payload_encryption_key.get_secret_value().encode()
    result = json.loads(Fernet(key).decrypt(payload))
    if not isinstance(result, dict):
        raise ValueError("邮件载荷格式无效")
    return result
