import abc
import datetime
from typing import List, Optional
from uuid import UUID

from linkurator_core.domain.users.user import User


class EmailAlreadyInUse(Exception):
    pass


class UserRepository(abc.ABC):
    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    async def add(self, user: User) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, user_id: UUID) -> Optional[User]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, user_id: UUID) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, user: User) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def find_latest_scan_before(self, timestamp: datetime.datetime) -> List[User]:
        raise NotImplementedError

    @abc.abstractmethod
    async def find_users_subscribed_to_subscription(self, subscription_id: UUID) -> List[User]:
        raise NotImplementedError
