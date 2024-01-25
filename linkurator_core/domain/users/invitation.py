from datetime import datetime
from uuid import UUID


class Invitation:
    id: UUID
    email: str
    created_at: datetime
    expires_at: datetime
