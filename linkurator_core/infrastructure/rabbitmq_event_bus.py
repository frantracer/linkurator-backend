import asyncio
from typing import Type, Callable, Coroutine, Any, Optional

import aio_pika

from linkurator_core.domain.common.event import Event
from linkurator_core.domain.common.event_bus_service import EventBusService

STOP_PAYLOAD = 'STOP'


class RabbitMQEventBus(EventBusService):
    def __init__(self, host: str, port: int, username: str, password: str, queue_name: str = 'event_queue',
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.event_handlers: dict[Type[Event], list[Callable[[Event], Coroutine[Any, Any, None]]]] = {}
        self.connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self.queue_name = queue_name
        self._is_running = False
        self.loop = loop or asyncio.get_event_loop()
        self.url = f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/"

    async def publish(self, event: Event) -> None:
        event_data = event.serialize()
        await self._publish(event_data)

    async def _publish(self, data: str) -> None:
        if self.connection is None:
            self.connection = await aio_pika.connect_robust(self.url, loop=self.loop)

        channel = await self.connection.channel()
        await channel.default_exchange.publish(
            aio_pika.Message(body=data.encode()),
            routing_key=self.queue_name
        )
        await channel.close()

    def subscribe(self, event_type: Type[Event], callback: Callable[[Event], Coroutine[Any, Any, None]]) -> None:
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []

        self.event_handlers[event_type].append(callback)

    async def start(self) -> None:
        self.connection = await aio_pika.connect_robust(self.url, loop=self.loop)

        if self.connection is None:
            raise ValueError('Connection is not established')

        async with self.connection:
            channel = await self.connection.channel()
            queue = await channel.declare_queue(self.queue_name)

            self._is_running = True

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        payload = message.body.decode()

                        if payload == STOP_PAYLOAD:
                            break

                        event = Event.deserialize(payload)

                        if event.__class__ in self.event_handlers:
                            for handler in self.event_handlers[event.__class__]:
                                self.loop.create_task(handler(event))

            await channel.close()

            self._is_running = False

    async def stop(self) -> None:
        if self.connection is None:
            raise ValueError('Connection is not established')

        await self._publish(STOP_PAYLOAD)

    def is_running(self) -> bool:
        return self._is_running
