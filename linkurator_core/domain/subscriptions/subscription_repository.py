from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import AnyUrl

from linkurator_core.domain.items.item import ItemProvider
from linkurator_core.domain.subscriptions.subscription import (
    Subscription,
)


@dataclass
class SubscriptionFilterCriteria:
    updated_before: datetime | None = None
    has_summary: bool | None = None


class SubscriptionRepository(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    async def add(self, subscription: Subscription) -> None: ...

    @abstractmethod
    async def get(self, subscription_id: UUID) -> Subscription | None: ...

    @abstractmethod
    async def get_list(self, subscription_ids: list[UUID]) -> list[Subscription]: ...

    @abstractmethod
    async def delete(self, subscription_id: UUID) -> None: ...

    @abstractmethod
    async def delete_all(self) -> None: ...

    @abstractmethod
    async def update(self, subscription: Subscription) -> None: ...

    @abstractmethod
    async def find_by_url(self, url: AnyUrl) -> Subscription | None: ...

    @abstractmethod
    async def find_latest_scan_before(
            self, datetime_limit: datetime,
    ) -> list[Subscription]: ...

    @abstractmethod
    async def find_by_name(self, name: str) -> list[Subscription]: ...

    @abstractmethod
    async def find(self, criteria: SubscriptionFilterCriteria) -> list[Subscription]: ...

    @abstractmethod
    async def count_subscriptions(self, provider: ItemProvider | None = None) -> int: ...
