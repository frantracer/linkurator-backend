import asyncio
from dataclasses import dataclass
from uuid import UUID

from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class CuratorTopic:
    topic: Topic
    curator: User


class FindTopicsByNameHandler:
    def __init__(self, topic_repository: TopicRepository, user_repository: UserRepository) -> None:
        self.topic_repository = topic_repository
        self.user_repository = user_repository

    async def handle(self, name: str) -> list[CuratorTopic]:
        topics = await self.topic_repository.find_topics_by_name(name)

        curators = await self._get_curators(topics)

        return [CuratorTopic(topic=topic, curator=curators[topic.user_id]) for topic in topics]

    async def _get_curators(self, topics: list[Topic]) -> dict[UUID, User]:
        user_ids = {topic.user_id for topic in topics}

        tasks = [self.user_repository.get(user_id) for user_id in user_ids]

        users = await asyncio.gather(*tasks)

        return {user.uuid: user for user in users if user is not None}
