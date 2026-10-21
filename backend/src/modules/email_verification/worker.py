"""邮件worker入口：从backend执行taskiq worker src.modules.email_verification.worker:broker --ack-type when_executed。"""

from uuid import UUID

from taskiq.events import TaskiqEvents

from .broker import create_broker
from .config import get_mail_settings
from .outbox import process

broker = create_broker()


async def check_worker_enabled(state) -> None:
    """关闭功能时worker应启动失败，而不是连接队列后反复消费失败任务。"""
    if not get_mail_settings().enabled:
        raise RuntimeError("邮箱功能未开启，请配置MAIL_ENABLED后启动邮件worker")


broker.add_event_handler(TaskiqEvents.WORKER_STARTUP, check_worker_enabled)


@broker.task(task_name="email:deliver")
async def deliver(job_id: str) -> None:
    """任务参数不包含收件人、验证码或任何凭据。"""
    await process(UUID(job_id))
