from datetime import datetime
from uuid import uuid4

from linkurator_core.domain.common.exceptions import ItemNotFoundError
from linkurator_core.domain.common.types import UuidGenerator, DateGenerator
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item_repository import ItemRepository


class CreateItemInteractionHandler:
    item_repository: ItemRepository

    def __init__(
            self,
            item_repository: ItemRepository,
            uuid_generator: UuidGenerator = uuid4,
            date_generator: DateGenerator = datetime.utcnow
    ) -> None:
        self.item_repository = item_repository
        self.uuid_generator = uuid_generator
        self.date_generator = date_generator

    def handle(self, new_interaction: Interaction) -> None:
        if self.item_repository.get_item(new_interaction.item_uuid) is None:
            raise ItemNotFoundError(f"Item with id '{new_interaction.item_uuid}' not found")

        current_interactions = self.item_repository.get_user_interactions_by_item_id(
            user_id=new_interaction.user_uuid, item_ids=[new_interaction.item_uuid])

        current_item_interactions = current_interactions.get(new_interaction.item_uuid, [])
        current_interaction_types = [interaction.type for interaction in current_item_interactions]

        if new_interaction.type in current_interaction_types:
            return

        self.item_repository.add_interaction(new_interaction)

        is_recommendation = new_interaction.type in [InteractionType.DISCOURAGED, InteractionType.RECOMMENDED]
        is_viewed = InteractionType.VIEWED in current_interaction_types
        if is_recommendation and not is_viewed:
            viewed_interaction = Interaction(
                uuid=self.uuid_generator(),
                item_uuid=new_interaction.item_uuid,
                user_uuid=new_interaction.user_uuid,
                type=InteractionType.VIEWED,
                created_at=self.date_generator()
            )
            self.item_repository.add_interaction(viewed_interaction)
