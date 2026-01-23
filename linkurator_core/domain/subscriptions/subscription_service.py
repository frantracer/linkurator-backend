from __future__ import annotations

import abc
import uuid
from datetime import datetime

from pydantic import AnyUrl

from linkurator_core.domain.items.item import DEFAULT_ITEM_VERSION, Item, ItemProvider
from linkurator_core.domain.subscriptions.subscription import Subscription


class SubscriptionService(abc.ABC):
    @abc.abstractmethod
    def provider_name(self) -> ItemProvider: ...

    def provider_alias(self) -> str:
        return self.provider_name()

    def provider_version(self) -> int:
        return DEFAULT_ITEM_VERSION

    def provider_thumbnail(self) -> str:
        return ""

    @abc.abstractmethod
    def refresh_period_minutes(self) -> int: ...

    @abc.abstractmethod
    async def get_subscriptions(
            self,
            user_id: uuid.UUID,
            access_token: str,
    ) -> list[Subscription]: ...

    @abc.abstractmethod
    async def get_subscription(
            self,
            sub_id: uuid.UUID,
    ) -> Subscription | None: ...

    @abc.abstractmethod
    async def get_items(
            self,
            item_ids: set[uuid.UUID],
    ) -> set[Item]: ...

    @abc.abstractmethod
    async def get_subscription_items(
            self,
            sub_id: uuid.UUID,
            from_date: datetime,
    ) -> list[Item]: ...

    @abc.abstractmethod
    async def get_subscription_from_url(
            self,
            url: AnyUrl,
    ) -> Subscription | None: ...

    @abc.abstractmethod
    async def get_subscriptions_from_name(
            self,
            name: str,
    ) -> list[Subscription]: ...
