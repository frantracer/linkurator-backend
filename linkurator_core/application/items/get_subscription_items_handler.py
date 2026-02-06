from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from linkurator_core.domain.items.interaction import Interaction
from linkurator_core.domain.items.item_repository import AnyItemInteraction, ItemFilterCriteria, ItemRepository
from linkurator_core.domain.items.item_with_interactions import CuratorInteractions, ItemWithInteractions
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class GetSubscriptionItemsResponse:
    items: list[ItemWithInteractions]
    subscription: Subscription


class GetSubscriptionItemsHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        item_repository: ItemRepository,
        subscription_repository: SubscriptionRepository,
    ) -> None:
        self.user_repository = user_repository
        self.item_repository = item_repository
        self.subscription_repository = subscription_repository

    async def handle(
        self,
        user_id: UUID | None,
        subscription_id: UUID,
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
    ) -> GetSubscriptionItemsResponse:
        results = await asyncio.gather(
            self.subscription_repository.get(subscription_id),
            self.item_repository.find_items(
                criteria=ItemFilterCriteria(
                    subscription_ids=[subscription_id],
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
            self.user_repository.get(user_id) if user_id else asyncio.sleep(0, result=None),
        )
        subscription = results[0]
        items = results[1]
        user = results[2]

        if subscription is None:
            msg = "Subscription not found"
            raise ValueError(msg)

        user_interactions_by_item: dict[UUID, list[Interaction]] = {}
        if user_id:
            user_interactions_by_item = await self.item_repository.get_user_interactions_by_item_id(
                user_id=user_id,
                item_ids=[item.uuid for item in items],
            )

        curator_index: dict[UUID, User] = {}
        if user is not None:
            for curator_id in user.curators:
                existing_curator = await self.user_repository.get(curator_id)
                if existing_curator is not None:
                    curator_index[curator_id] = existing_curator

        curator_interactions_by_item: dict[UUID, list[CuratorInteractions]] = {}
        for curator in curator_index.values():
            interactions_by_item = await self.item_repository.get_user_interactions_by_item_id(
                user_id=curator.uuid,
                item_ids=[item.uuid for item in items],
            )
            for item_id, interactions in interactions_by_item.items():
                if item_id not in curator_interactions_by_item:
                    curator_interactions_by_item[item_id] = []
                curator_interactions_by_item[item_id].append(
                    CuratorInteractions(curator=curator, interactions=interactions),
                )

        return GetSubscriptionItemsResponse(
            subscription=subscription,
            items=[
                ItemWithInteractions(
                    item=item,
                    subscription=subscription,
                    interactions=user_interactions_by_item.get(item.uuid, []),
                    curator_interactions=curator_interactions_by_item.get(item.uuid, []),
                )
                for item in items
            ],
        )
