from __future__ import annotations

import abc
import importlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel


class SerializedEvent(BaseModel):
    event_class: str
    event_data: str


class Event(abc.ABC, BaseModel):
    id: UUID
    created_at: datetime

    def __str__(self) -> str:
        return f"{self.__class__.__name__} ({self.id}) at {self.created_at}"

    def serialize(self) -> str:
        payload = SerializedEvent(
            event_class=self.__class__.__name__,
            event_data=self.model_dump_json()
        )

        return payload.model_dump_json()

    @staticmethod
    def deserialize(raw_data: str) -> Event:
        payload = SerializedEvent(**json.loads(raw_data))
        event_class = payload.event_class
        event_data = json.loads(payload.event_data)

        # Import the module that contains the class
        module = importlib.import_module('linkurator_core.domain.common.event')

        # Get the class from the module
        class_ = getattr(module, event_class)

        # Instantiate the class with the unpacked dictionary as keyword arguments
        instance = class_(**event_data)

        return instance


class SubscriptionItemsBecameOutdatedEvent(Event):
    subscription_id: UUID

    @classmethod
    def new(cls, subscription_id: UUID) -> SubscriptionItemsBecameOutdatedEvent:
        return cls(
            id=uuid4(),
            created_at=datetime.utcnow(),
            subscription_id=subscription_id
        )


class SubscriptionBecameOutdatedEvent(Event):
    subscription_id: UUID

    @classmethod
    def new(cls, subscription_id: UUID) -> SubscriptionBecameOutdatedEvent:
        return cls(
            id=uuid4(),
            created_at=datetime.utcnow(),
            subscription_id=subscription_id
        )

class ItemsBecameOutdatedEvent(Event):
    item_ids: set[UUID]

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ItemsBecameOutdatedEvent):
            return False
        return self.item_ids == other.item_ids

    @classmethod
    def new(cls, item_ids: set[UUID]) -> ItemsBecameOutdatedEvent:
        return cls(
            id=uuid4(),
            created_at=datetime.utcnow(),
            item_ids=item_ids
        )


class UserRegisterRequestSentEvent(Event):
    request_uuid: UUID

    @classmethod
    def new(cls, request_uuid: UUID) -> UserRegisterRequestSentEvent:
        return cls(
            id=uuid4(),
            created_at=datetime.utcnow(),
            request_uuid=request_uuid
        )


class UserRegisteredEvent(Event):
    user_id: UUID

    @classmethod
    def new(cls, user_id: UUID) -> UserRegisteredEvent:
        return cls(
            id=uuid4(),
            created_at=datetime.utcnow(),
            user_id=user_id
        )
