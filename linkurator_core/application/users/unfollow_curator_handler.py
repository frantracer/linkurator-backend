from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.users.user_repository import UserRepository


class UnfollowCuratorHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self, user_id: UUID, curator_id: UUID) -> None:
        user = await self.user_repository.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        user.unfollow_curator(curator_id)

        await self.user_repository.update(user)
