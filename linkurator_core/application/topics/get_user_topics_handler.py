import asyncio
from dataclasses import dataclass
from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.topics.followed_topics_repository import FollowedTopicsRepository
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class GetUserTopicsResponse:
    topics: list[Topic]
    followed_topics_ids: set[UUID]


class GetUserTopicsHandler:
    def __init__(self, user_repo: UserRepository,
                 topic_repo: TopicRepository,
                 followed_topics_repo: FollowedTopicsRepository) -> None:
        self.user_repo = user_repo
        self.topic_repo = topic_repo
        self.followed_topics_repo = followed_topics_repo

    async def handle(self, user_id: UUID) -> GetUserTopicsResponse:
        user = await self.user_repo.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        result = await asyncio.gather(
            self._get_followed_topics(user_id),
            self.topic_repo.get_by_user_id(user_id))

        return GetUserTopicsResponse(
            topics=result[0] + result[1],
            followed_topics_ids={followed_topic.uuid for followed_topic in result[0]}
        )

    async def _get_followed_topics(self, user_id: UUID) -> list[Topic]:
        followed_topics = await self.followed_topics_repo.get_followed_topics(user_id)
        followed_topics_ids = [followed_topic.topic_uuid for followed_topic in followed_topics]
        return await self.topic_repo.find_topics(followed_topics_ids)
