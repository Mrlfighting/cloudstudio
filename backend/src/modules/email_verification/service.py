"""邮箱业务事务：先登记申请/邮件任务，再异步投递；不调用SMTP。"""

import hmac
from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..user.models import User
from ..user.schemas import UserRegister
from ..user.service import UserService
from .config import get_mail_settings
from .crypto import digest, encrypt, new_code
from .models import EmailChallenge, EmailOutbox, now
from .rate_limit import MailLimiter
from .schemas import EmailRegistrationRequest, normalize_email


def require_enabled() -> None:
    """邮件关闭时明确拒绝邮箱操作，普通不带邮箱注册仍可使用。"""
    if not get_mail_settings().enabled:
        raise HTTPException(503, "邮箱功能尚未开启")


async def available(db: AsyncSession, email: str, user_id: int | None = None) -> None:
    """包括软删除账号；预检查仅改善提示，最终以数据库唯一索引为准。"""
    stmt = select(User.id).where(func.lower(func.btrim(User.email)) == email)
    if user_id is not None:
        stmt = stmt.where(User.id != user_id)
    if await db.scalar(stmt) is not None:
        raise HTTPException(409, "邮箱不可用，请更换邮箱")


async def locked_user(db: AsyncSession, user_id: int) -> User:
    """同一账号申请和确认始终按用户行、申请行的顺序加锁。"""
    user = await db.scalar(select(User).where(User.id == user_id, User.is_deleted.is_(False)).with_for_update())
    if user is None:
        raise HTTPException(401, "账号不可用，请重新登录")
    return user


async def invalidate(db: AsyncSession, user_id: int) -> None:
    """换绑/解绑互相撤销；已被worker取出的任务也在发送前重查申请。"""
    await db.execute(
        update(EmailChallenge)
        .where(
            EmailChallenge.user_id == user_id,
            EmailChallenge.consumed_at.is_(None),
            EmailChallenge.invalidated_at.is_(None),
        )
        .values(invalidated_at=now())
    )
    await db.execute(
        update(EmailOutbox)
        .where(
            EmailOutbox.user_id == user_id,
            EmailOutbox.challenge_id.is_not(None),
            EmailOutbox.status.in_(["pending", "publishing", "queued"]),
        )
        .values(status="cancelled", payload=None, lease_token=None, lease_until=None, updated_at=now())
    )


async def welcome(db: AsyncSession, user_id: int, email: str) -> None:
    """一个账号只登记一份欢迎任务；不依据是否收过某次验证码重复欢迎。"""
    if await db.scalar(select(EmailOutbox.id).where(EmailOutbox.dedupe_key == f"welcome/{user_id}")) is None:
        db.add(
            EmailOutbox(user_id=user_id, kind="welcome", recipient=email, dedupe_key=f"welcome/{user_id}", payload=encrypt({}))
        )


async def issue(db: AsyncSession, user: User, email: str, purpose: str) -> dict:
    """调用者持有用户行锁，重发前检查最近申请并冻结新的验证码。"""
    cfg = get_mail_settings()
    latest = await db.scalar(
        select(EmailChallenge).where(EmailChallenge.user_id == user.id).order_by(EmailChallenge.created_at.desc()).limit(1)
    )
    if latest:
        seconds = (latest.created_at + timedelta(seconds=cfg.resend_seconds) - now()).total_seconds()
        if seconds > 0:
            raise HTTPException(429, "请稍后再发送验证码", headers={"Retry-After": str(max(1, int(seconds) + 1))})
    await invalidate(db, user.id)
    code = new_code()
    challenge = EmailChallenge(
        user_id=user.id,
        email=email,
        purpose=purpose,
        code_hash="",
        expires_at=now() + timedelta(seconds=cfg.code_ttl_seconds),
        original_email=user.email,
    )
    challenge.code_hash = digest(challenge.id, user.id, purpose, code)
    db.add(challenge)
    await db.flush()
    db.add(
        EmailOutbox(
            user_id=user.id,
            kind=purpose,
            recipient=email,
            challenge_id=challenge.id,
            dedupe_key=f"challenge/{challenge.id}",
            payload=encrypt({"code": code}),
        )
    )
    return {
        "request_id": str(challenge.id),
        "expires_at": challenge.expires_at,
        "retry_after": cfg.resend_seconds,
        "delivery_status": "queued",
    }


