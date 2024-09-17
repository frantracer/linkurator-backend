from uuid import UUID

from linkurator_core.domain.common.exceptions import TopicNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository


class GetTopicHandler:
    def __init__(self, topic_repository: TopicRepository) -> None:
        self.topic_repository = topic_repository

    async def handle(self, topic_id: UUID) -> Topic:
        topic = await self.topic_repository.get(topic_id)
        if topic is None:
            raise TopicNotFoundError(topic_id)

        return topic
