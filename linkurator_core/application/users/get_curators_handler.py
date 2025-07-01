from __future__ import annotations

import asyncio
from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


class GetCuratorsHandler:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def handle(
        self,
        user_id: UUID | None = None,
        username: str | None = None,
    ) -> list[User]:
        if user_id is not None:
            user = await self.user_repository.get(user_id)
            if user is None:
                raise UserNotFoundError(user_id)

            tasks = [self.user_repository.get(curator_id) for curator_id in user.curators]
            curators = await asyncio.gather(*tasks)
            followed_curators = [curator for curator in curators if curator is not None]

            if username is not None and username != "":
                return [c for c in followed_curators if username.lower() in str(c.username).lower()]
            return followed_curators

        if username:
            return await self.user_repository.search_by_username(username)

        return []
