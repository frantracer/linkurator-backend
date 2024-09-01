import abc
from uuid import UUID

from linkurator_core.domain.users.password_change_request import PasswordChangeRequest


class PasswordChangeRequestRepository(abc.ABC):
    @abc.abstractmethod
    async def add_request(self, request: PasswordChangeRequest) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_request(self, uuid: UUID) -> PasswordChangeRequest | None:
        raise NotImplementedError()

    @abc.abstractmethod
    async def delete_request(self, uuid: UUID) -> None:
        raise NotImplementedError()
