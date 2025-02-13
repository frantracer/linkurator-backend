from uuid import uuid4

from linkurator_core.domain.common.event import Event, SubscriptionItemsBecameOutdatedEvent


def test_event_serialization() -> None:
    event = SubscriptionItemsBecameOutdatedEvent.new(uuid4())

    serialized_event = event.serialize()

    deserialized_event = Event.deserialize(serialized_event)

    assert event == deserialized_event