async def request_binding(db: AsyncSession, user_id: int, email: str, request: Request, limiter: MailLimiter) -> dict:
    """验证新邮箱前不修改正式绑定，失败保留原地址。"""
    require_enabled()
    await limiter.request(request, email, user_id)
    user = await locked_user(db, user_id)
    if user.email and normalize_email(user.email) == email and user.email_verified:
        raise HTTPException(409, "当前邮箱已验证，无需重复绑定")
    await available(db, email, user_id)
    result = await issue(db, user, email, "binding")
    await db.commit()
    return result


async def request_unbind(db: AsyncSession, user_id: int, request: Request, limiter: MailLimiter) -> dict:
    """解绑验证码只发送到当前地址，不接受客户端指定解绑收件人。"""
    require_enabled()
    user = await locked_user(db, user_id)
    if not user.email:
        raise HTTPException(409, "当前账号没有绑定邮箱")
    await limiter.request(request, normalize_email(user.email), user_id)
    result = await issue(db, user, user.email, "unbind")
    await db.commit()
    return result


async def confirm(db: AsyncSession, user_id: int, request_id: UUID, code: str, purpose: str) -> dict:
    """错误计数单独提交后再返回错误，避免异常回滚让暴力猜码无限重试。"""
    require_enabled()
    user = await locked_user(db, user_id)
    challenge = await db.scalar(
        select(EmailChallenge)
        .where(
            EmailChallenge.id == request_id,
            EmailChallenge.user_id == user_id,
            EmailChallenge.purpose == purpose,
        )
        .with_for_update()
    )
    if challenge is None:
        raise HTTPException(404, "验证申请不存在")
    cfg = get_mail_settings()
    if (
        challenge.consumed_at
        or challenge.invalidated_at
        or challenge.expires_at <= now()
        or challenge.attempts >= cfg.code_max_attempts
        or challenge.original_email != user.email
    ):
        raise HTTPException(400, "验证申请已失效，请重新获取验证码")
    valid_shape = len(code) == 6 and code.isascii() and code.isdigit()
    if not valid_shape or not hmac.compare_digest(challenge.code_hash, digest(request_id, user_id, purpose, code)):
        challenge.attempts += 1
        if challenge.attempts >= cfg.code_max_attempts:
            challenge.invalidated_at = now()
        await db.commit()
        raise HTTPException(400, "验证码错误或已失效")
    try:
        if purpose == "binding":
            await available(db, challenge.email, user_id)
            user.email, user.email_verified = challenge.email, True
            await welcome(db, user_id, challenge.email)
        else:
            user.email, user.email_verified = None, False
        challenge.consumed_at = now()
        await invalidate(db, user_id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "邮箱已被其他账号绑定，请重新申请") from None
    return {"email": user.email, "email_verified": user.email_verified}


async def status(db: AsyncSession, user_id: int) -> dict:
    """状态只返回本账号数据，不返回验证码摘要或加密载荷。"""
    user = await db.scalar(select(User).where(User.id == user_id, User.is_deleted.is_(False)))
    if user is None:
        raise HTTPException(401, "账号不可用")
    challenge = await db.scalar(
        select(EmailChallenge)
        .where(
            EmailChallenge.user_id == user_id,
            EmailChallenge.consumed_at.is_(None),
            EmailChallenge.invalidated_at.is_(None),
            EmailChallenge.expires_at > now(),
        )
        .order_by(EmailChallenge.created_at.desc())
        .limit(1)
    )
    pending = None
    if challenge:
        delivery = await db.scalar(select(EmailOutbox.status).where(EmailOutbox.challenge_id == challenge.id))
        pending = {
            "request_id": str(challenge.id),
            "email": challenge.email,
            "purpose": challenge.purpose,
            "expires_at": challenge.expires_at,
            "delivery_status": delivery,
            "retry_after": max(
                0,
                int((challenge.created_at + timedelta(seconds=get_mail_settings().resend_seconds) - now()).total_seconds()) + 1,
            ),
        }
    return {"email": user.email, "email_verified": user.email_verified, "pending": pending}


async def register(
    data: EmailRegistrationRequest, db: AsyncSession, core: UserService, request: Request, limiter: MailLimiter
) -> dict:
    """旧注册路径保持原行为；填写邮箱才使用新增事务编排。"""
    original = UserRegister(**data.model_dump(exclude={"email"}))
    if data.email is None:
        return await core.register(original, db)
    require_enabled()
    await limiter.request(request, data.email)
    try:
        await available(db, data.email)
        created = await core.register(original, db, commit=False)
        user = await locked_user(db, created["id"])
        verification = await issue(db, user, data.email, "binding")
        await welcome(db, user.id, data.email)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return {**created, "email_verification": verification}
