"""独立验证申请与事务邮件表；不在用户表保存验证码。"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from ...infrastructure.database.session import Base


def now() -> datetime:
    """数据库时间统一为有时区UTC。"""
    return datetime.now(UTC)


class EmailChallenge(Base):
    """验证码只保存带服务端独立密钥的摘要，消费和错误次数都必须落库。"""

    __tablename__ = "email_verification_challenges"
    __table_args__ = (Index("ix_email_challenge_user_created", "user_id", "created_at"),)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    email: Mapped[str] = mapped_column(String(254))
    purpose: Mapped[str] = mapped_column(String(16))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    original_email: Mapped[str | None] = mapped_column(String(254))
    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=now)
    attempts: Mapped[int] = mapped_column(default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class EmailOutbox(Base):
    """至少一次投递；幂等键和租约防并发，SMTP外部副作用不能保证绝对仅一次。"""

    __tablename__ = "email_outbox"
    __table_args__ = (Index("ix_email_outbox_due", "status", "next_attempt_at"),)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    kind: Mapped[str] = mapped_column(String(16))
    recipient: Mapped[str] = mapped_column(String(254))
    dedupe_key: Mapped[str] = mapped_column(String(120), unique=True)
    payload: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)
    challenge_id: Mapped[UUID | None] = mapped_column(ForeignKey("email_verification_challenges.id"), default=None)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=now)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=now)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    lease_token: Mapped[UUID | None] = mapped_column(default=None)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    error_code: Mapped[str | None] = mapped_column(String(80), default=None)
