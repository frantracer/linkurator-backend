from datetime import datetime, timezone
from typing import List, Tuple
from uuid import UUID

from linkurator_core.application.exceptions import TopicNotFoundError
from linkurator_core.domain.item import Item
from linkurator_core.domain.item_repository import ItemRepository
from linkurator_core.domain.topic_repository import TopicRepository


class GetTopicItemsHandler:
    def __init__(self, topic_repository: TopicRepository, item_repository: ItemRepository):
        self.item_repository = item_repository
        self.topic_repository = topic_repository

    def handle(self,
               topic_id: UUID,
               created_before: datetime,
               page_number: int,
               page_size: int
               ) -> Tuple[List[Item], int]:
        topic = self.topic_repository.get(topic_id)
        if topic is None:
            raise TopicNotFoundError(topic_id)

        return self.item_repository.find_sorted_by_publish_date(
            sub_ids=topic.subscriptions_ids,
            created_before=created_before,
            published_after=datetime.fromtimestamp(0, tz=timezone.utc),
            page_number=page_number,
            max_results=page_size
        )
