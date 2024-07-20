import abc
from typing import List, Optional
from uuid import UUID

from linkurator_core.domain.topics.topic import Topic


class TopicRepository(abc.ABC):
    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    async def add(self, topic: Topic) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, topic_id: UUID) -> Optional[Topic]:
        raise NotImplementedError

    @abc.abstractmethod
    async def find_topics(self, topic_ids: List[UUID]) -> List[Topic]:
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, topic: Topic) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, topic_id: UUID) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> List[Topic]:
        raise NotImplementedError
