from __future__ import annotations

from uuid import UUID

from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import InteractionFilterCriteria, ItemFilterCriteria, ItemRepository


def _item_contains_text(text: str, item: Item) -> bool:
    text_inputs = text.lower().strip('"').strip("'").split()
    item_text = item.name.lower()
    return all(text_input in item_text for text_input in text_inputs)


class InMemoryItemRepository(ItemRepository):
    def __init__(self) -> None:
        super().__init__()
        self.items: dict[UUID, Item] = {}
        self.interactions: dict[UUID, Interaction] = {}

    async def upsert_items(self, items: list[Item]) -> None:
        for item in items:
            self.items[item.uuid] = item

    async def get_item(self, item_id: UUID) -> Item | None:
        return self.items.get(item_id)

    async def delete_item(self, item_id: UUID) -> None:
        if item_id in self.items:
            del self.items[item_id]

    async def find_items(  # pylint: disable=too-many-branches
            self,
            criteria: ItemFilterCriteria,
            page_number: int,
            limit: int,
    ) -> list[Item]:
        found_items = []
        for item in self.items.values():
            if item.deleted_at is not None:
                continue
            if criteria.item_ids is not None and item.uuid not in criteria.item_ids:
                continue
            if criteria.subscription_ids is not None and item.subscription_uuid not in criteria.subscription_ids:
                continue
            if criteria.published_after and criteria.published_after >= item.published_at:
                continue
            if criteria.updated_before and criteria.updated_before <= item.updated_at:
                continue
            if criteria.created_before and criteria.created_before <= item.created_at:
                continue
            if criteria.url and criteria.url != item.url:
                continue
            if criteria.last_version and item.version >= criteria.last_version:
                continue
            if criteria.provider and item.provider != criteria.provider:
                continue
            if criteria.text is not None and not _item_contains_text(criteria.text, item):
                continue
            if item.duration is None and not (criteria.min_duration is None and criteria.max_duration is None):
                continue
            if item.duration is not None:
                if criteria.min_duration is not None and item.duration < criteria.min_duration:
                    continue
                if criteria.max_duration is not None and item.duration > criteria.max_duration:
                    continue

            if criteria.interactions_from_user is not None:
                is_filtered = True
                interactions = await self.get_user_interactions_by_item_id(criteria.interactions_from_user, [item.uuid])
                interactions_types = [interaction.type for interaction in interactions[item.uuid]]
                if criteria.interactions.without_interactions and len(interactions[item.uuid]) == 0:
                    is_filtered = False
                if criteria.interactions.hidden and InteractionType.HIDDEN in interactions_types:
                    is_filtered = False
                if criteria.interactions.viewed and InteractionType.VIEWED in interactions_types:
                    is_filtered = False
                if criteria.interactions.recommended and InteractionType.RECOMMENDED in interactions_types:
                    is_filtered = False
                if criteria.interactions.discouraged and InteractionType.DISCOURAGED in interactions_types:
                    is_filtered = False

                if is_filtered:
                    continue

            found_items.append(item)

        sorted_items = sorted(found_items, key=lambda found_item: found_item.published_at, reverse=True)
        return sorted_items[page_number * limit: (page_number + 1) * limit]

    async def delete_all_items(self) -> None:
        self.items.clear()

    async def add_interaction(self, interaction: Interaction) -> None:
        self.interactions[interaction.uuid] = interaction

    async def get_interaction(self, interaction_id: UUID) -> Interaction | None:
        return self.interactions.get(interaction_id)

    async def delete_interaction(self, interaction_id: UUID) -> None:
        if interaction_id in self.interactions:
            del self.interactions[interaction_id]

    async def delete_all_interactions(self) -> None:
        self.interactions.clear()

    async def get_user_interactions_by_item_id(
            self, user_id: UUID, item_ids: list[UUID],
    ) -> dict[UUID, list[Interaction]]:
        interactions: dict[UUID, list[Interaction]] = {item_id: [] for item_id in item_ids}
        for interaction in self.interactions.values():
            if interaction.user_uuid == user_id and interaction.item_uuid in item_ids:
                interactions[interaction.item_uuid].append(interaction)
        return interactions

    async def find_interactions(
            self, criteria: InteractionFilterCriteria, page_number: int, limit: int,
    ) -> list[Interaction]:
        found_interactions: list[Interaction] = []
        for interaction in self.interactions.values():
            if criteria.item_ids is not None and interaction.item_uuid not in criteria.item_ids:
                continue
            if criteria.user_ids is not None and interaction.user_uuid not in criteria.user_ids:
                continue
            if criteria.interaction_types is not None and interaction.type not in criteria.interaction_types:
                continue
            if criteria.created_before and criteria.created_before <= interaction.created_at:
                continue

            item = self.items.get(interaction.item_uuid)
            if item is not None:
                if criteria.text is not None and criteria.text.lower() not in item.name.lower():
                    continue
                if item.duration is not None:
                    if criteria.min_duration is not None and item.duration < criteria.min_duration:
                        continue
                    if criteria.max_duration is not None and item.duration > criteria.max_duration:
                        continue

            found_interactions.append(interaction)

        sorted_interactions = sorted(
            found_interactions,
            key=lambda found_interaction: found_interaction.created_at,
            reverse=True)

        return sorted_interactions[page_number * limit: (page_number + 1) * limit]
