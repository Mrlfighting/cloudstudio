"""邮件独立配置：关闭时不影响原有注册与登录，启用时严格检查密钥。"""

from functools import lru_cache
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import EmailStr, Field, SecretStr, TypeAdapter, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ...infrastructure.config.settings import env_path


class MailSettings(BaseSettings):
    """实际凭据仅来自环境变量或本地配置，不进入代码和日志。"""

    model_config = SettingsConfigDict(env_prefix="MAIL_", env_file=env_path, extra="ignore", hide_input_in_errors=True)
    enabled: bool = False
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = Field(default=465, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = ""
    smtp_use_tls: bool = True
    smtp_start_tls: bool = False
    smtp_allow_insecure: bool = False
    smtp_timeout: float = Field(default=20, ge=1, le=60)
    token_secret: SecretStr = SecretStr("")
    payload_encryption_key: SecretStr = SecretStr("")
    public_base_url: str = "https://cloudatelier.online"
    support_email: str = ""
    queue_name: str = "cloudatelier.email"
    code_ttl_seconds: int = Field(default=600, ge=60, le=1800)
    resend_seconds: int = Field(default=60, ge=30, le=600)
    code_max_attempts: int = Field(default=5, ge=1, le=10)
    account_hour_limit: int = Field(default=5, ge=1)
    address_hour_limit: int = Field(default=5, ge=1)
    ip_hour_limit: int = Field(default=20, ge=1)
    send_per_minute: int = Field(default=10, ge=1)
    poll_seconds: float = Field(default=2, ge=0.1, le=60)
    lease_seconds: int = Field(default=120, ge=90, le=600)

    @model_validator(mode="after")
    def validate_enabled(self) -> "MailSettings":
        """默认校验TLS；Mailpit仅在显式允许不安全的本地测试配置中使用。"""
        if not self.enabled:
            return self
        if self.smtp_use_tls and self.smtp_start_tls:
            raise ValueError("MAIL_SMTP_USE_TLS与START_TLS不能同时启用")
        if not (self.smtp_use_tls or self.smtp_start_tls or self.smtp_allow_insecure):
            raise ValueError("生产邮件必须启用TLS")
        TypeAdapter(EmailStr).validate_python(self.smtp_from)
        if not self.smtp_allow_insecure and (not self.smtp_username or not self.smtp_password.get_secret_value()):
            raise ValueError("必须配置SMTP账号和授权码")
        if len(self.token_secret.get_secret_value().encode()) < 32:
            raise ValueError("MAIL_TOKEN_SECRET至少32字节")
        try:
            Fernet(self.payload_encryption_key.get_secret_value().encode())
        except Exception:
            raise ValueError("MAIL_PAYLOAD_ENCRYPTION_KEY不是有效Fernet密钥") from None
        url = urlsplit(self.public_base_url)
        if url.scheme != "https" or not url.netloc or url.username or url.query or url.fragment:
            raise ValueError("MAIL_PUBLIC_BASE_URL必须为不含凭据和查询参数的HTTPS地址")
        if self.support_email:
            TypeAdapter(EmailStr).validate_python(self.support_email)
        return self


@lru_cache
def get_mail_settings() -> MailSettings:
    """API、调度器与worker加载相同配置。"""
    return MailSettings()
