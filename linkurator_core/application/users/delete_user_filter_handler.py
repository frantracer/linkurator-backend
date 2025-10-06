from uuid import UUID

from linkurator_core.domain.users.user_filter_repository import UserFilterRepository


class DeleteUserFilterHandler:
    def __init__(self, user_filter_repository: UserFilterRepository) -> None:
        self.user_filter_repository = user_filter_repository

    async def handle(self, user_id: UUID) -> None:
        await self.user_filter_repository.delete(user_id)
