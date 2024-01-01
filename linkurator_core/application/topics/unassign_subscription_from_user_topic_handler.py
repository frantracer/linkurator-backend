from uuid import UUID

from linkurator_core.domain.common.exceptions import TopicNotFoundError
from linkurator_core.domain.topics.topic_repository import TopicRepository


class UnassignSubscriptionFromUserTopicHandler:
    def __init__(self, topic_repository: TopicRepository) -> None:
        self.topic_repository = topic_repository

    def handle(self, user_id: UUID, subscription_id: UUID, topic_id: UUID) -> None:
        topic = self.topic_repository.get(topic_id)
        if topic is None or topic.user_id != user_id:
            raise TopicNotFoundError(topic_id)
        topic.remove_subscription(subscription_id)
        self.topic_repository.update(topic)
