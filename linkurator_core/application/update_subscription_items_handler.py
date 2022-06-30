from datetime import datetime, timezone
import uuid

from linkurator_core.application.subscription_service import SubscriptionService
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
            print(f"Cannot update items of subscription {subscription_id} because it does not exist")
            return

        now = datetime.now(tz=timezone.utc)

        new_items = await self.subscription_service.get_items(
            sub_id=subscription_id,
            from_date=subscription.scanned_at)
        for item in new_items:
            found_item = self.item_repository.find(item)
            if found_item is None:
                self.item_repository.add(item)

        subscription.scanned_at = now
        self.subscription_repository.update(subscription)

        print(f"Updated items of subscription {subscription_id}")
