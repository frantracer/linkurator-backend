from datetime import datetime, timezone
from typing import List, Tuple, Optional
from uuid import UUID

from linkurator_core.domain.items.interaction import Interaction
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import ItemRepository, ItemFilterCriteria, AnyItemInteraction


class GetSubscriptionItemsHandler:
    def __init__(self, item_repository: ItemRepository) -> None:
        self.item_repository = item_repository

    async def handle(
            self,
            user_id: Optional[UUID],
            subscription_id: UUID,
            created_before: datetime,
            page_number: int,
            page_size: int,
            text_filter: Optional[str] = None,
            min_duration: Optional[int] = None,
            max_duration: Optional[int] = None,
            include_items_without_interactions: bool = True,
            include_recommended_items: bool = True,
            include_discouraged_items: bool = True,
            include_viewed_items: bool = True,
            include_hidden_items: bool = True,
    ) -> List[Tuple[Item, List[Interaction]]]:
        items = self.item_repository.find_items(
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
                    hidden=include_hidden_items
                ),
            ),
            page_number=page_number,
            limit=page_size
        )

        interactions_by_item: dict[UUID, List[Interaction]] = {}
        if user_id:
            interactions_by_item = self.item_repository.get_user_interactions_by_item_id(
                user_id=user_id,
                item_ids=[item.uuid for item in items]
            )

        return [(item, interactions_by_item.get(item.uuid, [])) for item in items]
