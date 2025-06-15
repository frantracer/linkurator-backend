from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.users.user_repository import UserRepository


class FollowCuratorHandler:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def handle(self, user_id: UUID, curator_id: UUID) -> None:
        user = await self.user_repository.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        curator = await self.user_repository.get(curator_id)
        if curator is None:
            raise UserNotFoundError(curator_id)

        user.follow_curator(curator_id)

        await self.user_repository.update(user)
