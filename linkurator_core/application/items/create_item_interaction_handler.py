from linkurator_core.domain.common.exceptions import ItemNotFoundError
from linkurator_core.domain.items.interaction import Interaction
from linkurator_core.domain.items.interaction_repository import InteractionRepository
from linkurator_core.domain.items.item_repository import ItemRepository


class CreateItemInteractionHandler:
    item_repository: ItemRepository
    interaction_repository: InteractionRepository

    def __init__(self, item_repository: ItemRepository, interaction_repository: InteractionRepository) -> None:
        self.item_repository = item_repository
        self.interaction_repository = interaction_repository

    def handle(self, new_interaction: Interaction) -> None:
        if self.item_repository.get(new_interaction.item_uuid) is None:
            raise ItemNotFoundError(f"Item with id '{new_interaction.item_uuid}' not found")

        current_interactions = self.interaction_repository.get_user_interactions_by_item_id(
            user_id=new_interaction.user_uuid, item_ids=[new_interaction.item_uuid])

        current_item_interactions = current_interactions.get(new_interaction.item_uuid, [])
        if new_interaction.type not in [interaction.type for interaction in current_item_interactions]:
            self.interaction_repository.add(new_interaction)
