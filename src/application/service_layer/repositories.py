import abc
from typing import List, Optional
from uuid import UUID
from application.domain.user import User
from application.domain.topic import Topic
from application.domain.subscription import Subscription
from application.domain.item import Item


class ItemRepository(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def add(self, item: Item):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, item_id: UUID) -> Optional[Item]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, item_id: UUID):
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_subscription_id(self, subscription_id: UUID) -> List[Item]:
        raise NotImplementedError


class SubscriptionRepository(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def add(self, subscription: Subscription):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, subscription_id: UUID) -> Optional[Subscription]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, subscription_id: UUID):
        raise NotImplementedError


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
    def delete(self, topic_id: UUID):
        raise NotImplementedError

    @abc.abstractmethod
    def get_by_user_id(self, user_id: UUID) -> List[Topic]:
        raise NotImplementedError


class UserRepository(abc.ABC):
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
