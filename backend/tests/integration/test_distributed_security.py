"""独立 RabbitMQ/Redis 验证广播、共享锁和依赖恢复；不使用业务容器。"""

import asyncio
import importlib
import socket
import time
from uuid import uuid4

import pytest
import redis.asyncio as aioredis
from alembic.migration import MigrationContext
from alembic.operations import Operations
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from src.infrastructure import readiness
from src.infrastructure.app_factory import create_application
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.session import async_session
from src.infrastructure.image_collab import CollabBroker, CollabLock
from src.infrastructure.rate_limit import middleware as limits
from src.infrastructure.rate_limit import provider as limit_provider
from src.infrastructure.rate_limit.backends.redis import RedisBackend, RedisSettings
from src.infrastructure.rate_limit.provider import RateLimiterProvider
from src.interfaces.api import router
from src.modules.space.models import Space

pytestmark = pytest.mark.asyncio
_REAL_PIPELINE = aioredis.Redis.pipeline


async def test_broadcast_reaches_both_instances_and_recovers():
    """每个实例收到全部事件；其中一个退订不能删除另一个的队列。"""
    # Docker Desktop 重启随机端口映射可能改变端口，固定本次测试的映射以模拟同地址依赖恢复。
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    with DockerContainer("rabbitmq:3-management-alpine").with_bind_ports(5672, port) as rabbit:
        wait_for_logs(rabbit, "Server startup complete", timeout=60)
        url = f"amqp://guest:guest@{rabbit.get_container_host_ip()}:{rabbit.get_exposed_port(5672)}/"
        brokers = [CollabBroker(url), CollabBroker(url)]
        results = [[], []]
        room = int(uuid4().hex[:7], 16)

        async def first(payload):
            """第一个 API 实例的事件订阅。"""
            results[0].append(payload["n"])

        async def second(payload):
            """第二个 API 实例的事件订阅。"""
            results[1].append(payload["n"])

        async def wait_until(predicate):
            """事件测试按条件等待，不使用固定长延迟掩盖丢消息。"""
            async with asyncio.timeout(30):
                while not predicate():
                    await asyncio.sleep(0.05)

        try:
            await asyncio.gather(*(b.connect() for b in brokers))
            await brokers[0].subscribe(room, 1, first)
            await brokers[1].subscribe(room, 1, second)
            for n in range(10):
                await brokers[0].publish(room, 1, {"n": n})
            await wait_until(lambda: all(len(values) == 10 for values in results))
            assert results == [list(range(10)), list(range(10))]
            await brokers[0].unsubscribe(room, 1)
            await brokers[1].publish(room, 1, {"n": 10})
            await wait_until(lambda: len(results[1]) == 11)
            assert results[0] == list(range(10))
            # 真正中断连接并重启 RabbitMQ，Robust 连接必须恢复订阅。
            await asyncio.to_thread(rabbit.get_wrapped_container().stop, timeout=1)
            await wait_until(lambda: not brokers[1].available)
            await asyncio.to_thread(rabbit.get_wrapped_container().start)
            assert int(rabbit.get_exposed_port(5672)) == port
            await wait_until(lambda: brokers[1].available)
            await brokers[1].ensure_connected()
            await brokers[1].publish(room, 1, {"n": 11})
            await wait_until(lambda: len(results[1]) == 12)
            assert results[1][-1] == 11
        finally:
            await asyncio.gather(*(b.close() for b in brokers), return_exceptions=True)


async def test_shared_lock_state_and_outage_fail_closed():
    """不同 Redis 客户端只能有一个编辑者，故障时两边均不能降级授予编辑权。"""
    with DockerContainer("redis:7-alpine").with_exposed_ports(6379) as container:
        wait_for_logs(container, "Ready to accept connections", timeout=30)
        clients = [
            aioredis.Redis(
                host=container.get_container_host_ip(),
                port=int(container.get_exposed_port(6379)),
                socket_timeout=0.5,
                socket_connect_timeout=0.5,
            )
            for _ in range(2)
        ]
        locks = [CollabLock(client, ttl=30) for client in clients]
        try:
            assert await locks[0].try_acquire(1, 1, 100)
            assert not await locks[1].try_acquire(1, 1, 200)
            assert await locks[1].get_holder(1, 1) == 100
            await asyncio.to_thread(container.get_wrapped_container().pause)
            try:
                results = await asyncio.gather(*(lock.try_acquire(1, 1, 300) for lock in locks), return_exceptions=True)
                assert all(isinstance(value, Exception) for value in results)
            finally:
                await asyncio.to_thread(container.get_wrapped_container().unpause)
            assert await locks[0].release(1, 1, 100)
            assert await locks[1].try_acquire(1, 1, 200)
        finally:
            await asyncio.gather(*(lock.close() for lock in locks))


