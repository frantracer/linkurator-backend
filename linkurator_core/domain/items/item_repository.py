import abc
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from pydantic.networks import AnyUrl

from linkurator_core.domain.items.item import Item, ItemProvider

TotalItems = int
FindResult = Tuple[List[Item], TotalItems]


@dataclass
class ItemFilterCriteria:
    subscription_ids: Optional[List[UUID]] = None
    published_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    url: Optional[AnyUrl] = None
    last_version: Optional[int] = None
    provider: Optional[ItemProvider] = None
    text: Optional[str] = None


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
    def find_items(self, criteria: ItemFilterCriteria, page_number: int, limit: int) -> FindResult:
        raise NotImplementedError

    @abc.abstractmethod
    def delete_all_items(self):
        raise NotImplementedError
