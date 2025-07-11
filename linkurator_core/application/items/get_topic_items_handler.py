from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from linkurator_core.domain.common.exceptions import TopicNotFoundError
from linkurator_core.domain.items.interaction import Interaction
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import AnyItemInteraction, ItemFilterCriteria, ItemRepository
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.topics.topic_repository import TopicRepository


@dataclass
class ItemWithInteractionsAndSubscription:
    item: Item
    interactions: list[Interaction]
    subscription: Subscription


class GetTopicItemsHandler:
    def __init__(self,
                 topic_repository: TopicRepository,
                 subscription_repository: SubscriptionRepository,
                 item_repository: ItemRepository) -> None:
        self.item_repository = item_repository
        self.subscription_repository = subscription_repository
        self.topic_repository = topic_repository

    async def handle(
            self,
            user_id: UUID | None,
            topic_id: UUID,
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
            excluded_subscriptions: set[UUID] | None = None,
    ) -> list[ItemWithInteractionsAndSubscription]:
        topic = await self.topic_repository.get(topic_id)
        if topic is None:
            raise TopicNotFoundError(topic_id)

        subscriptions_ids = set(topic.subscriptions_ids) - (excluded_subscriptions or set())

        filter_criteria = ItemFilterCriteria(
            subscription_ids=list(subscriptions_ids),
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
        )

        results = await asyncio.gather(
            self.subscription_repository.get_list(topic.subscriptions_ids),
            self.item_repository.find_items(
                criteria=filter_criteria,
                page_number=page_number,
                limit=page_size,
            ),
        )

        subscriptions = results[0]
        items = results[1]

        subscriptions_indexed_by_id = {sub.uuid: sub for sub in subscriptions}

        interactions_by_item: dict[UUID, list[Interaction]] = {}
        if user_id is not None:
            interactions_by_item = await self.item_repository.get_user_interactions_by_item_id(
                user_id=user_id, item_ids=[item.uuid for item in items])

        return [
            ItemWithInteractionsAndSubscription(
                item=item,
                interactions=interactions_by_item.get(item.uuid, []),
                subscription=subscriptions_indexed_by_id[item.subscription_uuid],
            ) for item in items
        ]
