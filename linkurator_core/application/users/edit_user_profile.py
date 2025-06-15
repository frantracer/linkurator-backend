from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from uuid import UUID

from linkurator_core.domain.common.exceptions import UsernameAlreadyInUseError, UserNotFoundError
from linkurator_core.domain.common.utils import datetime_now
from linkurator_core.domain.users.user import Username
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class NewProfileAttributes:
    first_name: str | None = None
    last_name: str | None = None
    username: Username | None = None


class EditUserProfile:
    def __init__(self,
                 user_repository: UserRepository,
                 now_function: Callable[[], datetime] = datetime_now,
                 ) -> None:
        self.user_repository = user_repository
        self.now_function = now_function

    async def handle(
            self,
            user_id: UUID,
            new_attributes: NewProfileAttributes,
    ) -> None:
        user = await self.user_repository.get(user_id)
        if not user:
            msg = f"User with id {user_id} not found"
            raise UserNotFoundError(msg)

        if new_attributes.first_name:
            user.first_name = new_attributes.first_name

        if new_attributes.last_name:
            user.last_name = new_attributes.last_name

        if new_attributes.username:
            existing_user = await self.user_repository.get_by_username(new_attributes.username)
            if existing_user is not None:
                msg = f"Username {new_attributes.username} already in use"
                raise UsernameAlreadyInUseError(msg)
            user.username = new_attributes.username

        user.updated_at = self.now_function()

        await self.user_repository.update(user)
