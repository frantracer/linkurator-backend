from dataclasses import dataclass
from uuid import UUID

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class FindCuratorResponse:
    user: User | None
    followed: bool


class FindCuratorHandler:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def handle(self, username: str, current_user_id: UUID) -> FindCuratorResponse:
        user = await self.user_repository.get(current_user_id)
        if user is None:
            raise UserNotFoundError("User not found")

        curator = await self.user_repository.get_by_username(username.lower())
        if curator is None:
            return FindCuratorResponse(user=None, followed=False)

        followed = curator.uuid in user.curators
        return FindCuratorResponse(user=curator, followed=followed)
