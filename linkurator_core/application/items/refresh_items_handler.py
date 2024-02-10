import logging
from uuid import UUID

from linkurator_core.domain.items.item_repository import ItemRepository, ItemFilterCriteria
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService


class RefreshItemsHandler:
    def __init__(self, item_repository: ItemRepository, subscription_service: SubscriptionService) -> None:
        self.item_repository = item_repository
        self.subscription_service = subscription_service

    async def handle(self, item_uuids: set[UUID]) -> None:
        logging.info("Refreshing information for %s items", len(item_uuids))

        items = self.item_repository.find_items(criteria=ItemFilterCriteria(item_ids=item_uuids),
                                                page_number=0, limit=len(item_uuids))

        updated_items = await self.subscription_service.get_items(set(item.uuid for item in items))

        self.item_repository.upsert_items(list(updated_items))

        updated_item_uuids = set(item.uuid for item in updated_items)
        for item in items:
            if item.uuid not in updated_item_uuids:
                self.item_repository.delete_item(item.uuid)

        updated_items_count = len(updated_item_uuids)
        deleted_items_count = len(item_uuids) - len(updated_item_uuids)
        logging.info("%s items updated and %s items deleted", updated_items_count, deleted_items_count)
