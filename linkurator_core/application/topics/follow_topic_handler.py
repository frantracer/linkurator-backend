from uuid import UUID

from linkurator_core.domain.common.exceptions import CannotFollowOwnedTopicError, TopicNotFoundError
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


class FollowTopicHandler:
    def __init__(self, topic_repository: TopicRepository,
                 user_repository: UserRepository) -> None:
        self.topic_repository = topic_repository
        self.user_repository = user_repository

    async def handle(self, user_id: UUID, topic_id: UUID) -> None:
        topic = await self.topic_repository.get(topic_id)
        if topic is None:
            raise TopicNotFoundError()

        if topic.user_id == user_id:
            raise CannotFollowOwnedTopicError()

        user = await self.user_repository.get(user_id)
        if user is None:
            return

        user.follow_topic(topic_id)

        await self.user_repository.update(user)
