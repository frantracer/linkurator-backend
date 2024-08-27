from typing import List, Optional
from uuid import UUID

from linkurator_core.domain.common.exceptions import DuplicatedKeyError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository


class InMemoryTopicRepository(TopicRepository):
    def __init__(self) -> None:
        super().__init__()
        self.topics: dict[UUID, Topic] = {}

    async def add(self, topic: Topic) -> None:
        if topic.uuid in self.topics:
            raise DuplicatedKeyError(f"Topic with id {topic.uuid} already exists")
        self.topics[topic.uuid] = topic

    async def get(self, topic_id: UUID) -> Optional[Topic]:
        return self.topics.get(topic_id)

    async def find_topics(self, topic_ids: List[UUID]) -> List[Topic]:
        return [topic for topic in self.topics.values() if topic.uuid in topic_ids]

    async def update(self, topic: Topic) -> None:
        self.topics[topic.uuid] = topic

    async def delete(self, topic_id: UUID) -> None:
        if topic_id in self.topics:
            del self.topics[topic_id]

    async def get_by_user_id(self, user_id: UUID) -> List[Topic]:
        return [topic for topic in self.topics.values() if topic.user_id == user_id]
