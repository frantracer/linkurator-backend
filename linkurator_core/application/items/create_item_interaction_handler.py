from linkurator_core.domain.common.exceptions import ItemNotFoundError
from linkurator_core.domain.items.interaction import Interaction
from linkurator_core.domain.items.item_repository import ItemRepository


class CreateItemInteractionHandler:
    item_repository: ItemRepository

    def __init__(self, item_repository: ItemRepository) -> None:
        self.item_repository = item_repository

    def handle(self, new_interaction: Interaction) -> None:
        if self.item_repository.get_item(new_interaction.item_uuid) is None:
            raise ItemNotFoundError(f"Item with id '{new_interaction.item_uuid}' not found")

        current_interactions = self.item_repository.get_user_interactions_by_item_id(
            user_id=new_interaction.user_uuid, item_ids=[new_interaction.item_uuid])

        current_item_interactions = current_interactions.get(new_interaction.item_uuid, [])
        if new_interaction.type not in [interaction.type for interaction in current_item_interactions]:
            self.item_repository.add_interaction(new_interaction)
