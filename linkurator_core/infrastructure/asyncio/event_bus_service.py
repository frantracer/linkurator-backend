import asyncio
from asyncio import AbstractEventLoop
from typing import Callable, Dict, List

from linkurator_core.application.event_bus_service import EventBusService, Event, EventType


class AsyncioEventBusService(EventBusService):
    def __init__(self):
        self.event_loop: AbstractEventLoop = asyncio.get_event_loop()
        self.queue: asyncio.Queue = asyncio.Queue(loop=self.event_loop)
        self.callbacks: Dict[EventType, List[Callable]] = {}
        self._is_running = False

    def publish(self, event: Event):
        self.queue.put_nowait(event)

    def subscribe(self, event_type: EventType, callback: Callable):
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)

    async def start(self) -> None:
        print('starting event bus service')
        self._is_running = True
        while self._is_running:
            event = await self.queue.get()
            if event.event_type == EventType.SHUTDOWN:
                self._is_running = False
            if event.event_type in self.callbacks:
                for callback in self.callbacks[event.event_type]:
                    callback(event)
            self.queue.task_done()

    async def stop(self):
        await asyncio.sleep(0)
        self.publish(Event(EventType.SHUTDOWN, 'shutdown'))
