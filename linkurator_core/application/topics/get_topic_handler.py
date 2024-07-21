from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from linkurator_core.domain.common.exceptions import TopicNotFoundError
from linkurator_core.domain.topics.followed_topics_repository import FollowedTopicsRepository
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository


@dataclass
class GetTopicResponse:
    topic: Topic
    followed: bool


class GetTopicHandler:
    def __init__(self, topic_repository: TopicRepository,
                 followed_topics_repository: FollowedTopicsRepository) -> None:
        self.topic_repository = topic_repository
        self.followed_topics_repository = followed_topics_repository

    async def handle(self, topic_id: UUID, user_id: Optional[UUID]) -> GetTopicResponse:
        topic = await self.topic_repository.get(topic_id)
        if topic is None:
            raise TopicNotFoundError(topic_id)

        followed = False
        if user_id is not None:
            followed = await self.followed_topics_repository.is_following(user_id, topic_id)

        return GetTopicResponse(topic=topic, followed=followed)
