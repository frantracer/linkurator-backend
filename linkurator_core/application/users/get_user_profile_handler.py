from typing import Optional
from uuid import UUID

from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


class GetUserProfileHandler:
    user_repository: UserRepository

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def handle(self, user_id: UUID) -> Optional[User]:
        return self.user_repository.get(user_id)
