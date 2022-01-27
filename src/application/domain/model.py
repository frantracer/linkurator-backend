from dataclasses import dataclass
from datetime import datetime
from typing import List
from uuid import UUID
from pydantic import AnyUrl


@dataclass
class Item:
    uuid: UUID
    subscription_uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime


@dataclass
class Subscription:
    uuid: UUID
    name: str
    url: AnyUrl
    thumbnail: AnyUrl
    created_at: datetime
    updated_at: datetime
    scanned_at: datetime


@dataclass
class Topic:
    uuid: UUID
    name: str
    user_id: UUID
    subscriptions_ids: List[UUID]
    created_at: datetime
    updated_at: datetime


@dataclass
class User:
    uuid: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime
