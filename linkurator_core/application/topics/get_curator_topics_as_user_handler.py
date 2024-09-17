from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


class GetCuratorTopicsHandler:
    def __init__(self, topic_repository: TopicRepository, user_repository: UserRepository) -> None:
        self.topic_repository = topic_repository
        self.user_repository = user_repository

    async def handle(self, curator_id: UUID) -> list[Topic]:
        curator = await self.user_repository.get(curator_id)
        if curator is None:
            raise UserNotFoundError(curator_id)

        curator_topics = await self.topic_repository.get_by_user_id(curator_id)

        return curator_topics
