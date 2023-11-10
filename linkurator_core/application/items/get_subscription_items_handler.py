from datetime import datetime, timezone
from typing import List, Tuple, Optional
from uuid import UUID

from linkurator_core.domain.items.filter_item_criteria import FilterItemCriteria
from linkurator_core.domain.items.interaction_repository import InteractionRepository
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.interaction import Interaction
from linkurator_core.domain.items.item_repository import ItemRepository


class GetSubscriptionItemsHandler:
    def __init__(self, item_repository: ItemRepository, interaction_repository: InteractionRepository):
        self.item_repository = item_repository
        self.interaction_repository = interaction_repository

    def handle(self,
               user_id: UUID,
               subscription_id: UUID,
               created_before: datetime,
               page_number: int,
               page_size: int,
               text_filter: Optional[str] = None
               ) -> Tuple[List[Tuple[Item, List[Interaction]]], int]:
        items, total_items = self.item_repository.find_sorted_by_publish_date(
            sub_ids=[subscription_id],
            published_after=datetime.fromtimestamp(0, tz=timezone.utc),
            created_before=created_before,
            max_results=page_size,
            page_number=page_number,
            criteria=FilterItemCriteria() if text_filter is None else FilterItemCriteria(text=text_filter)
        )

        interactions_by_item = self.interaction_repository.get_user_interactions_by_item_id(
            user_id=user_id, item_ids=[item.uuid for item in items])

        return [(item, interactions_by_item.get(item.uuid, [])) for item in items], total_items
