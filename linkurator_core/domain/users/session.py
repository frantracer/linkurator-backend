import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

SESSION_DURATION_IN_SECONDS = 60 * 60 * 24 * 30  # 30 days


def generate_random_token_128_chars() -> str:
    return secrets.token_hex(64)


def datetime_now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class Session:
    token: str
    user_id: UUID
    expires_at: datetime

    @classmethod
    def new(cls,
            user_id: UUID,
            seconds_to_expire: int,
            token_generator: Callable[[], str] = generate_random_token_128_chars,
            now_function: Callable[[], datetime] = datetime_now_utc,
            ) -> "Session":
        return cls(
            token=token_generator(),
            user_id=user_id,
            expires_at=now_function() + timedelta(seconds=seconds_to_expire),
        )

    def is_expired(self) -> bool:
        now = datetime.now(tz=timezone.utc).timestamp()
        return self.expires_at.timestamp() < now
