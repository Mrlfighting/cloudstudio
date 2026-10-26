"""事务邮件调度与发送状态机；数据库是重试事实来源，RabbitMQ仅传任务ID。"""

import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from aiosmtplib.errors import SMTPException, SMTPRecipientsRefused, SMTPResponseException
from fastapi import HTTPException
from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.orm import undefer

from ...infrastructure.database.session import local_session

# 独立worker没有加载API聚合，需注册用户模型已有的Tier关系；不读写套餐业务。
from ..tier.models import Tier as Tier
from ..user.models import User
from .config import get_mail_settings
from .crypto import decrypt
from .mail import send
from .models import EmailChallenge, now
from .models import EmailOutbox as Job
from .rate_limit import MailLimiter, get_mail_limiter

logger = logging.getLogger(__name__)
BACKOFF = (30, 120, 600, 1800)
TERMINAL = ("sent", "failed", "cancelled")


async def dispatch_once(publish: Callable[[str], Awaitable[None]], factory=local_session, batch: int = 20) -> int:
    """先租约预留再发布；网络IO不持有数据库事务，失联后可重新调度。"""
    reservations = []
    cfg = get_mail_settings()
    async with factory() as db:
        jobs = (
            await db.scalars(
                select(Job)
                .where(
                    or_(
                        and_(Job.status == "pending", Job.next_attempt_at <= now()),
                        and_(Job.status.in_(["publishing", "queued", "processing"]), Job.lease_until < now()),
                    )
                )
                .order_by(Job.next_attempt_at)
                .limit(batch)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for job in jobs:
            token = uuid4()
            job.status, job.lease_token = "publishing", token
            job.lease_until, job.updated_at = now() + timedelta(seconds=cfg.lease_seconds), now()
            reservations.append((job.id, token))
        await db.commit()
    for job_id, token in reservations:
        try:
            await publish(str(job_id))
            values = {"status": "queued", "lease_until": now() + timedelta(seconds=cfg.lease_seconds)}
        except Exception:
            # 不记录异常正文，AMQP连接异常可能包含带密码的URL。
            logger.warning("邮件入队失败 job=%s，将由调度器重试", job_id)
            values = {
                "status": "pending",
                "lease_until": None,
                "lease_token": None,
                "next_attempt_at": now() + timedelta(seconds=30),
                "error_code": "broker_unavailable",
            }
        async with factory() as db:
            await db.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "publishing", Job.lease_token == token)
                .values(**values, updated_at=now())
            )
            await db.commit()
    return len(reservations)


async def active(db, job: Job) -> bool:
    """软删除账号、过期/消费/撤销申请不再发送；欢迎邮件不含账号私密资料。"""
    user = await db.scalar(select(User).where(User.id == job.user_id, User.is_deleted.is_(False)))
    if user is None:
        return False
    if job.challenge_id is None:
        return job.kind == "welcome"
    challenge = await db.get(EmailChallenge, job.challenge_id)
    return bool(
        challenge
        and not challenge.consumed_at
        and not challenge.invalidated_at
        and challenge.expires_at > now()
        and challenge.original_email == user.email
        and challenge.attempts < get_mail_settings().code_max_attempts
    )


async def finish(job_id: UUID, token: UUID, values: dict, factory) -> None:
    """只允许当前持租约者提交结果，旧worker不能覆盖恢复后的新状态。"""
    async with factory() as db:
        await db.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == "processing", Job.lease_token == token)
            .values(**values, lease_token=None, lease_until=None, updated_at=now())
        )
        await db.commit()


