from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from functools import reduce

from pydantic import AnyUrl

from linkurator_core.domain.items.item import Item
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService


class GeneralSubscriptionService:
    def __init__(self, services: list[SubscriptionService]) -> None:
        self.services = services

    async def get_subscriptions(
            self,
            user_id: uuid.UUID,
            access_token: str,
    ) -> list[Subscription]:
        results = await asyncio.gather(
            *[service.get_subscriptions(user_id=user_id, access_token=access_token)
              for service in self.services],
        )
        return [sub for result in results for sub in result]

    async def get_subscription(
            self,
            sub_id: uuid.UUID,
    ) -> Subscription | None:
        results = await asyncio.gather(
            *[service.get_subscription(sub_id) for service in self.services],
        )
        return next((r for r in results if r is not None), None)

    async def get_items(
            self,
            item_ids: set[uuid.UUID],
    ) -> set[Item]:
        results = await asyncio.gather(
            *[service.get_items(item_ids) for service in self.services],
        )
        return reduce(lambda a, b: a | b, results, set())

    async def get_subscription_items(
            self,
            sub_id: uuid.UUID,
            from_date: datetime,
    ) -> list[Item]:
        results = await asyncio.gather(
            *[service.get_subscription_items(sub_id, from_date) for service in self.services],
        )
        return [item for result in results for item in result]

    async def get_subscription_from_url(
            self,
            url: AnyUrl,
    ) -> Subscription | None:
        results = await asyncio.gather(
            *[service.get_subscription_from_url(url) for service in self.services],
        )
        return next((r for r in results if r is not None), None)

    async def get_subscriptions_from_name(
            self,
            name: str,
    ) -> list[Subscription]:
        results = await asyncio.gather(
            *[service.get_subscriptions_from_name(name) for service in self.services],
        )
        return [sub for result in results for sub in result]
