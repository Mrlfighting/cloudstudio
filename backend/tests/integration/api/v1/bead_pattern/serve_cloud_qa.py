"""手动浏览器验收服务：只在 Docker 临时数据库建测试账号，退出即删除容器。

从 backend 执行：../.venv/Scripts/python.exe tests/integration/api/v1/bead_pattern/serve_cloud_qa.py
"""

import asyncio
import os
import sys
from pathlib import Path

import uvicorn
from testcontainers.postgres import PostgresContainer


def serve() -> None:
    """配置先于应用导入，绝不沿用 .env 的数据库和认证密钥。"""
    with PostgresContainer("postgres:16-alpine") as pg:
        overrides = {
            "POSTGRES_SERVER": pg.get_container_host_ip(),
            "POSTGRES_PORT": str(pg.get_exposed_port(5432)),
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_DB": "test",
            "SESSION_BACKEND": "memory",
            "SESSION_SECURE_COOKIES": "false",
            "SECRET_KEY": "bead-local-qa-only-not-for-deployment",
            "ENVIRONMENT": "local",
            "DEBUG": "false",
            "CACHE_ENABLED": "false",
            "CACHE_TWO_TIER_ENABLED": "false",
            "RATE_LIMITER_ENABLED": "false",
            "IMAGE_COLLAB_ENABLED": "false",
            "IMAGE_SEARCH_ENABLED": "false",
            "IMAGE_OUTPAINTING_ENABLED": "false",
            "CREATE_TABLES_ON_STARTUP": "false",
            "TASKIQ_REDIS_HOST": "localhost",
        }
        os.environ.update(overrides)
        sys.path.insert(0, str(Path(__file__).parents[5]))
        # 仅测试入口允许延迟导入，以确保临时数据库覆盖先于配置加载。
        from crudauth import get_password_hash  # noqa: PLC0415

        from src.infrastructure.database.session import Base, engine, local_session  # noqa: PLC0415
        from src.interfaces.main import app  # noqa: PLC0415
        from src.modules.user.models import User  # noqa: PLC0415

        async def prepare() -> None:
            """合成测试账号与临时数据库同生命周期，不写开发库。"""
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            async with local_session() as db:
                for name in ("beadqaa", "beadqab"):
                    db.add(User(name=name, username=name, email=None, hashed_password=get_password_hash("Test-only-123!")))
                await db.commit()
            await engine.dispose()

        asyncio.run(prepare())
        print("BEAD_CLOUD_QA_READY port=8001 temporary-postgresql", flush=True)
        uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")


if __name__ == "__main__":
    serve()
