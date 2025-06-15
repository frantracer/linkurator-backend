from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import AnyUrl

from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item, ItemProvider


@dataclass
class AnyItemInteraction:
    without_interactions: bool | None = None
    recommended: bool | None = None
    discouraged: bool | None = None
    viewed: bool | None = None
    hidden: bool | None = None


@dataclass
class ItemFilterCriteria:
    item_ids: set[UUID] | None = None
    subscription_ids: list[UUID] | None = None
    published_after: datetime | None = None
    updated_before: datetime | None = None
    created_before: datetime | None = None
    url: AnyUrl | None = None
    last_version: int | None = None
    provider: ItemProvider | None = None
    text: str | None = None
    interactions_from_user: UUID | None = None
    min_duration: int | None = None
    max_duration: int | None = None
    interactions: AnyItemInteraction = AnyItemInteraction()


@dataclass
class InteractionFilterCriteria:
    item_ids: list[UUID] | None = None
    user_ids: list[UUID] | None = None
    interaction_types: list[InteractionType] | None = None
    created_before: datetime | None = None
    text: str | None = None
    min_duration: int | None = None
    max_duration: int | None = None


class ItemRepository(abc.ABC):
    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    async def upsert_items(self, items: list[Item]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_item(self, item_id: UUID) -> Item | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_item(self, item_id: UUID) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def find_items(self, criteria: ItemFilterCriteria, page_number: int, limit: int) -> list[Item]:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_all_items(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def add_interaction(self, interaction: Interaction) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_interaction(self, interaction_id: UUID) -> Interaction | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_interaction(self, interaction_id: UUID) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_all_interactions(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_user_interactions_by_item_id(
            self, user_id: UUID, item_ids: list[UUID],
    ) -> dict[UUID, list[Interaction]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def find_interactions(
            self, criteria: InteractionFilterCriteria, page_number: int, limit: int,
    ) -> list[Interaction]:
        raise NotImplementedError
