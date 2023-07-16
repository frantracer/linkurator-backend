import abc
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from linkurator_core.domain.items.item import Item


class ItemRepository(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def add(self, item: Item):
        raise NotImplementedError

    @abc.abstractmethod
    def add_bulk(self, items: List[Item]):
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
    def get_items_created_before(self, date: datetime, limit: int) -> List[Item]:
        raise NotImplementedError

    @abc.abstractmethod
    def find(self, item: Item) -> Optional[Item]:
        raise NotImplementedError

    @abc.abstractmethod
    def find_sorted_by_publish_date(
            self,
            sub_ids: List[UUID],
            published_after: datetime,
            created_before: datetime,
            max_results: int,
            page_number: int
    ) -> Tuple[List[Item], int]:
        raise NotImplementedError
