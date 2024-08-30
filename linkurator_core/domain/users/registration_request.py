from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Callable
from uuid import UUID, uuid4

from linkurator_core.domain.users.user import User


def default_now_function() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class RegistrationRequest:
    uuid: UUID
    user: User
    valid_until: datetime

    @classmethod
    def new(cls,
            user: User,
            seconds_to_expire: int,
            uuid_generator: Callable[[], UUID] = uuid4,
            now_function: Callable[[], datetime] = default_now_function
            ) -> RegistrationRequest:
        return cls(
            uuid=uuid_generator(),
            user=user,
            valid_until=now_function() + timedelta(seconds=seconds_to_expire)
        )

    def is_valid(self, now_function: Callable[[], datetime] = default_now_function) -> bool:
        return now_function() < self.valid_until
