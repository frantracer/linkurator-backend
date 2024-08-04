from uuid import UUID

from linkurator_core.domain.items.interaction import InteractionType
from linkurator_core.domain.items.item_repository import ItemRepository


class DeleteItemInteractionHandler:
    item_repository: ItemRepository

    def __init__(self, item_repository: ItemRepository) -> None:
        self.item_repository = item_repository

    async def handle(self, user_id: UUID, item_id: UUID, interaction_type: InteractionType) -> None:
        current_interactions = await self.item_repository.get_user_interactions_by_item_id(
            user_id=user_id, item_ids=[item_id])

        current_item_interactions = current_interactions.get(item_id, [])
        for interaction in current_item_interactions:
            if interaction.type == interaction_type:
                await self.item_repository.delete_interaction(interaction.uuid)
