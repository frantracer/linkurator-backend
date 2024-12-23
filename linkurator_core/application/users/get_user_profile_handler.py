from datetime import datetime, timedelta
from typing import Callable, Optional
from uuid import UUID

from linkurator_core.domain.common.utils import datetime_now
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


class GetUserProfileHandler:
    user_repository: UserRepository

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def handle(self, user_id: UUID, now_function: Callable[[], datetime] = datetime_now) -> Optional[User]:
        user = await self.user_repository.get(user_id)

        now = now_function()
        if user is not None and now - user.last_login_at > timedelta(hours=1):
            user.last_login_at = now
            await self.user_repository.update(user)

        return user
