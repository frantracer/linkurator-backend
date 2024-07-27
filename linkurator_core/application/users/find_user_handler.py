from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


class FindUserHandler:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def handle(self, username: str) -> User | None:
        return await self.user_repository.get_by_username(username.lower())
