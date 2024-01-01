import abc
from datetime import datetime, timezone
import uuid
from typing import Any


class Event(abc.ABC):
    id: uuid.UUID
    created_at: datetime

    def __init__(self, event_id: uuid.UUID) -> None:
        self.id = event_id
        self.created_at = datetime.now(tz=timezone.utc)

    def __str__(self) -> str:
        return f"{self.__class__.__name__} ({self.id}) at {self.created_at}"


class UserSubscriptionsBecameOutdatedEvent(Event):
    user_id: uuid.UUID

    def __init__(self, event_id: uuid.UUID, user_id: uuid.UUID) -> None:
        super().__init__(event_id)
        self.user_id = user_id


class SubscriptionBecameOutdatedEvent(Event):
    subscription_id: uuid.UUID

    def __init__(self, event_id: uuid.UUID, subscription_id: uuid.UUID) -> None:
        super().__init__(event_id)
        self.subscription_id = subscription_id


class ItemsBecameOutdatedEvent(Event):
    item_ids: set[uuid.UUID]

    def __init__(self, event_id: uuid.UUID, item_ids: set[uuid.UUID]) -> None:
        super().__init__(event_id)
        self.item_ids = item_ids

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ItemsBecameOutdatedEvent):
            return False
        return self.item_ids == other.item_ids
