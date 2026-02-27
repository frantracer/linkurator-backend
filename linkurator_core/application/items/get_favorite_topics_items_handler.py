from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from linkurator_core.domain.items.item_repository import AnyItemInteraction, ItemFilterCriteria, ItemRepository
from linkurator_core.domain.items.item_with_interactions import CuratorInteractions, ItemWithInteractions
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


class GetFavoriteTopicsItemsHandler:
    def __init__(self,
                 topic_repository: TopicRepository,
                 subscription_repository: SubscriptionRepository,
                 item_repository: ItemRepository,
                 user_repository: UserRepository) -> None:
        self.item_repository = item_repository
        self.subscription_repository = subscription_repository
        self.topic_repository = topic_repository
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
            excluded_subscriptions: set[UUID] | None = None,
    ) -> list[ItemWithInteractions]:
        user = await self.user_repository.get(user_id)
        if user is None:
            return []

        favorite_topic_ids = user.get_favorite_topics()
        if not favorite_topic_ids:
            return []

        topics = await asyncio.gather(*[self.topic_repository.get(topic_id) for topic_id in favorite_topic_ids])

        all_subscription_ids: set[UUID] = set()
        for topic in topics:
            if topic is not None:
                all_subscription_ids.update(topic.subscriptions_ids)

        filtered_subscription_ids = all_subscription_ids - (excluded_subscriptions or set())
        if not filtered_subscription_ids:
            return []

        filter_criteria = ItemFilterCriteria(
            subscription_ids=list(filtered_subscription_ids),
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
            self.subscription_repository.get_list(list(all_subscription_ids)),
            self.item_repository.find_items(
                criteria=filter_criteria,
                page_number=page_number,
                limit=page_size,
            ),
        )

        subscriptions = results[0]
        items = results[1]

        subscriptions_indexed_by_id = {sub.uuid: sub for sub in subscriptions}

        interactions_by_item = await self.item_repository.get_user_interactions_by_item_id(
            user_id=user_id, item_ids=[item.uuid for item in items])

        curator_index = {}
        for curator_id in user.curators:
            curator = await self.user_repository.get(curator_id)
            if curator is not None:
                curator_index[curator_id] = curator

        curator_interactions_by_item: dict[UUID, list[CuratorInteractions]] = {}
        for curator in curator_index.values():
            interactions_by_curator_item = await self.item_repository.get_user_interactions_by_item_id(
                user_id=curator.uuid,
                item_ids=[item.uuid for item in items],
            )
            for item_id, interactions in interactions_by_curator_item.items():
                if item_id not in curator_interactions_by_item:
                    curator_interactions_by_item[item_id] = []
                curator_interactions_by_item[item_id].append(
                    CuratorInteractions(curator=curator, interactions=interactions),
                )

        return [
            ItemWithInteractions(
                item=item,
                subscription=subscriptions_indexed_by_id[item.subscription_uuid],
                interactions=interactions_by_item.get(item.uuid, []),
                curator_interactions=curator_interactions_by_item.get(item.uuid, []),
            ) for item in items
        ]
