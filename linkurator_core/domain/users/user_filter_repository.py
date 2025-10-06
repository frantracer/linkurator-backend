import abc
from uuid import UUID

from linkurator_core.domain.users.user_filter import UserFilter


class UserFilterRepository(abc.ABC):
    @abc.abstractmethod
    async def get(self, user_id: UUID) -> UserFilter | None: ...

    @abc.abstractmethod
    async def upsert(self, user_filter: UserFilter) -> None: ...

    @abc.abstractmethod
    async def delete(self, user_id: UUID) -> None: ...

    @abc.abstractmethod
    async def delete_all(self) -> None: ...
