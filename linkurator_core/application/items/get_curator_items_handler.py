import asyncio
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import ItemRepository, ItemFilterCriteria, AnyItemInteraction


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
            curator_interactions: list[InteractionType],
            curator_id: UUID,
            user_id: UUID
    ) -> list[ItemWithInteractions]:
        curator_items = await self.item_repository.find_items(
            criteria=ItemFilterCriteria(
                created_before=created_before,
                interactions_from_user=curator_id,
                interactions=AnyItemInteraction(
                    recommended=InteractionType.RECOMMENDED in curator_interactions,
                    discouraged=InteractionType.DISCOURAGED in curator_interactions,
                    viewed=InteractionType.VIEWED in curator_interactions,
                    hidden=InteractionType.HIDDEN in curator_interactions
                )
            ),
            page_number=page_number,
            limit=page_size,
        )

        items_ids = [item.uuid for item in curator_items]
        results = await asyncio.gather(
            self.item_repository.get_user_interactions_by_item_id(
                user_id=user_id,
                item_ids=items_ids
            ),
            self.item_repository.get_user_interactions_by_item_id(
                user_id=curator_id,
                item_ids=items_ids
            )
        )
        user_items_interactions = results[0]
        curator_items_interactions = results[1]

        return [
            ItemWithInteractions(
                item=item,
                user_interactions=user_items_interactions.get(item.uuid, []),
                curator_interactions=curator_items_interactions.get(item.uuid, [])
            )
            for item in curator_items
        ]
