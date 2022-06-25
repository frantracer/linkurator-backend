from uuid import UUID

from linkurator_core.application.exceptions import TopicNotFoundError
from linkurator_core.domain.topic import Topic
from linkurator_core.domain.topic_repository import TopicRepository


class GetTopicHandler:
    def __init__(self, topic_repository: TopicRepository):
        self.topic_repository = topic_repository

    def handle(self, topic_id: UUID) -> Topic:
        topic = self.topic_repository.get(topic_id)
        if topic is None:
            raise TopicNotFoundError(topic_id)
        return topic
