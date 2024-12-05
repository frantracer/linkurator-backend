import abc
import datetime
from typing import List, Optional
from uuid import UUID

from linkurator_core.domain.users.user import User, Username


class EmailAlreadyInUse(Exception):
    pass


class UserRepository(abc.ABC):
    @abc.abstractmethod
    async def add(self, user: User) -> None: ...

    @abc.abstractmethod
    async def get(self, user_id: UUID) -> Optional[User]: ...

    @abc.abstractmethod
    async def get_all(self) -> List[User]: ...

    @abc.abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]: ...

    @abc.abstractmethod
    async def get_by_username(self, username: Username) -> Optional[User]: ...

    @abc.abstractmethod
    async def delete(self, user_id: UUID) -> None: ...

    @abc.abstractmethod
    async def delete_all(self) -> None: ...

    @abc.abstractmethod
    async def update(self, user: User) -> None: ...

    @abc.abstractmethod
    async def find_latest_scan_before(self, timestamp: datetime.datetime) -> List[User]: ...

    @abc.abstractmethod
    async def find_users_subscribed_to_subscription(self, subscription_id: UUID) -> List[User]: ...

    @abc.abstractmethod
    async def count_registered_users(self) -> int: ...

    @abc.abstractmethod
    async def count_active_users(self) -> int: ...
