import abc
from enum import Enum
from typing import Callable


class EventType(Enum):
    ACCOUNT_CREATED = 'account_created'
    SHUTDOWN = 'shutdown'


class Event:
    def __init__(self, event_type, data):
        self.event_type = event_type
        self.data = data

    def __str__(self):
        return f"Event type: {self.event_type}, data: {self.data}"


class EventBusService(abc.ABC):
    @abc.abstractmethod
    def publish(self, event: Event) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    async def start(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    async def stop(self) -> None:
        raise NotImplementedError()
