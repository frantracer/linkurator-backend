import abc
from typing import Optional
from uuid import UUID

from application.domain.user import User


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
