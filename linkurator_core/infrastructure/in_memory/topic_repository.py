from __future__ import annotations

from uuid import UUID

from unidecode import unidecode

from linkurator_core.domain.common.exceptions import DuplicatedKeyError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository


class InMemoryTopicRepository(TopicRepository):
    def __init__(self) -> None:
        super().__init__()
        self.topics: dict[UUID, Topic] = {}

    async def add(self, topic: Topic) -> None:
        if topic.uuid in self.topics:
            msg = f"Topic with id {topic.uuid} already exists"
            raise DuplicatedKeyError(msg)
        self.topics[topic.uuid] = topic

    async def get(self, topic_id: UUID) -> Topic | None:
        return self.topics.get(topic_id)

    async def find_topics(self, topic_ids: list[UUID]) -> list[Topic]:
        return [topic for topic in self.topics.values() if topic.uuid in topic_ids]

    async def find_topics_by_name(self, name: str) -> list[Topic]:
        search_terms = unidecode(name.lower()).split(" ")

        def search_terms_in_name(terms: list[str], topic_name: str) -> bool:
            return all(term in topic_name for term in terms)

        return [topic for topic in self.topics.values()
                if search_terms_in_name(search_terms, unidecode(topic.name.lower()))]

    async def update(self, topic: Topic) -> None:
        self.topics[topic.uuid] = topic

    async def delete(self, topic_id: UUID) -> None:
        if topic_id in self.topics:
            del self.topics[topic_id]

    async def delete_all(self) -> None:
        self.topics.clear()

    async def get_by_user_id(self, user_id: UUID) -> list[Topic]:
        return [topic for topic in self.topics.values() if topic.user_id == user_id]