async def process(job_id: UUID, factory=local_session, limiter: MailLimiter | None = None, sender=send) -> None:
    """单任务最多一次并发SMTP；响应丢失的外部副作用仍可能重复，不伪称严格恰好一次。"""
    cfg, token = get_mail_settings(), uuid4()
    if not cfg.enabled:
        raise RuntimeError("邮箱功能未开启，不能启动邮件worker")
    async with factory() as db:
        job = await db.scalar(select(Job).options(undefer(Job.payload)).where(Job.id == job_id).with_for_update())
        if job is None or job.status in TERMINAL:
            return
        # 队列里的旧副本不能跳过数据库重试时间或抢占正在发送的租约。
        if job.status == "pending" and job.next_attempt_at > now():
            return
        if job.status == "processing" and job.lease_until and job.lease_until > now():
            return
        maximum = 5 if job.kind == "welcome" else 3
        if not await active(db, job) or job.attempts >= maximum:
            job.status = "failed" if job.attempts >= maximum else "cancelled"
            job.payload, job.lease_until, job.lease_token = None, None, None
            job.updated_at = now()
            await db.commit()
            return
        try:
            payload = decrypt(job.payload) if job.payload is not None else None
            if payload is None:
                raise ValueError("缺少加密载荷")
        except Exception:
            job.status, job.payload, job.error_code = "failed", None, "payload_invalid"
            job.lease_until, job.lease_token = None, None
            await db.commit()
            logger.error("邮件载荷不可用 job=%s", job_id)
            return
        kind, recipient, attempt = job.kind, job.recipient, job.attempts + 1
        if job.challenge_id:
            challenge = await db.get(EmailChallenge, job.challenge_id)
            payload["expires_at"] = challenge.expires_at.isoformat() if challenge else ""
        job.status, job.lease_token, job.attempts = "processing", token, attempt
        job.lease_until, job.updated_at = now() + timedelta(seconds=cfg.lease_seconds), now()
        await db.commit()
    try:
        await (limiter or get_mail_limiter()).sending()
    except HTTPException as error:
        # 尚未接触SMTP，不消耗邮件发送次数，限流基础设施恢复后继续。
        await finish(
            job_id,
            token,
            {
                "status": "pending",
                "attempts": attempt - 1,
                "next_attempt_at": now()
                + timedelta(seconds=int(error.headers.get("Retry-After", 30)) if error.headers else 30),
                "error_code": "send_rate_limited",
            },
            factory,
        )
        return
    async with factory() as db:
        # 限速等待期间也可能消费或撤销验证码；发送前再检查一次。
        current = await db.get(Job, job_id)
        if not current or current.lease_token != token or not await active(db, current):
            await finish(job_id, token, {"status": "cancelled", "payload": None}, factory)
            return
    try:
        await sender(kind, recipient, payload, job_id)
    except Exception as error:
        transient = isinstance(error, (TimeoutError, OSError, ConnectionError, SMTPException))
        if isinstance(error, SMTPResponseException) and error.code >= 500:
            transient = False
        if isinstance(error, SMTPRecipientsRefused):
            # aiosmtplib对RCPT失败使用聚合异常，不能把其中的永久5xx拒信当成临时网络错误。
            transient = any(item.code < 500 for item in error.recipients)
        retry = transient and attempt < maximum
        values: dict[str, Any] = {"status": "pending" if retry else "failed", "error_code": type(error).__name__[:80]}
        if retry:
            values["next_attempt_at"] = now() + timedelta(seconds=BACKOFF[attempt - 1])
        else:
            values["payload"] = None
        await finish(job_id, token, values, factory)
        logger.warning("邮件投递失败 job=%s attempt=%s retry=%s type=%s", job_id, attempt, retry, type(error).__name__)
        return
    await finish(job_id, token, {"status": "sent", "sent_at": now(), "payload": None, "error_code": None}, factory)
    logger.info("邮件投递成功 job=%s", job_id)


async def cleanup(factory=local_session) -> None:
    """终态元数据保留30天；所有未完成邮件保留到重试或明确失效。"""
    cutoff = now() - timedelta(days=30)
    async with factory() as db:
        # 欢迎幂等墓碑保留，删除它会导致老账号再次绑定时重复收到欢迎信。
        await db.execute(
            update(Job)
            .where(Job.status.in_(TERMINAL), Job.updated_at < cutoff, Job.kind == "welcome")
            .values(recipient="", payload=None, error_code=None)
        )
        await db.execute(delete(Job).where(Job.status.in_(TERMINAL), Job.updated_at < cutoff, Job.kind != "welcome"))
        referenced = select(Job.challenge_id).where(Job.challenge_id.is_not(None))
        await db.execute(delete(EmailChallenge).where(EmailChallenge.expires_at < cutoff, EmailChallenge.id.not_in(referenced)))
        await db.commit()


async def expire_jobs(factory=local_session) -> None:
    """RabbitMQ离线也及时销毁失效验证码载荷，不能依赖worker启动才能清理。"""
    async with factory() as db:
        invalid_challenges = select(EmailChallenge.id).where(
            or_(
                EmailChallenge.expires_at <= now(),
                EmailChallenge.invalidated_at.is_not(None),
                EmailChallenge.consumed_at.is_not(None),
            )
        )
        inactive_users = select(User.id).where(User.is_deleted.is_(True))
        await db.execute(
            update(Job)
            .where(
                or_(Job.challenge_id.in_(invalid_challenges), Job.user_id.in_(inactive_users)),
                or_(
                    Job.status.in_(["pending", "publishing", "queued"]),
                    and_(Job.status == "processing", Job.lease_until < now()),
                ),
            )
            .values(status="cancelled", payload=None, lease_until=None, lease_token=None, updated_at=now())
        )
        await db.commit()
