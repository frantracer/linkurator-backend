from __future__ import annotations

from uuid import UUID

from pydantic.dataclasses import dataclass

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class GetCuratorTopicsResponse:
    topics: list[Topic]
    curator: User


class GetCuratorTopicsHandler:
    def __init__(self, topic_repository: TopicRepository, user_repository: UserRepository) -> None:
        self.topic_repository = topic_repository
        self.user_repository = user_repository

    async def handle(self, curator_id: UUID) -> GetCuratorTopicsResponse:
        curator = await self.user_repository.get(curator_id)
        if curator is None:
            raise UserNotFoundError(curator_id)

        curator_topics = await self.topic_repository.get_by_user_id(curator_id)

        return GetCuratorTopicsResponse(topics=curator_topics, curator=curator)
