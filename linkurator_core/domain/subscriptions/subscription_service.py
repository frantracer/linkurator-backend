import abc
from datetime import datetime
import uuid
from typing import List, Optional

from linkurator_core.domain.items.item import Item
from linkurator_core.domain.subscriptions.subscription import Subscription


class SubscriptionService(abc.ABC):
    @abc.abstractmethod
    async def get_subscriptions(self, user_id: uuid.UUID) -> List[Subscription]:
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_subscription(self, sub_id: uuid.UUID) -> Optional[Subscription]:
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_items(self, sub_id: uuid.UUID, from_date: datetime) -> List[Item]:
        raise NotImplementedError()
