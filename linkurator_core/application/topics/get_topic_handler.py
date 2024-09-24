from uuid import UUID

from pydantic.dataclasses import dataclass

from linkurator_core.domain.common.exceptions import TopicNotFoundError, UserNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class GetTopicResponse:
    topic: Topic
    curator: User


class GetTopicHandler:
    def __init__(self, topic_repository: TopicRepository, user_repository: UserRepository) -> None:
        self.topic_repository = topic_repository
        self.user_repository = user_repository

    async def handle(self, topic_id: UUID) -> GetTopicResponse:
        topic = await self.topic_repository.get(topic_id)
        if topic is None:
            raise TopicNotFoundError(topic_id)

        user = await self.user_repository.get(topic.user_id)
        if user is None:
            raise UserNotFoundError(topic.user_id)

        return GetTopicResponse(topic=topic, curator=user)
