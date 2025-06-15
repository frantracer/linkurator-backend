from __future__ import annotations

from copy import copy
from uuid import UUID

from linkurator_core.domain.users.password_change_request import PasswordChangeRequest
from linkurator_core.domain.users.password_change_request_repository import PasswordChangeRequestRepository


class InMemoryPasswordChangeRequestRepository(PasswordChangeRequestRepository):
    def __init__(self) -> None:
        self.requests: dict[UUID, PasswordChangeRequest] = {}

    async def add_request(self, request: PasswordChangeRequest) -> None:
        self.requests[request.uuid] = copy(request)

    async def get_request(self, uuid: UUID) -> PasswordChangeRequest | None:
        if uuid in self.requests:
            return copy(self.requests[uuid])
        return None

    async def delete_request(self, uuid: UUID) -> None:
        if uuid in self.requests:
            self.requests.pop(uuid, None)
