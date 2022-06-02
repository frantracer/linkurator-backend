import abc
import uuid
from typing import List

from linkurator_core.domain.subscription import Subscription


class SubscriptionService(abc.ABC):
    def get_subscriptions(self, user_id: uuid.UUID) -> List[Subscription]:
        raise NotImplementedError()
