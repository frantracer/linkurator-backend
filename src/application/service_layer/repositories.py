import abc
from typing import List, Optional
from uuid import UUID
from application.domain.model import Item, Subscription, Topic, User


class AbstractItemRepository(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def add(self, item: Item):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, item_id: UUID) -> Optional[Item]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_topic_id(self, topic_id: UUID) -> List[Item]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_subscription_id(self, topic_id: UUID) -> List[Item]:
        raise NotImplementedError


class AbstractSubscriptionRepository(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def add(self, subscription: Subscription):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, subscription_id: UUID) -> Optional[Subscription]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_topic_id(self, topic_id: UUID) -> List[Subscription]:
        raise NotImplementedError


class AbstractTopicRepository(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def add(self, topic: Topic):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, topic_id: UUID) -> Optional[Topic]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, topic_id: UUID):
        raise NotImplementedError


class AbstractUserRepository(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def add(self, user: User):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, user_id: UUID) -> Optional[User]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, user_id: UUID):
        raise NotImplementedError
