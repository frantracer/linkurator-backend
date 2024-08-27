from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic.networks import AnyUrl

from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository


class InMemorySubscriptionRepository(SubscriptionRepository):
    def __init__(self) -> None:
        super().__init__()
        self.subscriptions: dict[UUID, Subscription] = {}

    async def add(self, subscription: Subscription) -> None:
        self.subscriptions[subscription.uuid] = subscription

    async def get(self, subscription_id: UUID) -> Optional[Subscription]:
        return self.subscriptions.get(subscription_id)

    async def get_list(self, subscription_ids: List[UUID]) -> List[Subscription]:
        subs = [subscription for subscription in self.subscriptions.values() if subscription.uuid in subscription_ids]
        return sorted(subs, key=lambda x: x.created_at, reverse=True)

    async def delete(self, subscription_id: UUID) -> None:
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]

    async def update(self, subscription: Subscription) -> None:
        if self._find_by_url(subscription.url) is None:
            self.subscriptions[subscription.uuid] = subscription

    async def find(self, subscription: Subscription) -> Optional[Subscription]:
        return self._find_by_url(subscription.url)

    async def find_latest_scan_before(self, datetime_limit: datetime) -> List[Subscription]:
        subs = [subscription for subscription in self.subscriptions.values() if
                subscription.scanned_at < datetime_limit]
        return sorted(subs, key=lambda x: x.created_at, reverse=True)

    def _find_by_url(self, url: AnyUrl) -> Optional[Subscription]:
        for subscription in self.subscriptions.values():
            if subscription.url == url:
                return subscription
        return None
