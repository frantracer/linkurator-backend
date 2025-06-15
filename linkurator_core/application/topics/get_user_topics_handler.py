from __future__ import annotations

import asyncio
from uuid import UUID

from pydantic.dataclasses import dataclass

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class CuratorTopic:
    topic: Topic
    curator: User


GetUserTopicsResponse = list[CuratorTopic]


class GetUserTopicsHandler:

    def __init__(self, user_repo: UserRepository,
                 topic_repo: TopicRepository) -> None:
        self.user_repo = user_repo
        self.topic_repo = topic_repo

    async def handle(self, user_id: UUID) -> GetUserTopicsResponse:
        user = await self.user_repo.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        results = await asyncio.gather(
            self.topic_repo.find_topics(list(user.get_followed_topics())),
            self.topic_repo.get_by_user_id(user_id),
        )

        followed_topics = results[0]
        user_topics = results[1]

        followed_curators = await self._get_curators(followed_topics)

        followed_curator_topics = [CuratorTopic(topic=topic, curator=followed_curators[topic.user_id])
                                   for topic in followed_topics
                                   if topic.user_id in followed_curators]
        user_curator_topics = [CuratorTopic(topic=topic, curator=user)
                               for topic in user_topics]

        return followed_curator_topics + user_curator_topics

    async def _get_followed_topics(self, user: User) -> list[Topic]:
        return await self.topic_repo.find_topics(list(user.get_followed_topics()))

    async def _get_curators(self, topics: list[Topic]) -> dict[UUID, User]:
        user_ids = {topic.user_id for topic in topics}

        tasks = [self.user_repo.get(user_id) for user_id in user_ids]

        users = await asyncio.gather(*tasks)

        return {user.uuid: user for user in users if user is not None}
