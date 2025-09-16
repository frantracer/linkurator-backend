from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from linkurator_core.domain.common.exceptions import ItemNotFoundError, SubscriptionNotFoundError
from linkurator_core.domain.items.interaction import Interaction
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import ItemRepository
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository


@dataclass
class GetItemResponse:
    item: Item
    interactions: list[Interaction]
    subscription: Subscription


class GetItemHandler:
    def __init__(self, item_repository: ItemRepository, subscription_repository: SubscriptionRepository) -> None:
        self.item_repository = item_repository
        self.subscription_repository = subscription_repository

    async def handle(self, user_id: UUID | None, item_id: UUID) -> GetItemResponse:
        item = await self.item_repository.get_item(item_id)
        if item is None:
            raise ItemNotFoundError(item_id)

        subscription = await self.subscription_repository.get(item.subscription_uuid)
        if subscription is None:
            raise SubscriptionNotFoundError(item.subscription_uuid)

        interactions: dict[UUID, list[Interaction]] = {}
        if user_id is not None:
            interactions = await self.item_repository.get_user_interactions_by_item_id(user_id, [item_id])
        return GetItemResponse(item=item, interactions=interactions.get(item_id, []), subscription=subscription)
