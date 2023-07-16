import abc
from typing import List, Optional
from uuid import UUID

from linkurator_core.domain.topics.topic import Topic


class TopicRepository(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def add(self, topic: Topic):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, topic_id: UUID) -> Optional[Topic]:
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, topic: Topic) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, topic_id: UUID):
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_user_id(self, user_id: UUID) -> List[Topic]:
        raise NotImplementedError
