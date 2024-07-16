from datetime import timezone, datetime
from typing import Optional, List
from uuid import UUID

from linkurator_core.domain.common.exceptions import TopicNotFoundError, SubscriptionNotFoundError
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.topics.topic_repository import TopicRepository


class UpdateTopicHandler:
    topic_repository: TopicRepository
    subscription_repository: SubscriptionRepository

    def __init__(self, topic_repository: TopicRepository, subscription_repository: SubscriptionRepository) -> None:
        self.topic_repository = topic_repository
        self.subscription_repository = subscription_repository

    async def handle(self, topic_id: UUID, name: Optional[str], subscriptions_ids: Optional[List[UUID]]) -> None:
        topic = self.topic_repository.get(topic_id)
        if topic is None:
            raise TopicNotFoundError()

        now = datetime.now(tz=timezone.utc)

        if name is not None:
            topic.name = name
            topic.updated_at = now

        if subscriptions_ids is not None:
            for subscription_id in subscriptions_ids:
                subscription = self.subscription_repository.get(subscription_id)
                if subscription is None:
                    raise SubscriptionNotFoundError()
            topic.subscriptions_ids = subscriptions_ids
            topic.updated_at = now

        self.topic_repository.update(topic)
