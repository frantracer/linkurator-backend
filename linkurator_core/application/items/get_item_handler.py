from uuid import UUID

from linkurator_core.domain.common.exceptions import ItemNotFoundError
from linkurator_core.domain.items.item_repository import ItemRepository
from linkurator_core.domain.items.item_with_interactions import ItemWithInteractions


class GetItemHandler:
    def __init__(self, item_repository: ItemRepository) -> None:
        self.item_repository = item_repository

    def handle(self, user_id: UUID, item_id: UUID) -> ItemWithInteractions:
        item = self.item_repository.get_item(item_id)
        if item is None:
            raise ItemNotFoundError(item_id)
        interactions = self.item_repository.get_user_interactions_by_item_id(user_id, [item_id])
        return ItemWithInteractions(item, interactions.get(item_id, []))
