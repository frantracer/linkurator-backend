from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from linkurator_core.domain.items.interaction import Interaction
from linkurator_core.domain.items.item_repository import AnyItemInteraction, ItemFilterCriteria, ItemRepository
from linkurator_core.domain.items.item_with_interactions import ItemWithInteractions
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class GetFollowedSubscriptionsItemsResponse:
    items: list[ItemWithInteractions]


class GetFollowedSubscriptionsItemsHandler:
    def __init__(
        self,
        item_repository: ItemRepository,
        subscription_repository: SubscriptionRepository,
        user_repository: UserRepository,
    ) -> None:
        self.item_repository = item_repository
        self.subscription_repository = subscription_repository
        self.user_repository = user_repository

    async def handle(
        self,
        user_id: UUID,
        created_before: datetime,
        page_number: int,
        page_size: int,
        text_filter: str | None = None,
        min_duration: int | None = None,
        max_duration: int | None = None,
        include_items_without_interactions: bool = True,
        include_recommended_items: bool = True,
        include_discouraged_items: bool = True,
        include_viewed_items: bool = True,
        include_hidden_items: bool = True,
    ) -> GetFollowedSubscriptionsItemsResponse:
        user = await self.user_repository.get(user_id)
        if user is None:
            return GetFollowedSubscriptionsItemsResponse(items=[])

        subscription_ids = list(user.get_subscriptions())
        if not subscription_ids:
            return GetFollowedSubscriptionsItemsResponse(items=[])

        results = await asyncio.gather(
            self.item_repository.find_items(
                criteria=ItemFilterCriteria(
                    subscription_ids=subscription_ids,
                    published_after=datetime.fromtimestamp(0, tz=timezone.utc),
                    created_before=created_before,
                    text=text_filter,
                    interactions_from_user=user_id,
                    min_duration=min_duration,
                    max_duration=max_duration,
                    interactions=AnyItemInteraction(
                        without_interactions=include_items_without_interactions,
                        recommended=include_recommended_items,
                        discouraged=include_discouraged_items,
                        viewed=include_viewed_items,
                        hidden=include_hidden_items,
                    ),
                ),
                page_number=page_number,
                limit=page_size,
            ),
            self.subscription_repository.get_list(subscription_ids),
        )
        items = results[0]
        subscriptions = results[1]

        subscriptions_by_id = {sub.uuid: sub for sub in subscriptions}

        interactions_by_item: dict[UUID, list[Interaction]] = {}
        if items:
            interactions_by_item = await self.item_repository.get_user_interactions_by_item_id(
                user_id=user_id,
                item_ids=[item.uuid for item in items],
            )

        return GetFollowedSubscriptionsItemsResponse(
            items=[
                ItemWithInteractions(
                    item=item,
                    subscription=subscriptions_by_id[item.subscription_uuid],
                    interactions=interactions_by_item.get(item.uuid, []),
                )
                for item in items
                if item.subscription_uuid in subscriptions_by_id
            ],
        )
