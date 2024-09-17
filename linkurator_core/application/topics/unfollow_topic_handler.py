from uuid import UUID

from linkurator_core.domain.users.user_repository import UserRepository


class UnfollowTopicHandler:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def handle(self, user_id: UUID, topic_id: UUID) -> None:
        user = await self.user_repository.get(user_id)
        if user is None:
            return

        user.unfollow_topic(topic_id)

        await self.user_repository.update(user)
