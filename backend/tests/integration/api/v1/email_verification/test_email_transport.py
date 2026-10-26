"""真实临时RabbitMQ、Redis、Mailpit与独立worker的端到端发信验收。"""

import asyncio
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
import psutil
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from src.infrastructure.config.settings import get_settings
from src.modules.email_verification.broker import create_broker
from src.modules.email_verification.models import EmailOutbox as Job
from src.modules.email_verification.outbox import dispatch_once
from src.modules.email_verification.rate_limit import MailLimiter

from .test_email_api import URL

pytestmark = pytest.mark.asyncio


async def test_real_queue_worker_mailpit(email_client, db_session, test_db_engine, test_db_url, mail_env, monkeypatch):
    """实际子进程消费RabbitMQ，通过本地SMTP投递两封邮件，再用API中的验证码完成绑定。"""
    with (
        DockerContainer("rabbitmq:3-management-alpine").with_exposed_ports(5672) as rabbit,
        DockerContainer("redis:7-alpine").with_exposed_ports(6379) as redis,
        DockerContainer("axllent/mailpit:v1.27.4").with_exposed_ports(1025, 8025) as smtp,
    ):
        wait_for_logs(rabbit, "Server startup complete", timeout=60)
        wait_for_logs(redis, "Ready to accept connections", timeout=30)
        cfg = get_settings()
        for name, value in {
            "TASKIQ_RABBITMQ_HOST": rabbit.get_container_host_ip(),
            "TASKIQ_RABBITMQ_PORT": int(rabbit.get_exposed_port(5672)),
            "TASKIQ_RABBITMQ_USER": "guest",
            "TASKIQ_RABBITMQ_PASSWORD": "guest",
            "TASKIQ_RABBITMQ_VHOST": "/",
            "RATE_LIMITER_REDIS_HOST": redis.get_container_host_ip(),
            "RATE_LIMITER_REDIS_PORT": int(redis.get_exposed_port(6379)),
            "RATE_LIMITER_REDIS_DB": 0,
            "RATE_LIMITER_REDIS_PASSWORD": None,
        }.items():
            monkeypatch.setattr(cfg, name, value)
        monkeypatch.setattr(mail_env, "queue_name", "test.email." + uuid4().hex)
        broker = create_broker()

        @broker.task(task_name="email:deliver")
        async def publish_only(job_id: str):
            """父进程只发布，真正的任务函数由独立worker入口注册。"""

        # 独立worker必须覆盖所有数据库、队列与限流连接，不能继承开发/生产配置。
        url = test_db_engine.url
        env = {
            **os.environ,
            "DEBUG": "false",
            "PYTHONIOENCODING": "utf-8",
            "MAIL_ENABLED": "true",
            "POSTGRES_SERVER": url.host,
            "POSTGRES_PORT": str(url.port),
            "POSTGRES_USER": url.username,
            "POSTGRES_PASSWORD": url.password,
            "POSTGRES_DB": url.database,
            "TASKIQ_RABBITMQ_HOST": cfg.TASKIQ_RABBITMQ_HOST,
            "TASKIQ_RABBITMQ_PORT": str(cfg.TASKIQ_RABBITMQ_PORT),
            "TASKIQ_RABBITMQ_USER": "guest",
            "TASKIQ_RABBITMQ_PASSWORD": "guest",
            "TASKIQ_RABBITMQ_VHOST": "/",
            "RATE_LIMITER_REDIS_HOST": cfg.RATE_LIMITER_REDIS_HOST,
            "RATE_LIMITER_REDIS_PORT": str(cfg.RATE_LIMITER_REDIS_PORT),
            "RATE_LIMITER_REDIS_DB": "0",
            "RATE_LIMITER_REDIS_PASSWORD": "",
            "MAIL_QUEUE_NAME": mail_env.queue_name,
            "MAIL_SMTP_HOST": smtp.get_container_host_ip(),
            "MAIL_SMTP_PORT": str(smtp.get_exposed_port(1025)),
            "MAIL_SMTP_FROM": "sender@example.com",
            "MAIL_SMTP_USERNAME": "",
            "MAIL_SMTP_PASSWORD": "",
            "MAIL_SMTP_USE_TLS": "false",
            "MAIL_SMTP_START_TLS": "false",
            "MAIL_SMTP_ALLOW_INSECURE": "true",
            "MAIL_TOKEN_SECRET": mail_env.token_secret.get_secret_value(),
            "MAIL_PAYLOAD_ENCRYPTION_KEY": mail_env.payload_encryption_key.get_secret_value(),
        }
        payload = {
            "account": "transportuser",
            "password": "Test-only-123!",
            "confirm_password": "Test-only-123!",
            "email": "transport@example.com",
        }
        response = await email_client.post("/api/v1/users/register", json=payload)
        assert response.status_code == 201, response.text
        account_id = response.json()["id"]
        root = Path(__file__).parents[6]
        log_path = root / ".cache/email-worker-transport.log"
        with log_path.open("w", encoding="utf-8") as log:
            worker = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "taskiq",
                    "worker",
                    "src.modules.email_verification.worker:broker",
                    "--workers",
                    "1",
                    "--ack-type",
                    "when_executed",
                ],
                cwd=Path(__file__).parents[5],
                env=env,
                stdout=log,
                stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                await broker.startup()

                async def publish(job_id):
                    """发布任务ID，不把验证码或收件人放到RabbitMQ中。"""
                    await publish_only.kicker().with_labels(queue_name=mail_env.queue_name).kiq(job_id)

                factory = async_sessionmaker(test_db_engine, expire_on_commit=False)
                await dispatch_once(publish, factory)
                endpoint = f"http://{smtp.get_container_host_ip()}:{smtp.get_exposed_port(8025)}"
                async with httpx.AsyncClient() as http:
                    deadline = time.monotonic() + 45
                    messages = []
                    while time.monotonic() < deadline:
                        result = await http.get(endpoint + "/api/v1/messages")
                        messages = result.json().get("messages", [])
                        if len(messages) == 2:
                            break
                        if worker.poll() is not None:
                            raise AssertionError("独立worker提前退出，检查项目缓存中的脱敏日志")
                        await asyncio.sleep(0.5)
                    assert len(messages) == 2, "Mailpit未收到两封邮件，检查项目缓存日志"
                    bodies = [(await http.get(endpoint + "/api/v1/message/" + row["ID"])).json() for row in messages]
                welcome = next(row for row in bodies if "欢迎" in row["Subject"])
                verification = next(row for row in bodies if "验证" in row["Subject"])
                assert "拼豆" in welcome["HTML"] and "/pictures" in welcome["Text"]
                assert "验证码" in verification["HTML"] and verification["Text"]
                code_payload = await db_session.scalar(
                    select(Job.payload).where(Job.user_id == account_id, Job.kind == "binding")
                )
                # 发送后载荷已清除；从捕获邮件取码，模拟实际用户。
                assert code_payload is None

                code = re.search(r"验证码：(\d{6})", verification["Text"]).group(1)
                login = await email_client.post(
                    "/api/v1/auth/login", data={"username": "transportuser", "password": payload["password"]}
                )
                email_client.headers.update({"X-CSRF-Token": login.json()["csrf_token"], "X-Expected-User-ID": str(account_id)})
                confirmed = await email_client.post(
                    URL + "/binding/confirm",
                    json={"request_id": response.json()["email_verification"]["request_id"], "code": code},
                )
                assert confirmed.status_code == 200 and confirmed.json()["email_verified"]
                # 使用真实Lua计数验证并发不能绕过限流。
                limiter = MailLimiter()
                identity = uuid4().hex

                async def counted():
                    try:
                        await limiter.check([(identity, 5, 3600)])
                        return 200
                    except HTTPException as error:
                        return error.status_code

                results = await asyncio.gather(*(counted() for _ in range(12)))
                assert results.count(200) == 5 and results.count(429) == 7
            finally:
                await broker.shutdown()
                children = psutil.Process(worker.pid).children(recursive=True) if worker.poll() is None else []
                worker.terminate()
                try:
                    worker.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.wait(timeout=5)
                # Windows终止父进程不保证退出子worker，只清理此测试进程树。
                for child in children:
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                psutil.wait_procs(children, timeout=5)
