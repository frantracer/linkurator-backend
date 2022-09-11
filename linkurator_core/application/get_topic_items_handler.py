from datetime import datetime, timezone
from typing import List, Tuple
from uuid import UUID

from linkurator_core.application.exceptions import TopicNotFoundError
from linkurator_core.domain.interaction import Interaction
from linkurator_core.domain.interaction_repository import InteractionRepository
from linkurator_core.domain.item import Item
from linkurator_core.domain.item_repository import ItemRepository
from linkurator_core.domain.topic_repository import TopicRepository


class GetTopicItemsHandler:
    def __init__(self,
                 topic_repository: TopicRepository,
                 item_repository: ItemRepository,
                 interaction_repository: InteractionRepository):
        self.item_repository = item_repository
        self.topic_repository = topic_repository
        self.interaction_repository = interaction_repository

    def handle(self,
               user_id: UUID,
               topic_id: UUID,
               created_before: datetime,
               page_number: int,
               page_size: int
               ) -> Tuple[List[Tuple[Item, List[Interaction]]], int]:
        topic = self.topic_repository.get(topic_id)
        if topic is None:
            raise TopicNotFoundError(topic_id)

        items, total_items = self.item_repository.find_sorted_by_publish_date(
            sub_ids=topic.subscriptions_ids,
            created_before=created_before,
            published_after=datetime.fromtimestamp(0, tz=timezone.utc),
            page_number=page_number,
            max_results=page_size
        )

        interactions_by_item = self.interaction_repository.get_user_interactions_by_item_id(
            user_id=user_id, item_ids=[item.uuid for item in items])

        return [(item, interactions_by_item.get(item.uuid, [])) for item in items], total_items
