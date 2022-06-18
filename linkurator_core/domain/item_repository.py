import abc
from typing import List, Optional
from uuid import UUID

from linkurator_core.domain.item import Item


class ItemRepository(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def add(self, item: Item):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, item_id: UUID) -> Optional[Item]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, item_id: UUID):
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_subscription_id(self, subscription_id: UUID) -> List[Item]:
        raise NotImplementedError

    @abc.abstractmethod
    def find(self, item: Item) -> Optional[Item]:
        raise NotImplementedError
