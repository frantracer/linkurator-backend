from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError
from linkurator_core.domain.items.item_repository import ItemFilterCriteria, ItemRepository
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.user_repository import UserRepository


class DeleteSubscriptionItemsHandler:
    def __init__(self, user_repository: UserRepository, subscription_repository: SubscriptionRepository,
                 item_repository: ItemRepository) -> None:
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository

    async def handle(self, user_id: UUID, subscription_id: UUID) -> None:
        user = await self.user_repository.get(user_id)
        if user is None or user.is_admin is False:
            msg = "Only admins can delete subscription items"
            raise PermissionError(msg)

        subscription = await self.subscription_repository.get(subscription_id)
        if subscription is None:
            raise SubscriptionNotFoundError(subscription_id)

        items_uuids: list[UUID] = []
        page_number = 0

        while True:
            items = await self.item_repository.find_items(
                criteria=ItemFilterCriteria(subscription_ids=[subscription_id]),
                page_number=page_number,
                limit=100)
            if len(items) == 0:
                break
            items_uuids.extend([item.uuid for item in items])

        for item_uuid in items_uuids:
            await self.item_repository.delete_item(item_uuid)

        subscription.scanned_at = datetime.fromtimestamp(0, tz=timezone.utc)
        await self.subscription_repository.update(subscription)

        logging.info("Deleted items of subscription %s - %s", subscription_id, subscription.name)
