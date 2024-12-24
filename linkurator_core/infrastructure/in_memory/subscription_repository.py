from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import AnyUrl
from unidecode import unidecode

from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import (
    SubscriptionRepository,
)


class InMemorySubscriptionRepository(SubscriptionRepository):
    def __init__(self) -> None:
        super().__init__()
        self.subscriptions: dict[UUID, Subscription] = {}

    async def add(self, subscription: Subscription) -> None:
        self.subscriptions[subscription.uuid] = subscription

    async def get(self, subscription_id: UUID) -> Optional[Subscription]:
        return self.subscriptions.get(subscription_id)

    async def get_list(self, subscription_ids: List[UUID]) -> List[Subscription]:
        subs = [
            subscription
            for subscription in self.subscriptions.values()
            if subscription.uuid in subscription_ids
        ]
        return sorted(subs, key=lambda x: x.created_at, reverse=True)

    async def delete(self, subscription_id: UUID) -> None:
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]

    async def delete_all(self) -> None:
        self.subscriptions = {}

    async def update(self, subscription: Subscription) -> None:
        existing_sub = self._find_by_url(subscription.url)
        if existing_sub is None or (
            existing_sub is not None and existing_sub.uuid == subscription.uuid
        ):
            self.subscriptions[subscription.uuid] = subscription

    async def find_by_url(self, url: AnyUrl) -> Optional[Subscription]:
        return self._find_by_url(url)

    async def find_latest_scan_before(
        self, datetime_limit: datetime
    ) -> List[Subscription]:
        subs = [
            subscription
            for subscription in self.subscriptions.values()
            if subscription.scanned_at < datetime_limit
        ]
        return sorted(subs, key=lambda x: x.created_at, reverse=True)

    async def find_by_name(self, name: str) -> List[Subscription]:
        search_terms = unidecode(name.lower()).split(" ")

        def search_terms_in_name(terms: list[str], name: str) -> bool:
            return all(term in name for term in terms)

        subs = [
            subscription
            for subscription in self.subscriptions.values()
            if search_terms_in_name(search_terms, unidecode(subscription.name.lower()))
        ]
        return sorted(subs, key=lambda x: x.created_at, reverse=True)

    def _find_by_url(self, url: AnyUrl) -> Optional[Subscription]:
        for subscription in self.subscriptions.values():
            if subscription.url == url:
                return subscription
        return None

    async def count_subscriptions(self, provider: Optional[str] = None) -> int:
        if provider is None:
            return len(self.subscriptions)
        return len(
            [
                subscription
                for subscription in self.subscriptions.values()
                if subscription.provider == provider
            ]
        )
