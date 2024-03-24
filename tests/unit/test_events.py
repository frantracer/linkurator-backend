from uuid import uuid4

from linkurator_core.domain.common.event import Event, SubscriptionBecameOutdatedEvent


def test_event_serialization() -> None:
    event = SubscriptionBecameOutdatedEvent.new(uuid4())

    serialized_event = event.serialize()

    deserialized_event = Event.deserialize(serialized_event)

    assert event == deserialized_event
