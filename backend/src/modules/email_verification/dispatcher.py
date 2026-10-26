"""可独立重启的邮件调度进程：python -m src.modules.email_verification.dispatcher。"""

import asyncio
import logging

from .config import get_mail_settings
from .outbox import cleanup, dispatch_once, expire_jobs
from .worker import broker, deliver

logger = logging.getLogger(__name__)


async def publish(job_id: str) -> None:
    """网络故障有整体超时，失败保留数据库任务。"""
    async with asyncio.timeout(10):
        await deliver.kicker().with_labels(queue_name=get_mail_settings().queue_name).kiq(job_id)


async def main() -> None:
    """只有调度器连接RabbitMQ；API不等待中间件。"""
    cfg = get_mail_settings()
    if not cfg.enabled:
        raise RuntimeError("请先启用并配置MAIL_ENABLED")
    started, rounds = False, 0
    try:
        while True:
            try:
                await expire_jobs()
                if rounds % 1800 == 0:
                    await cleanup()
                rounds += 1
                if not started:
                    async with asyncio.timeout(10):
                        await broker.startup()
                    started = True
                await dispatch_once(publish)
            except Exception:
                # 不输出包含AMQP凭据的异常或连接URL。
                logger.error("邮件调度暂不可用，任务仍保留在数据库")
                if not started:
                    await broker.shutdown()
            await asyncio.sleep(cfg.poll_seconds)
    finally:
        await broker.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
