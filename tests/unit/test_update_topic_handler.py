import uuid
from copy import copy
from datetime import timezone, datetime
from unittest.mock import MagicMock, call

import pytest

from linkurator_core.domain.common.exceptions import TopicNotFoundError, SubscriptionNotFoundError
from linkurator_core.application.topics.update_topic_handler import UpdateTopicHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository


@pytest.mark.asyncio
async def test_update_topic_name() -> None:
    topic = Topic(
        uuid=uuid.UUID("37e47030-5f82-4b17-a5c6-a9667bbff1be"),
        name="topic1",
        user_id=uuid.UUID("815c38fd-6db2-403b-9b76-3dcbc3518cb5"),
        created_at=datetime.fromtimestamp(0, tz=timezone.utc),
        updated_at=datetime.fromtimestamp(1, tz=timezone.utc),
        subscriptions_ids=[uuid.UUID("73207811-f6d0-4a47-8e33-307be731fdcc")])
    topic_repository = MagicMock(spec=TopicRepository)
    topic_repository.get.return_value = copy(topic)

    subscription_repository = MagicMock(spec=SubscriptionRepository)

    handler = UpdateTopicHandler(topic_repository=topic_repository, subscription_repository=subscription_repository)

    await handler.handle(topic_id=topic.uuid, name="topic2", subscriptions_ids=None)

    assert topic_repository.get.call_count == 1
    assert topic_repository.get.call_args == call(topic.uuid)
    assert topic_repository.update.call_count == 1
    updated_topic = topic_repository.update.call_args[0][0]
    assert updated_topic.name == "topic2"
    assert updated_topic.updated_at > topic.updated_at
    assert updated_topic.subscriptions_ids == topic.subscriptions_ids


@pytest.mark.asyncio
async def test_update_topic_subscriptions() -> None:
    topic = Topic(
        uuid=uuid.UUID("08ec8a7e-b433-4c70-971e-d52d1e3ffcc0"),
        name="topic1",
        user_id=uuid.UUID("535f0651-f5c4-422b-90fa-10144e4fd695"),
        created_at=datetime.fromtimestamp(0, tz=timezone.utc),
        updated_at=datetime.fromtimestamp(1, tz=timezone.utc),
        subscriptions_ids=[uuid.UUID("e7c9773b-9569-42c1-ab6c-43296756c534")])
    topic_repository = MagicMock(spec=TopicRepository)
    topic_repository.get.return_value = copy(topic)

    subscription_repository = MagicMock(spec=SubscriptionRepository)
    subscription_repository.get = MagicMock(return_value=Subscription.new(
        uuid=uuid.UUID("e7c9773b-9569-42c1-ab6c-43296756c534"),
        name="subscription1",
        provider=SubscriptionProvider.YOUTUBE,
        thumbnail=utils.parse_url("https://example.com/thumbnail.png"),
        external_data={},
        url=utils.parse_url("https://url.com")
    ))

    handler = UpdateTopicHandler(
        topic_repository=topic_repository,
        subscription_repository=subscription_repository)

    await handler.handle(
        topic_id=topic.uuid,
        name=None,
        subscriptions_ids=[uuid.UUID("8cfb4561-6fc5-4cc0-914d-cc91737cb316")])

    assert topic_repository.get.call_count == 1
    assert topic_repository.get.call_args == call(topic.uuid)
    assert topic_repository.update.call_count == 1

    assert subscription_repository.get.call_count == 1
    assert subscription_repository.get.call_args == call(uuid.UUID("8cfb4561-6fc5-4cc0-914d-cc91737cb316"))

    updated_topic = topic_repository.update.call_args[0][0]
    assert updated_topic.name == topic.name
    assert updated_topic.updated_at > topic.updated_at
    assert updated_topic.subscriptions_ids == [uuid.UUID("8cfb4561-6fc5-4cc0-914d-cc91737cb316")]


@pytest.mark.asyncio
async def test_update_non_existing_topic_returns_error() -> None:
    topic_repository = MagicMock(spec=TopicRepository)
    topic_repository.get.return_value = None

    subscription_repository = MagicMock(spec=SubscriptionRepository)

    handler = UpdateTopicHandler(topic_repository=topic_repository, subscription_repository=subscription_repository)

    with pytest.raises(TopicNotFoundError):
        await handler.handle(
            topic_id=uuid.UUID("37e47030-5f82-4b17-a5c6-a9667bbff1be"),
            name="topic2",
            subscriptions_ids=None)


@pytest.mark.asyncio
async def test_update_topic_with_non_existing_topic_returns_error() -> None:
    topic_repository = MagicMock(spec=TopicRepository)
    topic_repository.get.return_value = Topic(
        uuid=uuid.UUID("cdd2d4ec-4965-4751-b001-3cc6c5de68ae"),
        name="topic1",
        user_id=uuid.UUID("b8a7028e-8b4e-4d07-9c28-d69da7b1d7c7"),
        created_at=datetime.fromtimestamp(0, tz=timezone.utc),
        updated_at=datetime.fromtimestamp(1, tz=timezone.utc),
        subscriptions_ids=[])
    topic_repository.update.side_effect = TopicNotFoundError()

    subscription_repository = MagicMock(spec=SubscriptionRepository)
    subscription_repository.get = MagicMock(return_value=None)

    handler = UpdateTopicHandler(topic_repository=topic_repository, subscription_repository=subscription_repository)

    with pytest.raises(SubscriptionNotFoundError):
        await handler.handle(
            topic_id=uuid.UUID("cdd2d4ec-4965-4751-b001-3cc6c5de68ae"),
            name="topic2",
            subscriptions_ids=[uuid.UUID("0dc54832-41d5-41e4-9da1-e2c741a928d9")])
