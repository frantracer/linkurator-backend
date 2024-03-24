from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Type
from uuid import uuid4

from linkurator_core.domain.common.event import Event
from linkurator_core.domain.common.event_bus_service import EventBusService


class ShutdownEvent(Event):
    @classmethod
    def new(cls) -> ShutdownEvent:
        return cls(
            id=uuid4(),
            created_at=datetime.utcnow()
        )


class AsyncioEventBusService(EventBusService):
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._callbacks: Dict[Type[Event], List[Callable[[Event], Coroutine[Any, Any, None]]]] = {}
        self._is_running = False

    async def publish(self, event: Event) -> None:
        self._queue.put_nowait(event)

    def subscribe(self, event_type: Type[Event], callback: Callable[[Event], Coroutine[Any, Any, None]]) -> None:
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    async def start(self) -> None:
        logging.info('event bus service started')
        self._is_running = True
        while self._is_running:
            event = await self._queue.get()
            if isinstance(event, ShutdownEvent):
                self._is_running = False
            else:
                event_type = type(event)
                if event_type in self._callbacks:
                    for callback in self._callbacks[event_type]:
                        asyncio.create_task(callback(event))
            self._queue.task_done()
        logging.info('event bus service stopped')

    async def stop(self) -> None:
        logging.info('stopping event bus service')
        self._queue.put_nowait(ShutdownEvent.new())

    def is_running(self) -> bool:
        return self._is_running
