from uuid import UUID

from linkurator_core.domain.topics.followed_topics_repository import FollowedTopicsRepository


class UnfollowTopicHandler:
    def __init__(self, followed_topics_repository: FollowedTopicsRepository):
        self.followed_topics_repository = followed_topics_repository

    async def handle(self, user_id: UUID, topic_id: UUID) -> None:
        await self.followed_topics_repository.unfollow_topic(user_id, topic_id)
