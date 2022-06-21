from datetime import datetime
from typing import List, Tuple
from uuid import UUID

from linkurator_core.domain.item import Item
from linkurator_core.domain.item_repository import ItemRepository


class GetSubscriptionItemsHandler:
    def __init__(self, item_repository: ItemRepository):
        self.item_repository = item_repository

    def handle(self,
               subscription_id: UUID,
               created_before: datetime,
               page_number: int,
               page_size: int
               ) -> Tuple[List[Item], int]:
        return self.item_repository.find_sorted_by_publish_date(
            sub_ids=[subscription_id],
            published_after=datetime.fromtimestamp(0),
            created_before=created_before,
            max_results=page_size,
            page_number=page_number
        )
