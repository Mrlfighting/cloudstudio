"""协同结果事件分发：topic 交换机与每实例、每房间的专属队列。

命令在原连接持共享锁执行，消息只携带已完成的响应；消费者不再次落库。
序号去重和临时状态由 Redis 维护，Robust 连接恢复断线后的订阅。
"""

import asyncio
import json
import uuid
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
        self._instance_id = uuid.uuid4().hex
        self._connect_lock = asyncio.Lock()
        self._connection: Any = None
        self._channel: Any = None
        self._exchange: Any = None
        # room_key -> (queue, consumer_tag)
        self._consumers: dict[str, tuple[Any, str]] = {}

    @property
    def available(self) -> bool:
        return self._is_available()

    def _is_available(self) -> bool:
        """每次重新读取连接状态，等待连接锁期间状态可能已经变化。"""
        return self._channel is not None and not self._channel.is_closed and not self._connection.is_closed

    async def connect(self) -> None:
        """建立连接、通道、声明 topic 交换机（失败抛出，由上层决定降级）。"""
        self._connection = await aio_pika.connect_robust(self._url, timeout=3.0, reconnect_interval=1)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=1)
        self._exchange = await self._channel.declare_exchange(EXCHANGE_NAME, ExchangeType.TOPIC)

    async def publish(self, space_id: int, picture_id: int, payload: dict[str, Any]) -> None:
        """发布消息到房间路由键。"""
        await self.ensure_connected()
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        await self._exchange.publish(
            Message(body=body, content_type="application/json"),
            routing_key=_routing_key(space_id, picture_id),
            timeout=2,
        )

    async def subscribe(self, space_id: int, picture_id: int, handler: Handler) -> None:
        """为房间声明队列并开始消费（幂等：已订阅则跳过）。"""
        await self.ensure_connected()
        room_key = f"{space_id}:{picture_id}"
        if room_key in self._consumers:
            return

        # 每个实例独立接收已经处理的事件，禁止竞争消费导致其他实例看不到更新。
        queue = await self._channel.declare_queue(
            f"{_queue_name(space_id, picture_id)}.{self._instance_id}",
            durable=False,
            exclusive=True,
            auto_delete=True,
        )
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

    async def ensure_connected(self) -> None:
        """启动连接失败后仍可重试；已建立的 Robust 连接负责恢复订阅。"""
        if self._is_available():
            return
        async with self._connect_lock:
            if self._is_available():
                return
            if self._connection is not None and not self._connection.is_closed and self._channel is not None:
                await asyncio.wait_for(self._connection.connected.wait(), timeout=3)
                await asyncio.wait_for(self._channel.ready(), timeout=3)
            else:
                await self.connect()
