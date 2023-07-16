import abc
import datetime
from typing import List, Optional
from uuid import UUID

from linkurator_core.domain.users.user import User


class EmailAlreadyInUse(Exception):
    pass


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
    def get_by_email(self, email: str) -> Optional[User]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, user_id: UUID):
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, user: User):
        raise NotImplementedError

    @abc.abstractmethod
    def find_latest_scan_before(self, timestamp: datetime.datetime) -> List[User]:
        raise NotImplementedError
