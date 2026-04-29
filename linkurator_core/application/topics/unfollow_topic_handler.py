from uuid import UUID

from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


class UnfollowTopicHandler:
    def __init__(self, user_repository: UserRepository,
                 topic_repository: TopicRepository) -> None:
        self.user_repository = user_repository
        self.topic_repository = topic_repository

    async def handle(self, user_id: UUID, topic_id: UUID) -> None:
        user = await self.user_repository.get(user_id)
        if user is None:
            return

        user.unfollow_topic(topic_id)

        topic = await self.topic_repository.get(topic_id)
        if topic is not None and topic.user_id != user_id:
            user.unfavorite_topic(topic_id)

        await self.user_repository.update(user)
