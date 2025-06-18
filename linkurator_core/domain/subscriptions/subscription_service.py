from __future__ import annotations

import abc
import uuid
from datetime import datetime

from pydantic import AnyUrl

from linkurator_core.domain.items.item import Item
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential


class SubscriptionService(abc.ABC):
    @abc.abstractmethod
    async def get_subscriptions(
            self,
            user_id: uuid.UUID,
            access_token: str,
            credential: ExternalServiceCredential | None = None,
    ) -> list[Subscription]: ...

    @abc.abstractmethod
    async def get_subscription(
            self,
            sub_id: uuid.UUID,
            credential: ExternalServiceCredential | None = None,
    ) -> Subscription | None: ...

    @abc.abstractmethod
    async def get_items(
            self,
            item_ids: set[uuid.UUID],
            credential: ExternalServiceCredential | None = None,
    ) -> set[Item]: ...

    @abc.abstractmethod
    async def get_subscription_items(
            self,
            sub_id: uuid.UUID,
            from_date: datetime,
            credential: ExternalServiceCredential | None = None,
    ) -> list[Item]: ...

    @abc.abstractmethod
    async def get_subscription_from_url(
            self,
            url: AnyUrl,
            credential: ExternalServiceCredential | None = None,
    ) -> Subscription | None: ...

    @abc.abstractmethod
    async def get_subscriptions_from_name(
            self,
            name: str,
            credential: ExternalServiceCredential | None = None,
    ) -> list[Subscription]: ...
