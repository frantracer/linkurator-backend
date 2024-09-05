import abc
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import AnyUrl

from linkurator_core.domain.subscriptions.subscription import Subscription


class SubscriptionRepository(abc.ABC):
    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    async def add(self, subscription: Subscription) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, subscription_id: UUID) -> Optional[Subscription]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_list(self, subscription_ids: List[UUID]) -> List[Subscription]:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, subscription_id: UUID) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_all(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, subscription: Subscription) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def find_by_url(self, url: AnyUrl) -> Optional[Subscription]:
        raise NotImplementedError

    @abc.abstractmethod
    async def find_latest_scan_before(self, datetime_limit: datetime) -> List[Subscription]:
        raise NotImplementedError

    @abc.abstractmethod
    async def find_by_name(self, name: str) -> List[Subscription]:
        raise NotImplementedError
