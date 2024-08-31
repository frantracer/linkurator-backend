from uuid import UUID

from linkurator_core.domain.common.event import UserRegisteredEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.exceptions import InvalidRegistrationRequestError
from linkurator_core.domain.users.registration_requests_repository import RegistrationRequestRepository
from linkurator_core.domain.users.user_repository import UserRepository


class ValidateNewUserRequest:
    def __init__(self,
                 registration_request_repository: RegistrationRequestRepository,
                 user_repository: UserRepository,
                 event_bus: EventBusService
                 ) -> None:
        self.registration_request_repository = registration_request_repository
        self.user_repository = user_repository
        self.event_bus = event_bus

    async def handle(self, request_uuid: UUID) -> None:
        request = await self.registration_request_repository.get_request(request_uuid)
        if request is None:
            raise InvalidRegistrationRequestError()

        if not request.is_valid():
            await self.registration_request_repository.delete_request(request_uuid)
            raise InvalidRegistrationRequestError()

        await self.user_repository.add(request.user)

        await self.registration_request_repository.delete_request(request_uuid)

        await self.event_bus.publish(UserRegisteredEvent.new(user_id=request.user.uuid))
