from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    uuid: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime