from uuid import UUID

from linkurator_core.domain.common.exceptions import CannotFollowOwnedTopicError, TopicNotFoundError
from linkurator_core.domain.topics.followed_topics_repository import FollowedTopicsRepository
from linkurator_core.domain.topics.topic_repository import TopicRepository


class FollowTopicHandler:
    def __init__(self, topic_repository: TopicRepository,
                 followed_topics_repository: FollowedTopicsRepository):
        self.topic_repository = topic_repository
        self.followed_topics_repository = followed_topics_repository

    async def handle(self, user_id: UUID, topic_id: UUID) -> None:
        topic = await self.topic_repository.get(topic_id)
        if topic is None:
            raise TopicNotFoundError()

        if topic.user_id == user_id:
            raise CannotFollowOwnedTopicError()

        await self.followed_topics_repository.follow_topic(user_id, topic_id)
