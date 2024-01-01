from uuid import UUID

from linkurator_core.domain.items.interaction import InteractionType
from linkurator_core.domain.items.interaction_repository import InteractionRepository


class DeleteItemInteractionHandler:
    interaction_repository: InteractionRepository

    def __init__(self, interaction_repository: InteractionRepository) -> None:
        self.interaction_repository = interaction_repository

    def handle(self, user_id: UUID, item_id: UUID, interaction_type: InteractionType) -> None:
        current_interactions = self.interaction_repository.get_user_interactions_by_item_id(
            user_id=user_id, item_ids=[item_id])

        current_item_interactions = current_interactions.get(item_id, [])
        for interaction in current_item_interactions:
            if interaction.type == interaction_type:
                self.interaction_repository.delete(interaction.uuid)
