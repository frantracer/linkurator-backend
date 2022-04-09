from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic.networks import AnyUrl


@dataclass
class Item:
    uuid: UUID
    subscription_uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime
