import abc
import datetime
import uuid


class Event(abc.ABC):
    id: uuid.UUID
    created_at: datetime.datetime

    def __init__(self, event_id: uuid.UUID):
        self.id = event_id
        self.created_at = datetime.datetime.now()

    def __str__(self):
        return f"{self.__class__.__name__} ({self.id}) at {self.created_at}"


class UserSubscriptionsBecameOutdatedEvent(Event):
    user_id: uuid.UUID

    def __init__(self, event_id: uuid.UUID, user_id: uuid.UUID):
        super().__init__(event_id)
        self.user_id = user_id


class SubscriptionBecameOutdatedEvent(Event):
    subscription_id: uuid.UUID

    def __init__(self, event_id: uuid.UUID, subscription_id: uuid.UUID):
        super().__init__(event_id)
        self.subscription_id = subscription_id
