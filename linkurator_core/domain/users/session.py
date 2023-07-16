from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID


@dataclass
class Session:
    token: str
    user_id: UUID
    expires_at: datetime

    def is_expired(self) -> bool:
        now = datetime.now(tz=timezone.utc).timestamp()
        return self.expires_at.timestamp() < now
