from abc import ABC, abstractmethod
from uuid import UUID

from linkurator_core.domain.topics.followed_topic import FollowedTopic


class FollowedTopicsRepository(ABC):

    @abstractmethod
    async def get_followed_topics(self, user_uuid: UUID) -> list[FollowedTopic]:
        pass

    @abstractmethod
    async def follow_topic(self, user_id: UUID, topic_id: UUID) -> None:
        pass

    @abstractmethod
    async def unfollow_topic(self, user_uuid: UUID, topic_uuid: UUID) -> None:
        pass

    @abstractmethod
    async def is_following(self, user_uuid: UUID, topic_uuid: UUID) -> bool:
        pass
