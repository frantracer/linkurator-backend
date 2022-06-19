import abc
from datetime import datetime
import uuid
from typing import List

from linkurator_core.domain.item import Item
from linkurator_core.domain.subscription import Subscription


class SubscriptionService(abc.ABC):
    async def get_subscriptions(self, user_id: uuid.UUID) -> List[Subscription]:
        raise NotImplementedError()

    async def get_items(self, sub_id: uuid.UUID, from_date: datetime) -> List[Item]:
        raise NotImplementedError()
