"""独立持久RabbitMQ队列，既有默认任务与协同队列均不改变。"""

from urllib.parse import quote

from taskiq_aio_pika import AioPikaBroker, Exchange, Queue, QueueType

from ...infrastructure.config.settings import get_settings
from .config import get_mail_settings


def create_broker():
    """复用RabbitMQ连接配置，但使用独立交换机/任务队列/死信队列。"""
    cfg, settings = get_mail_settings(), get_settings()
    user = quote(settings.TASKIQ_RABBITMQ_USER, safe="")
    password = quote(settings.TASKIQ_RABBITMQ_PASSWORD, safe="")
    vhost = quote(settings.TASKIQ_RABBITMQ_VHOST.lstrip("/"), safe="")
    url = f"amqp://{user}:{password}@{settings.TASKIQ_RABBITMQ_HOST}:{settings.TASKIQ_RABBITMQ_PORT}/{vhost}"
    return AioPikaBroker(
        url=url,
        qos=2,
        exchange=Exchange(name=f"{cfg.queue_name}.exchange", durable=True),
        task_queues=[Queue(name=cfg.queue_name, routing_key=cfg.queue_name, type=QueueType.QUORUM, durable=True)],
        dead_letter_queue=Queue(name=f"{cfg.queue_name}.dead", durable=True),
    )
