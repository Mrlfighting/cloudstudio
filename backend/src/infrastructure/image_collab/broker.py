"""图片协同编辑的 RabbitMQ 消息缓冲/分发（topic 交换机 + 每房间队列）。

- publish：把客户端消息发布到 topic 交换机（路由键 = collab.{space_id}.{picture_id}）
- subscribe/unsubscribe：为房间声明队列并消费 / 停止消费并删除队列
- 每房间一个队列 + 单消费者 prefetch=1 → 房间内消息严格 FIFO，不同房间并行
"""

import json
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika import ExchangeType, IncomingMessage, Message

EXCHANGE_NAME = "collab"
Handler = Callable[[dict[str, Any]], Awaitable[None]]


def _routing_key(space_id: int, picture_id: int) -> str:
    return f"collab.{space_id}.{picture_id}"


def _queue_name(space_id: int, picture_id: int) -> str:
    return f"collab.{space_id}.{picture_id}"


class CollabBroker:
    """RabbitMQ 消息缓冲：发布 + 每房间队列消费。"""

    def __init__(self, url: str) -> None:
        self._url = url
        self._connection: Any = None
        self._channel: Any = None
        self._exchange: Any = None
        # room_key -> (queue, consumer_tag)
        self._consumers: dict[str, tuple[Any, str]] = {}

    @property
    def available(self) -> bool:
        return self._channel is not None

    async def connect(self) -> None:
        """建立连接、通道、声明 topic 交换机（失败抛出，由上层决定降级）。"""
        self._connection = await aio_pika.connect(self._url, timeout=3.0)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=1)
        self._exchange = await self._channel.declare_exchange(EXCHANGE_NAME, ExchangeType.TOPIC)

    async def publish(self, space_id: int, picture_id: int, payload: dict[str, Any]) -> None:
        """发布消息到房间路由键。"""
        if self._exchange is None:
            return
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        await self._exchange.publish(
            Message(body=body, content_type="application/json"),
            routing_key=_routing_key(space_id, picture_id),
        )

    async def subscribe(self, space_id: int, picture_id: int, handler: Handler) -> None:
        """为房间声明队列并开始消费（幂等：已订阅则跳过）。"""
        if self._channel is None:
            return
        room_key = f"{space_id}:{picture_id}"
        if room_key in self._consumers:
            return

        queue = await self._channel.declare_queue(_queue_name(space_id, picture_id), durable=False)
        await queue.bind(self._exchange, _routing_key(space_id, picture_id))

        async def _on_message(message: IncomingMessage) -> None:
            async with message.process():
                payload = json.loads(message.body.decode("utf-8"))
                await handler(payload)

        consumer_tag = await queue.consume(_on_message)
        self._consumers[room_key] = (queue, consumer_tag)

    async def unsubscribe(self, space_id: int, picture_id: int) -> None:
        """停止消费并删除房间队列。"""
        room_key = f"{space_id}:{picture_id}"
        entry = self._consumers.pop(room_key, None)
        if entry is None:
            return
        queue, consumer_tag = entry
        try:
            await queue.cancel(consumer_tag)
        except Exception:
            pass
        try:
            await queue.delete()
        except Exception:
            pass

    async def close(self) -> None:
        """关闭通道与连接。"""
        self._consumers.clear()
        if self._channel is not None:
            await self._channel.close()
        if self._connection is not None:
            await self._connection.close()
