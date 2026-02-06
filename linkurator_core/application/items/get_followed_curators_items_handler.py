from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item_repository import InteractionFilterCriteria, ItemFilterCriteria, ItemRepository
from linkurator_core.domain.items.item_with_interactions import ItemWithInteractions
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


class GetFollowedCuratorsItemsHandler:
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
    ) -> list[ItemWithInteractions]:
        user = await self.user_repository.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        if len(user.curators) == 0:
            return []

        curator_ids = list(user.curators)

        curators_items_interactions = await self.item_repository.find_interactions(
            criteria=InteractionFilterCriteria(
                user_ids=curator_ids,
                created_before=created_before,
                interaction_types=[InteractionType.RECOMMENDED],
                text=text_filter,
                min_duration=min_duration,
                max_duration=max_duration,
            ),
            page_number=page_number,
            limit=page_size,
        )

        if len(curators_items_interactions) == 0:
            return []

        items_ids = {interaction.item_uuid for interaction in curators_items_interactions}

        async def get_curators() -> list[User]:
            curator_results = await asyncio.gather(*[self.user_repository.get(cid) for cid in curator_ids])
            return [c for c in curator_results if c is not None]

        results = await asyncio.gather(
            self.item_repository.find_items(
                criteria=ItemFilterCriteria(item_ids=items_ids),
                page_number=0,
                limit=len(items_ids),
            ),
            self.item_repository.get_user_interactions_by_item_id(
                user_id=user_id,
                item_ids=list(items_ids),
            ),
            get_curators(),
        )
        curators_items = results[0]
        user_items_interactions = results[1]
        curators = results[2]

        subscriptions_ids = {item.subscription_uuid for item in curators_items}
        subscriptions = await self.subscription_repository.get_list(list(subscriptions_ids))

        subscriptions_index = {sub.uuid: sub for sub in subscriptions}
        curators_items_index = {item.uuid: item for item in curators_items}
        curators_index = {curator.uuid: curator for curator in curators}
        curators_items_interactions_index: dict[UUID, list[Interaction]] = {}
        for interaction in curators_items_interactions:
            if interaction.item_uuid not in curators_items_interactions_index:
                curators_items_interactions_index[interaction.item_uuid] = []
            curators_items_interactions_index[interaction.item_uuid].append(interaction)

        return [
            ItemWithInteractions(
                item=curators_items_index[interaction.item_uuid],
                subscription=subscriptions_index[curators_items_index[interaction.item_uuid].subscription_uuid],
                interactions=user_items_interactions.get(interaction.item_uuid, []),
                curator_interactions=curators_items_interactions_index.get(interaction.item_uuid, []),
                curator=curators_index.get(interaction.user_uuid),
            )
            for interaction in curators_items_interactions
            if interaction.item_uuid in curators_items_index
        ]
