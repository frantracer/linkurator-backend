import asyncio
from typing import Callable, Dict, List

from linkurator_core.application.event_bus_service import Event, EventBusService, EventType


class AsyncioEventBusService(EventBusService):
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._callbacks: Dict[EventType, List[Callable]] = {}
        self._is_running = False

    def publish(self, event: Event):
        self._queue.put_nowait(event)

    def subscribe(self, event_type: EventType, callback: Callable):
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    async def start(self) -> None:
        print('event bus service started')
        self._is_running = True
        while self._is_running:
            event = await self._queue.get()
            if event.event_type == EventType.SHUTDOWN:
                self._is_running = False
            if event.event_type in self._callbacks:
                for callback in self._callbacks[event.event_type]:
                    callback(event)
            self._queue.task_done()
        print('event bus service stopped')

    async def stop(self):
        print('stopping event bus service')
        self.publish(Event(EventType.SHUTDOWN, 'shutdown'))
