"""邮件任务持久状态机：队列故障、租约恢复、重复消息和重试上限。"""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from aiosmtplib.errors import SMTPRecipientRefused, SMTPRecipientsRefused, SMTPResponseException
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import undefer

from src.modules.email_verification.crypto import encrypt
from src.modules.email_verification.models import EmailChallenge as Challenge
from src.modules.email_verification.models import EmailOutbox as Job
from src.modules.email_verification.models import now
from src.modules.email_verification.outbox import cleanup, dispatch_once, expire_jobs, finish, process
from src.modules.user.models import User

from .test_email_api import age_requests, request_code

pytestmark = pytest.mark.asyncio


async def read_job(db, job_id):
    """读取worker独立事务结果，避免测试会话身份缓存制造假成功。"""
    return await db.scalar(
        select(Job).options(undefer(Job.payload)).where(Job.id == job_id).execution_options(populate_existing=True)
    )


async def due(db, job_id):
    """推进数据库调度时钟，不用真实等待退避时间。"""
    await db.execute(update(Job).where(Job.id == job_id).values(next_attempt_at=now() - timedelta(seconds=1)))
    await db.commit()


async def test_delivery_once_concurrent(email_client, db_session, test_db_engine):
    """重复任务与并发worker均不会同时调用SMTP，成功后清除加密载荷。"""
    request_id, _ = await request_code(email_client, db_session)
    job_id = await db_session.scalar(select(Job.id).where(Job.challenge_id == UUID(request_id)))
    factory = async_sessionmaker(test_db_engine, expire_on_commit=False)
    limiter = AsyncMock()
    sender = AsyncMock(side_effect=lambda *args: None)
    await asyncio.gather(process(job_id, factory, limiter, sender), process(job_id, factory, limiter, sender))
    assert sender.await_count == 1
    row = await read_job(db_session, job_id)
    assert row.status == "sent" and row.sent_at and row.payload is None and row.attempts == 1
    await process(job_id, factory, limiter, sender)
    assert sender.await_count == 1


async def test_retry_limit_and_log_redaction(email_client, db_session, test_db_engine, caplog):
    """临时失败退避三次后停止，异常正文含验证码也不能进入日志。"""
    request_id, code = await request_code(email_client, db_session)
    job_id = await db_session.scalar(select(Job.id).where(Job.challenge_id == UUID(request_id)))
    factory = async_sessionmaker(test_db_engine, expire_on_commit=False)
    sender = AsyncMock(side_effect=SMTPResponseException(450, f"private-code:{code} smtp-secret"))
    for attempt in range(1, 4):
        await process(job_id, factory, AsyncMock(), sender)
        row = await read_job(db_session, job_id)
        assert row.attempts == attempt
        assert row.status == ("pending" if attempt < 3 else "failed")
        await due(db_session, job_id)
    assert row.payload is None and code not in caplog.text and "smtp-secret" not in caplog.text


@pytest.mark.parametrize(
    "smtp_error",
    [
        SMTPResponseException(550, "recipient rejected"),
        SMTPRecipientsRefused([SMTPRecipientRefused(550, "recipient rejected", "rejected@example.com")]),
    ],
    ids=["smtp-permanent", "recipient-permanent"],
)
async def test_permanent_and_limiter_failures(email_client, db_session, test_db_engine, smtp_error):
    """限流未接触SMTP不消耗次数，永久拒信只尝试一次。"""
    request_id, _ = await request_code(email_client, db_session)
    job_id = await db_session.scalar(select(Job.id).where(Job.challenge_id == UUID(request_id)))
    factory = async_sessionmaker(test_db_engine, expire_on_commit=False)
    limiter, sender = AsyncMock(), AsyncMock(side_effect=smtp_error)
    limiter.sending.side_effect = HTTPException(429, "测试限流", headers={"Retry-After": "5"})
    await process(job_id, factory, limiter, sender)
    row = await read_job(db_session, job_id)
    assert row.status == "pending" and row.attempts == 0 and sender.await_count == 0
    await due(db_session, job_id)
    await process(job_id, factory, AsyncMock(), sender)
    row = await read_job(db_session, job_id)
    assert row.status == "failed" and row.payload is None and row.attempts == 1


