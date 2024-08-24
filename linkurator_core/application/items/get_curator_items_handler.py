import asyncio
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import ItemRepository, ItemFilterCriteria, InteractionFilterCriteria


@dataclass
class ItemWithInteractions:
    item: Item
    user_interactions: list[Interaction]
    curator_interactions: list[Interaction]


class GetCuratorItemsHandler:
    def __init__(self, item_repository: ItemRepository):
        self.item_repository = item_repository

    async def handle(
            self,
            created_before: datetime,
            page_number: int,
            page_size: int,
            curator_id: UUID,
            user_id: UUID,
            text_filter: str | None = None,
            min_duration: int | None = None,
            max_duration: int | None = None,
    ) -> list[ItemWithInteractions]:
        curator_items_interactions = await self.item_repository.find_interactions(
            criteria=InteractionFilterCriteria(
                user_ids=[curator_id],
                created_before=created_before,
                interaction_types=[InteractionType.RECOMMENDED],
                text=text_filter,
                min_duration=min_duration,
                max_duration=max_duration
            ),
            page_number=page_number,
            limit=page_size
        )

        items_ids = {interaction.item_uuid for interaction in curator_items_interactions}

        results = await asyncio.gather(
            self.item_repository.find_items(
                criteria=ItemFilterCriteria(
                    item_ids=items_ids,
                ),
                page_number=0,
                limit=len(items_ids)
            ),
            self.item_repository.get_user_interactions_by_item_id(
                user_id=user_id,
                item_ids=list(items_ids)
            )
        )
        curator_items = results[0]
        user_items_interactions = results[1]

        curator_items_index = {item.uuid: item for item in curator_items}
        curator_items_interactions_index = {
            interaction.item_uuid: [interaction]
            for interaction in curator_items_interactions
        }

        return [
            ItemWithInteractions(
                item=curator_items_index[interaction.item_uuid],
                user_interactions=user_items_interactions.get(interaction.item_uuid, []),
                curator_interactions=curator_items_interactions_index.get(interaction.item_uuid, [])
            )
            for interaction in curator_items_interactions
        ]
