import abc
from typing import Optional
from uuid import UUID

from linkurator_core.domain.subscription import Subscription


class SubscriptionRepository(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def add(self, subscription: Subscription):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, subscription_id: UUID) -> Optional[Subscription]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, subscription_id: UUID):
        raise NotImplementedError

    @abc.abstractmethod
    def find(self, subscription: Subscription) -> Optional[Subscription]:
        raise NotImplementedError
