import logging
import uuid
from datetime import datetime, timezone
from typing import List

from linkurator_core.application.subscription_service import SubscriptionService
from linkurator_core.domain.item import Item
from linkurator_core.domain.item_repository import ItemRepository
from linkurator_core.domain.subscription_repository import SubscriptionRepository


class UpdateSubscriptionItemsHandler:
    subscription_service: SubscriptionService
    subscription_repository: SubscriptionRepository
    item_repository: ItemRepository

    def __init__(self, subscription_service: SubscriptionService,
                 subscription_repository: SubscriptionRepository,
                 item_repository: ItemRepository):
        self.subscription_service = subscription_service
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository

    async def handle(self, subscription_id: uuid.UUID) -> None:
        subscription = self.subscription_repository.get(subscription_id)
        if subscription is None:
            logging.error("Cannot update items of subscription %s because it does not exist", subscription_id)
            return

        logging.info("Updating items for subscription %s - %s", subscription_id, subscription.name)

        now = datetime.now(tz=timezone.utc)

        try:
            new_items = await self.subscription_service.get_items(
                sub_id=subscription_id,
                from_date=subscription.scanned_at)
            item_count = 0
            new_filtered_items: List[Item] = []
            for item in new_items:
                if item_count % 100 == 0:
                    logging.debug("%s items processed", item_count)
                item_count += 1

                found_item = self.item_repository.find(item)
                if found_item is None:
                    new_filtered_items.append(item)

            self.item_repository.add_bulk(new_filtered_items)

            subscription.scanned_at = now
            self.subscription_repository.update(subscription)

            logging.info("Updated %s items of subscription %s - %s",
                         len(new_filtered_items), subscription.uuid, subscription.name)
        except Exception as err:  # pylint: disable=broad-except
            logging.error("Cannot update items of subscription %s because %s", subscription_id, err)
