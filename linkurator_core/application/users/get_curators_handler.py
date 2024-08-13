import asyncio
from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


class GetCuratorsHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self, user_id: UUID) -> list[User]:
        user = await self.user_repository.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        tasks = [self.user_repository.get(curator_id) for curator_id in user.curators]

        curators = await asyncio.gather(*tasks)

        return [curator for curator in curators if curator is not None]
