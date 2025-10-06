from uuid import UUID

from linkurator_core.domain.users.user_filter import UserFilter
from linkurator_core.domain.users.user_filter_repository import UserFilterRepository


class GetUserFilterHandler:
    def __init__(self, user_filter_repository: UserFilterRepository) -> None:
        self.user_filter_repository = user_filter_repository

    async def handle(self, user_id: UUID) -> UserFilter | None:
        return await self.user_filter_repository.get(user_id)
