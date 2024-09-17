import asyncio
from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


class GetUserTopicsHandler:
    def __init__(self, user_repo: UserRepository,
                 topic_repo: TopicRepository) -> None:
        self.user_repo = user_repo
        self.topic_repo = topic_repo

    async def handle(self, user_id: UUID) -> list[Topic]:
        user = await self.user_repo.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        results = await asyncio.gather(
            self.topic_repo.find_topics(list(user.get_followed_topics())),
            self.topic_repo.get_by_user_id(user_id)
        )

        return results[0] + results[1]

    async def _get_followed_topics(self, user: User) -> list[Topic]:
        return await self.topic_repo.find_topics(list(user.get_followed_topics()))
