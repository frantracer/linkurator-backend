from uuid import UUID

from linkurator_core.domain.users.password_change_request_repository import PasswordChangeRequestRepository
from linkurator_core.domain.users.user_repository import UserRepository


class ChangePasswordFromRequest:
    def __init__(self, request_repository: PasswordChangeRequestRepository, user_repository: UserRepository) -> None:
        self.request_repository = request_repository
        self.user_repository = user_repository

    async def handle(self, request_id: UUID, new_password: str) -> bool:
        request = await self.request_repository.get_request(request_id)
        if request is None:
            return False

        if request.is_expired():
            await self.request_repository.delete_request(request_id)
            return False

        user = await self.user_repository.get(request.user_id)
        if user is None:
            return False

        await self.request_repository.delete_request(request_id)

        user.set_password(new_password)
        await self.user_repository.update(user)

        return True
