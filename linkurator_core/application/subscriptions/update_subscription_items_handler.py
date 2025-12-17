from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import ItemFilterCriteria, ItemRepository
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService


class UpdateSubscriptionItemsHandler:
    subscription_service: SubscriptionService
    subscription_repository: SubscriptionRepository
    item_repository: ItemRepository
    subscriptions_being_updated: dict[uuid.UUID, datetime] = {}

    def __init__(self,
                 subscription_service: SubscriptionService,
                 subscription_repository: SubscriptionRepository,
                 item_repository: ItemRepository,
    ) -> None:
        self.subscription_service = subscription_service
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository

    async def handle(self, subscription_id: uuid.UUID) -> None:
        now = datetime.now(tz=timezone.utc)
        if subscription_id in self.subscriptions_being_updated:
            logging.info("Skipping update of subscription %s because it was scheduled on %s",
                         subscription_id, self.subscriptions_being_updated[subscription_id])
            return
        self.subscriptions_being_updated[subscription_id] = now

        subscription = await self.subscription_repository.get(subscription_id)
        if subscription is None:
            logging.error("Cannot update items of subscription %s because it does not exist", subscription_id)
            return
        logging.info("Updating items for subscription %s - %s", subscription_id, subscription.name)

        try:
            new_items = await self.subscription_service.get_subscription_items(
                sub_id=subscription_id,
                from_date=subscription.last_published_at)
            item_count = 0
            new_filtered_items: list[Item] = []
            for new_item in new_items:
                if item_count % 100 == 0:
                    logging.debug("%s items processed", item_count)
                item_count += 1

                existing_items = await self.item_repository.find_items(
                    criteria=ItemFilterCriteria(
                        subscription_ids=[subscription_id],
                        url=new_item.url,
                    ),
                    page_number=0, limit=1)

                if len(existing_items) == 0:
                    new_filtered_items.append(new_item)

            await self.item_repository.upsert_items(new_filtered_items)

            subscription.scanned_at = now
            if len(new_items) > 0:
                subscription.last_published_at = max(i.published_at for i in new_items)
            await self.subscription_repository.update(subscription)

            logging.info("Updated %s items of subscription %s - %s",
                         len(new_filtered_items), subscription.uuid, subscription.name)
        except Exception as err:  # pylint: disable=broad-except
            logging.error("Cannot update items of subscription %s because %s", subscription_id, err, exc_info=True)
        finally:
            self.subscriptions_being_updated.pop(subscription_id, None)
