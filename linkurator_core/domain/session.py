from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Session:
    token: str
    user_id: UUID
    expires_at: datetime

    def is_expired(self) -> bool:
        return self.expires_at > datetime.now()