async def test_broker_failure_recovery_and_stale_lease(email_client, db_session, test_db_engine):
    """入队失败留库，进程退出后的租约能恢复；旧租约不能覆盖新worker。"""
    request_id, _ = await request_code(email_client, db_session)
    job_id = await db_session.scalar(select(Job.id).where(Job.challenge_id == UUID(request_id)))
    factory = async_sessionmaker(test_db_engine, expire_on_commit=False)
    publish = AsyncMock(side_effect=OSError("amqp://never-log-this-secret"))
    assert await dispatch_once(publish, factory) == 1
    assert (await read_job(db_session, job_id)).status == "pending"
    await due(db_session, job_id)
    publish.side_effect = None
    await dispatch_once(publish, factory)
    row = await read_job(db_session, job_id)
    assert row.status == "queued" and publish.await_args.args == (str(job_id),)
    old_token = row.lease_token
    await db_session.execute(
        update(Job).where(Job.id == job_id).values(status="processing", lease_until=now() - timedelta(seconds=1))
    )
    await db_session.commit()
    assert await dispatch_once(publish, factory) == 1
    await finish(job_id, old_token, {"status": "sent"}, factory)
    assert (await read_job(db_session, job_id)).status == "queued"
    await process(job_id, factory, AsyncMock(), AsyncMock())
    assert (await read_job(db_session, job_id)).status == "sent"


async def test_cancelled_expired_deleted_user(email_client, db_session, test_db_engine, test_user):
    """过期、撤销与账号软删除均不调用SMTP。"""
    request_id, _ = await request_code(email_client, db_session)
    job_id = await db_session.scalar(select(Job.id).where(Job.challenge_id == UUID(request_id)))
    factory, sender = async_sessionmaker(test_db_engine, expire_on_commit=False), AsyncMock()
    await db_session.execute(update(Challenge).values(expires_at=now() - timedelta(seconds=1)))
    await db_session.commit()
    await process(job_id, factory, AsyncMock(), sender)
    assert (await read_job(db_session, job_id)).status == "cancelled"
    await age_requests(db_session)
    request_id, _ = await request_code(email_client, db_session, email="other@example.com")
    other_id = await db_session.scalar(select(Job.id).where(Job.challenge_id == UUID(request_id)))
    await db_session.execute(update(User).where(User.id == test_user["id"]).values(is_deleted=True))
    await db_session.commit()
    await process(other_id, factory, AsyncMock(), sender)
    assert (await read_job(db_session, other_id)).status == "cancelled" and not sender.await_count


async def test_welcome_retry_cleanup_tombstone(email_client, db_session, test_db_engine, test_user):
    """损坏载荷不可发送；清理保留欢迎墓碑以防老账号重复欢迎。"""
    job = Job(
        user_id=test_user["id"],
        kind="welcome",
        recipient="hello@example.com",
        dedupe_key=f"welcome/{test_user['id']}",
        payload=b"corrupt",
    )
    db_session.add(job)
    await db_session.commit()
    factory, sender = async_sessionmaker(test_db_engine, expire_on_commit=False), AsyncMock()
    await process(job.id, factory, AsyncMock(), sender)
    assert (await read_job(db_session, job.id)).error_code == "payload_invalid"
    await db_session.execute(update(Job).where(Job.id == job.id).values(updated_at=now() - timedelta(days=31)))
    await db_session.commit()
    await cleanup(factory)
    assert await db_session.get(Job, job.id) is not None and not sender.await_count


async def test_welcome_five_attempts(email_client, db_session, test_db_engine, test_user):
    """欢迎邮件按独立上限尝试五次，重试不新增业务记录。"""
    job = Job(
        user_id=test_user["id"],
        kind="welcome",
        recipient="hello@example.com",
        dedupe_key=f"welcome/{test_user['id']}",
        payload=encrypt({}),
    )
    db_session.add(job)
    await db_session.commit()
    factory = async_sessionmaker(test_db_engine, expire_on_commit=False)
    sender = AsyncMock(side_effect=TimeoutError("测试SMTP超时"))
    for attempt in range(1, 6):
        await process(job.id, factory, AsyncMock(), sender)
        row = await read_job(db_session, job.id)
        assert row.status == ("pending" if attempt < 5 else "failed") and row.attempts == attempt
        await due(db_session, job.id)
    assert sender.await_count == 5 and row.payload is None


async def test_expiry_without_broker(email_client, db_session, test_db_engine):
    """队列完全离线时，数据库维护仍销毁过期验证码载荷。"""
    request_id, _ = await request_code(email_client, db_session)
    job_id = await db_session.scalar(select(Job.id).where(Job.challenge_id == UUID(request_id)))
    await db_session.execute(update(Challenge).values(expires_at=now() - timedelta(seconds=1)))
    await db_session.commit()
    await expire_jobs(async_sessionmaker(test_db_engine, expire_on_commit=False))
    row = await read_job(db_session, job_id)
    assert row.status == "cancelled" and row.payload is None
