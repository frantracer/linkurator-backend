from uuid import UUID

from linkurator_core.domain.users.registration_request import RegistrationRequest
from linkurator_core.domain.users.registration_requests_repository import RegistrationRequestRepository


class InMemoryRegistrationRequestRepository(RegistrationRequestRepository):
    def __init__(self) -> None:
        super().__init__()
        self.requests: dict[UUID, RegistrationRequest] = {}

    async def add_request(self, request: RegistrationRequest) -> None:
        self.requests[request.uuid] = request

    async def get_request(self, uuid: UUID) -> RegistrationRequest | None:
        return self.requests.get(uuid)

    async def delete_request(self, uuid: UUID) -> None:
        if uuid in self.requests:
            self.requests.pop(uuid, None)
