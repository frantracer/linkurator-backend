import abc
from typing import Any, Callable, Coroutine, Type

from linkurator_core.domain.common.event import Event


class EventBusService(abc.ABC):
    @abc.abstractmethod
    async def publish(self, event: Event) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def subscribe(self, event_type: Type[Event], callback: Callable[[Event], Coroutine[Any, Any, None]]) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    async def start(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    async def stop(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def is_running(self) -> bool:
        raise NotImplementedError()
