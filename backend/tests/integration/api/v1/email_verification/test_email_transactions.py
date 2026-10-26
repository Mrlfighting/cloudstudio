"""迁移升降级、历史重复预检及数据库并发抢占回归。"""

import asyncio
import importlib.util
from pathlib import Path
from uuid import UUID

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.email_verification import service
from src.modules.email_verification.crypto import decrypt
from src.modules.email_verification.models import EmailOutbox as Job

pytestmark = pytest.mark.asyncio


def migration():
    """加载指定迁移，禁止误用环境配置连接真实数据库。"""
    file = Path(__file__).parents[5] / "migrations/versions/f3c4d5e6a7b8_email_verification.py"
    spec = importlib.util.spec_from_file_location("email_migration", file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(connection, operation):
    """复用Alembic Operations，但连接只能来自临时库fixture。"""
    with Operations.context(MigrationContext.configure(connection)):
        operation()


async def test_email_migration_up_down(test_db_engine):
    """从已有表模型模拟升级前结构，真实执行SQL并检查254长度与索引。"""
    module = migration()
    async with test_db_engine.begin() as connection:
        await connection.run_sync(lambda c: run(c, module.downgrade))
        await connection.run_sync(lambda c: run(c, module.upgrade))
        length = await connection.scalar(
            text(
                "SELECT character_maximum_length FROM information_schema.columns "
                "WHERE table_name='user' AND column_name='email'"
            )
        )
        assert length == 254
        await connection.run_sync(lambda c: run(c, module.downgrade))
        await connection.run_sync(lambda c: run(c, module.upgrade))


async def test_migration_rejects_case_duplicates(test_db_engine, test_user, test_user_2):
    """旧唯一索引允许大小写变体，新迁移必须拒绝并保留原数据。"""
    module = migration()
    async with test_db_engine.begin() as connection:
        await connection.run_sync(lambda c: run(c, module.downgrade))
        await connection.execute(
            text('UPDATE "user" SET email=:email WHERE id=:id'), {"email": "Same@Example.com", "id": test_user["id"]}
        )
        await connection.execute(
            text('UPDATE "user" SET email=:email WHERE id=:id'), {"email": "same@example.com", "id": test_user_2["id"]}
        )
    with pytest.raises(RuntimeError, match="重复邮箱"):
        async with test_db_engine.begin() as connection:
            await connection.run_sync(lambda c: run(c, module.upgrade))
    async with test_db_engine.begin() as connection:
        assert await connection.scalar(text('SELECT count(*) FROM "user"')) == 2
        await connection.execute(
            text('UPDATE "user" SET email=:email WHERE id=:id'), {"email": "distinct@example.com", "id": test_user_2["id"]}
        )
        await connection.run_sync(lambda c: run(c, module.upgrade))


async def test_migration_no_lossy_downgrade(test_db_engine, test_user):
    """合法长邮箱不能在降级时被截断，失败前不删除邮件表。"""
    module = migration()
    async with test_db_engine.begin() as connection:
        await connection.execute(
            text('UPDATE "user" SET email=:email WHERE id=:id'), {"email": "a" * 60 + "@example.com", "id": test_user["id"]}
        )
    with pytest.raises(RuntimeError, match="有损降级"):
        async with test_db_engine.begin() as connection:
            await connection.run_sync(lambda c: run(c, module.downgrade))
    async with test_db_engine.begin() as connection:
        assert await connection.scalar(text("SELECT to_regclass('email_outbox')")) == "email_outbox"


async def test_concurrent_email_claim(test_db_engine, test_user, test_user_2):
    """两份有效验证码同时抢同一地址，数据库保证仅一个账号绑定成功。"""

    async def prepare(user_id):
        async with AsyncSession(test_db_engine, expire_on_commit=False) as db:
            user = await service.locked_user(db, user_id)
            info = await service.issue(db, user, "race@example.com", "binding")
            await db.commit()
            payload = await db.scalar(select(Job.payload).where(Job.user_id == user_id))
            return user_id, info["request_id"], decrypt(payload)["code"]

    first, second = await prepare(test_user["id"]), await prepare(test_user_2["id"])

    async def confirm(values):
        user_id, request_id, code = values
        async with AsyncSession(test_db_engine, expire_on_commit=False) as db:
            try:
                await service.confirm(db, user_id, UUID(request_id), code, "binding")
                return 200
            except HTTPException as error:
                return error.status_code

    assert sorted(await asyncio.gather(confirm(first), confirm(second))) == [200, 409]
