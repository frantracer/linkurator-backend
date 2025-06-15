from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.users.user import User, Username
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class FindCuratorResponse:
    user: User | None
    followed: bool


class FindCuratorHandler:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def handle(self, username: Username, current_user_id: UUID | None) -> FindCuratorResponse:
        user_curators: set[UUID] = set()
        if current_user_id is not None:
            user = await self.user_repository.get(current_user_id)
            if user is None:
                msg = "User not found"
                raise UserNotFoundError(msg)
            user_curators = user.curators

        curator = await self.user_repository.get_by_username(username)
        if curator is None:
            return FindCuratorResponse(user=None, followed=False)

        followed = curator.uuid in user_curators
        return FindCuratorResponse(user=curator, followed=followed)
