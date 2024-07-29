import asyncio
from dataclasses import dataclass
from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.topics.followed_topics_repository import FollowedTopicsRepository
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class CuratorTopic:
    topic: Topic
    followed: bool


class GetCuratorTopicsAsUserHandler:
    def __init__(self, user_repository: UserRepository,
                 topic_repository: TopicRepository,
                 followed_topics_repository: FollowedTopicsRepository) -> None:
        self.user_repository = user_repository
        self.topic_repository = topic_repository
        self.followed_topics_repo = followed_topics_repository

    async def handle(self, curator_id: UUID, user_id: UUID) -> list[CuratorTopic]:
        user_result = await asyncio.gather(
            self.user_repository.get(curator_id),
            self.user_repository.get(user_id)
        )

        curator = user_result[0]
        if curator is None:
            raise UserNotFoundError(curator_id)

        user = user_result[1]
        if user is None:
            raise UserNotFoundError(user_id)

        result = await asyncio.gather(
            self.followed_topics_repo.get_followed_topics(user_id),
            self.topic_repository.get_by_user_id(curator_id))

        followed_topics = result[0]
        curator_topics = result[1]

        followed_topics_ids = {followed_topic.topic_uuid for followed_topic in followed_topics}

        return [
            CuratorTopic(topic=topic, followed=topic.uuid in followed_topics_ids)
            for topic in curator_topics
        ]
