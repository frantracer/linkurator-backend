from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import AnyUrl

from linkurator_core.domain.subscriptions.subscription import (
    Subscription,
    SubscriptionProvider,
)


@dataclass
class SubscriptionFilterCriteria:
    updated_before: Optional[datetime] = None


class SubscriptionRepository(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    async def add(self, subscription: Subscription) -> None: ...

    @abstractmethod
    async def get(self, subscription_id: UUID) -> Optional[Subscription]: ...

    @abstractmethod
    async def get_list(self, subscription_ids: List[UUID]) -> List[Subscription]: ...

    @abstractmethod
    async def delete(self, subscription_id: UUID) -> None: ...

    @abstractmethod
    async def delete_all(self) -> None: ...

    @abstractmethod
    async def update(self, subscription: Subscription) -> None: ...

    @abstractmethod
    async def find_by_url(self, url: AnyUrl) -> Optional[Subscription]: ...

    @abstractmethod
    async def find_latest_scan_before(
            self, datetime_limit: datetime
    ) -> List[Subscription]: ...

    @abstractmethod
    async def find_by_name(self, name: str) -> List[Subscription]: ...

    @abstractmethod
    async def find(self, criteria: SubscriptionFilterCriteria) -> List[Subscription]: ...

    @abstractmethod
    async def count_subscriptions(self, provider: SubscriptionProvider | None = None) -> int: ...
