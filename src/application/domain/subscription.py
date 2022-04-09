from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic.networks import AnyUrl


@dataclass
class Subscription:
    uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime