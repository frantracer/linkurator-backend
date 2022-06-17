import abc
from typing import Any, Callable, Coroutine, Type

from linkurator_core.domain.event import Event


class EventBusService(abc.ABC):
    @abc.abstractmethod
    def publish(self, event: Event) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def subscribe(self, event_type: Type[Event], callback: Callable[[Event], Coroutine[Any, Any, None]]):
        raise NotImplementedError()

    @abc.abstractmethod
    async def start(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    async def stop(self) -> None:
        raise NotImplementedError()