async def test_security_migration_round_trip_and_duplicate_preflight(test_db_engine, db_session, test_user):
    """在临时 PostgreSQL 升降级，并确认重复空间会阻止迁移而非被删除。"""
    migration = importlib.import_module("migrations.versions.a8d9e0f1b2c3_security_consistency")

    def run(connection, operation):
        """Alembic Operations 绑定当前测试连接。"""
        with Operations.context(MigrationContext.configure(connection)):
            operation()

    async with test_db_engine.begin() as connection:
        await connection.run_sync(run, migration.downgrade)
        await connection.run_sync(run, migration.upgrade)
        await connection.run_sync(run, migration.downgrade)
    db_session.add_all([Space(name="重复一", user_id=test_user["id"]), Space(name="重复二", user_id=test_user["id"])])
    await db_session.commit()
    with pytest.raises(RuntimeError, match="重复空间"):
        async with test_db_engine.begin() as connection:
            await connection.run_sync(run, migration.upgrade)
    rows = (await db_session.execute(select(Space))).scalars().all()
    assert len(rows) == 2
    rows[1].is_deleted = True
    await db_session.commit()
    async with test_db_engine.begin() as connection:
        await connection.run_sync(run, migration.upgrade)


async def test_api_rate_limit_shared_between_apps_and_user_isolation(db_session, test_user, test_user_2, monkeypatch):
    """真实 Redis + 实际 API 路由：变更资源编号、伪造 IP、换实例均不能重置配额。"""
    with DockerContainer("redis:7-alpine").with_exposed_ports(6379) as container:
        wait_for_logs(container, "Ready to accept connections", timeout=30)
        monkeypatch.setattr(aioredis.Redis, "pipeline", _REAL_PIPELINE)
        backend = RedisBackend(
            RedisSettings(host=container.get_container_host_ip(), port=int(container.get_exposed_port(6379)), db=0),
            fail_open=False,
        )
        provider = RateLimiterProvider()
        provider.register_backend("redis", backend, default=True)
        monkeypatch.setattr(limit_provider, "rate_limiter_provider", provider)
        settings = get_settings()
        monkeypatch.setattr(settings, "RATE_LIMITER_ENABLED", True)
        monkeypatch.setattr(settings, "RATE_LIMITER_FAIL_OPEN", False)
        monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 0)
        monkeypatch.setattr(limits, "DEFAULT_LIMIT", 2)
        monkeypatch.setattr(limits, "DEFAULT_PERIOD", 17)
        apps = [create_application(router=router, settings=settings) for _ in range(2)]

        async def db():
            """API 实例共享临时测试数据库，绝不使用本地配置中的数据库。"""
            yield db_session

        for app in apps:
            app.dependency_overrides[async_session] = db
        try:
            async with (
                AsyncClient(transport=ASGITransport(app=apps[0]), base_url="http://test") as first,
                AsyncClient(transport=ASGITransport(app=apps[1]), base_url="http://test") as second,
            ):
                assert (await first.get("/api/v1/pictures/9001")).status_code == 404
                assert (await second.get("/api/v1/pictures/9002")).status_code == 404
                limited = await first.get("/api/v1/pictures/9003", headers={"X-Forwarded-For": "198.51.100.77"})
                assert limited.status_code == 429 and limited.headers["retry-after"] == "17"
                assert limited.headers["x-ratelimit-remaining"] == "0"
                for client, user in ((first, test_user), (second, test_user_2)):
                    response = await client.post(
                        "/api/v1/auth/login", data={"username": user["username"], "password": user["password"]}
                    )
                    assert response.status_code == 200
                    assert (await client.get("/api/v1/pictures/9001")).status_code == 404
                    assert (await client.get("/api/v1/pictures/9002")).status_code == 404
                assert (await first.get("/api/v1/pictures/9003")).status_code == 429
                assert (await second.get("/api/v1/pictures/9003")).status_code == 429
                # 暂停的共享限流依赖必须在请求预算内返回 503，恢复后可继续读取。
                await asyncio.to_thread(container.get_wrapped_container().pause)
                try:
                    async with asyncio.timeout(7):
                        unavailable = await first.get("/api/v1/tiers/")
                    assert unavailable.status_code == 503
                finally:
                    await asyncio.to_thread(container.get_wrapped_container().unpause)
                assert (await first.get("/api/v1/tiers/")).status_code == 200
        finally:
            await backend.client.aclose()


async def test_real_database_outage_readiness_recovers(pg_container, test_db_engine, monkeypatch):
    """真实数据库暂停时就绪检查在预算内失败，恢复后重新连通；不影响存活检查。"""
    monkeypatch.setattr(readiness, "engine", test_db_engine)
    assert (await readiness.readiness_response()).status_code == 200
    await asyncio.to_thread(pg_container.get_wrapped_container().pause)
    try:
        started = time.monotonic()
        async with asyncio.timeout(5):
            response = await readiness.readiness_response()
        assert response.status_code == 503 and time.monotonic() - started < 4
    finally:
        await asyncio.to_thread(pg_container.get_wrapped_container().unpause)
    assert (await readiness.readiness_response()).status_code == 200
