import abc
from uuid import UUID

from linkurator_core.domain.users.registration_request import RegistrationRequest


class RegistrationRequestRepository(abc.ABC):
    @abc.abstractmethod
    async def add_request(self, request: RegistrationRequest) -> None:
        pass

    @abc.abstractmethod
    async def get_request(self, uuid: UUID) -> RegistrationRequest | None:
        pass

    @abc.abstractmethod
    async def delete_request(self, uuid: UUID) -> None:
        pass
