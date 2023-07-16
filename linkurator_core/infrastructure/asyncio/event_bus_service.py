import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List, Type

from linkurator_core.domain.common.event_bus_service import Event, EventBusService

SHUTDOWN_MESSAGE = 'shutdown'


class AsyncioEventBusService(EventBusService):
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._callbacks: Dict[Type[Event], List[Callable[[Event], Coroutine[Any, Any, None]]]] = {}
        self._is_running = False

    def publish(self, event: Event):
        self._queue.put_nowait(event)

    def subscribe(self, event_type: Type[Event], callback: Callable[[Event], Coroutine[Any, Any, None]]):
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    async def start(self) -> None:
        logging.info('event bus service started')
        self._is_running = True
        while self._is_running:
            event = await self._queue.get()
            if isinstance(event, Event):
                event_type = type(event)
                if event_type in self._callbacks:
                    for callback in self._callbacks[event_type]:
                        asyncio.create_task(callback(event))
            elif event == SHUTDOWN_MESSAGE:
                self._is_running = False
            self._queue.task_done()
        logging.info('event bus service stopped')

    async def stop(self):
        logging.info('stopping event bus service')
        self._queue.put_nowait(SHUTDOWN_MESSAGE)
