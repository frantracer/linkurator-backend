import abc
import uuid
from datetime import datetime
from typing import List, Optional

from linkurator_core.domain.items.item import Item
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential


class SubscriptionService(abc.ABC):
    @abc.abstractmethod
    async def get_subscriptions(
            self,
            user_id: uuid.UUID,
            credential: Optional[ExternalServiceCredential] = None
    ) -> List[Subscription]:
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_subscription(
            self,
            sub_id: uuid.UUID,
            credential: Optional[ExternalServiceCredential] = None
    ) -> Optional[Subscription]:
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_items(
            self,
            sub_id: uuid.UUID,
            from_date: datetime,
            credential: Optional[ExternalServiceCredential] = None
    ) -> List[Item]:
        raise NotImplementedError()
