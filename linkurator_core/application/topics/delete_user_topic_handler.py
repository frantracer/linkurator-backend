from uuid import UUID

from linkurator_core.domain.common.exceptions import TopicNotFoundError
from linkurator_core.domain.topics.topic_repository import TopicRepository


class DeleteUserTopicHandler:
    def __init__(self, topic_repository: TopicRepository):
        self.topic_repository = topic_repository

    def handle(self, user_id: UUID, topic_id: UUID) -> None:
        topic = self.topic_repository.get(topic_id)
        if topic is None or topic.user_id != user_id:
            raise TopicNotFoundError(topic_id)
        self.topic_repository.delete(topic_id)
