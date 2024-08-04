import abc
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID

from pydantic.networks import AnyUrl

from linkurator_core.domain.items.interaction import Interaction
from linkurator_core.domain.items.item import Item, ItemProvider


@dataclass
class AnyItemInteraction:
    without_interactions: Optional[bool] = None
    recommended: Optional[bool] = None
    discouraged: Optional[bool] = None
    viewed: Optional[bool] = None
    hidden: Optional[bool] = None


@dataclass
class ItemFilterCriteria:
    item_ids: Optional[set[UUID]] = None
    subscription_ids: Optional[List[UUID]] = None
    published_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None
    created_before: Optional[datetime] = None
    url: Optional[AnyUrl] = None
    last_version: Optional[int] = None
    provider: Optional[ItemProvider] = None
    text: Optional[str] = None
    interactions_from_user: Optional[UUID] = None
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    interactions: AnyItemInteraction = AnyItemInteraction()


class ItemRepository(abc.ABC):
    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    async def upsert_items(self, items: List[Item]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_item(self, item_id: UUID) -> Optional[Item]:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_item(self, item_id: UUID) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def find_items(self, criteria: ItemFilterCriteria, page_number: int, limit: int) -> List[Item]:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_all_items(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def add_interaction(self, interaction: Interaction) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_interaction(self, interaction_id: UUID) -> Optional[Interaction]:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_interaction(self, interaction_id: UUID) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_user_interactions_by_item_id(
            self, user_id: UUID, item_ids: List[UUID]
    ) -> Dict[UUID, List[Interaction]]:
        raise NotImplementedError
