from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from functools import reduce

from pydantic import AnyUrl

from linkurator_core.domain.items.item import Item
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential


class GeneralSubscriptionService(SubscriptionService):
    def __init__(self, services: list[SubscriptionService]) -> None:
        self.services = services

    async def get_subscriptions(
            self,
            user_id: uuid.UUID,
            access_token: str,
            credential: ExternalServiceCredential | None = None,
    ) -> list[Subscription]:
        results = await asyncio.gather(
            *[service.get_subscriptions(user_id=user_id, credential=credential, access_token=access_token)
              for service in self.services],
        )
        return [sub for result in results for sub in result]

    async def get_subscription(
            self,
            sub_id: uuid.UUID,
            credential: ExternalServiceCredential | None = None,
    ) -> Subscription | None:
        results = await asyncio.gather(
            *[service.get_subscription(sub_id, credential) for service in self.services],
        )
        return next((r for r in results if r is not None), None)

    async def get_items(
            self,
            item_ids: set[uuid.UUID],
            credential: ExternalServiceCredential | None = None,
    ) -> set[Item]:
        results = await asyncio.gather(
            *[service.get_items(item_ids, credential) for service in self.services],
        )
        return reduce(lambda a, b: a | b, results, set())

    async def get_subscription_items(
            self,
            sub_id: uuid.UUID,
            from_date: datetime,
            credential: ExternalServiceCredential | None = None,
    ) -> list[Item]:
        results = await asyncio.gather(
            *[service.get_subscription_items(sub_id, from_date, credential) for service in self.services],
        )
        return [item for result in results for item in result]

    async def get_subscription_from_url(
            self,
            url: AnyUrl,
            credential: ExternalServiceCredential | None = None,
    ) -> Subscription | None:
        results = await asyncio.gather(
            *[service.get_subscription_from_url(url, credential) for service in self.services],
        )
        return next((r for r in results if r is not None), None)

    async def get_subscriptions_from_name(
            self,
            name: str,
            credential: ExternalServiceCredential | None = None,
    ) -> list[Subscription]:
        results = await asyncio.gather(
            *[service.get_subscriptions_from_name(name, credential) for service in self.services],
        )
        return [sub for result in results for sub in result]
