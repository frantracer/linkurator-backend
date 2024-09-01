from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID, uuid4


def default_datetime_generator() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class PasswordChangeRequest:
    uuid: UUID
    user_id: UUID
    valid_until: datetime

    @classmethod
    def new(cls,
            user_id: UUID,
            seconds_to_expire: int,
            now_function: Callable[[], datetime] = default_datetime_generator,
            uuid_generator: Callable[[], UUID] = uuid4
            ) -> PasswordChangeRequest:
        return cls(
            uuid=uuid_generator(),
            user_id=user_id,
            valid_until=now_function() + timedelta(seconds=seconds_to_expire)
        )

    def is_expired(self, now_function: Callable[[], datetime] = default_datetime_generator) -> bool:
        return now_function() > self.valid_until
