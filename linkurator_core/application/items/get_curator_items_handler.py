from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID

from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item_repository import InteractionFilterCriteria, ItemFilterCriteria, ItemRepository
from linkurator_core.domain.items.item_with_interactions import CuratorInteractions, ItemWithInteractions
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.user_repository import UserRepository


class GetCuratorItemsHandler:
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
            created_before: datetime,
            page_number: int,
            page_size: int,
            curator_id: UUID,
            user_id: UUID | None = None,
            text_filter: str | None = None,
            min_duration: int | None = None,
            max_duration: int | None = None,
    ) -> list[ItemWithInteractions]:
        curator_items_interactions = await self.item_repository.find_interactions(
            criteria=InteractionFilterCriteria(
                user_ids=[curator_id],
                created_before=created_before,
                interaction_types=[InteractionType.RECOMMENDED],
                text=text_filter,
                min_duration=min_duration,
                max_duration=max_duration,
            ),
            page_number=page_number,
            limit=page_size,
        )

        items_ids = {interaction.item_uuid for interaction in curator_items_interactions}

        async def get_user_interactions_if_user_id_provided() -> dict[UUID, list[Interaction]]:
            if user_id is not None:
                return await self.item_repository.get_user_interactions_by_item_id(
                    user_id=user_id,
                    item_ids=list(items_ids),
                )
            return {}

        results = await asyncio.gather(
            self.item_repository.find_items(
                criteria=ItemFilterCriteria(
                    item_ids=items_ids,
                ),
                page_number=0,
                limit=len(items_ids),
            ),
            get_user_interactions_if_user_id_provided(),
            self.user_repository.get(user_id) if user_id is not None else asyncio.sleep(0, result=None),
        )
        curator_items = results[0]
        user_items_interactions = results[1]
        user = results[2]

        subscriptions_ids = {item.subscription_uuid for item in curator_items}
        subscriptions = await self.subscription_repository.get_list(list(subscriptions_ids))
        subscriptions_index = {sub.uuid: sub for sub in subscriptions}

        curator_items_index = {item.uuid: item for item in curator_items}

        curator_index = {}
        if user is not None:
            for followed_curator_id in user.curators:
                followed_curator = await self.user_repository.get(followed_curator_id)
                if followed_curator is not None:
                    curator_index[followed_curator_id] = followed_curator

        curator_interactions_by_item: dict[UUID, list[CuratorInteractions]] = {}
        for curator in curator_index.values():
            interactions_by_item = await self.item_repository.get_user_interactions_by_item_id(
                user_id=curator.uuid,
                item_ids=list(items_ids),
            )
            for item_id, interactions in interactions_by_item.items():
                if item_id not in curator_interactions_by_item:
                    curator_interactions_by_item[item_id] = []
                curator_interactions_by_item[item_id].append(
                    CuratorInteractions(curator=curator, interactions=interactions),
                )

        return [
            ItemWithInteractions(
                item=curator_items_index[interaction.item_uuid],
                subscription=subscriptions_index[curator_items_index[interaction.item_uuid].subscription_uuid],
                interactions=user_items_interactions.get(interaction.item_uuid, []),
                curator_interactions=curator_interactions_by_item.get(interaction.item_uuid, []),
            )
            for interaction in curator_items_interactions
            if interaction.item_uuid in curator_items_index
        ]
