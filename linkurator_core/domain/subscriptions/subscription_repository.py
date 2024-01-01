import abc
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from linkurator_core.domain.subscriptions.subscription import Subscription


class SubscriptionRepository(abc.ABC):
    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    def add(self, subscription: Subscription) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, subscription_id: UUID) -> Optional[Subscription]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_list(self, subscription_ids: List[UUID]) -> List[Subscription]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, subscription_id: UUID) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, subscription: Subscription) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def find(self, subscription: Subscription) -> Optional[Subscription]:
        raise NotImplementedError

    @abc.abstractmethod
    def find_latest_scan_before(self, datetime_limit: datetime) -> List[Subscription]:
        raise NotImplementedError
