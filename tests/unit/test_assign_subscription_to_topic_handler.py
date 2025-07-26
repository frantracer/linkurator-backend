from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from linkurator_core.application.topics.assign_subscription_to_user_topic_handler import (
    AssignSubscriptionToTopicHandler,
)
from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError, TopicNotFoundError, UserNotFoundError
from linkurator_core.domain.common.mock_factory import mock_sub, mock_user
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


@pytest.mark.asyncio()
async def test_assign_subscription_to_topic_handler() -> None:
    user_id = UUID("b9534313-5dbf-4596-9493-779b55ead651")
    subscription_id = UUID("942ad011-362c-4b12-accb-a5c8f273e8db")
    topic_id = UUID("9b3020f8-6f72-4a78-bff6-c315e36808de")

    user_repo_mock = AsyncMock(spec=UserRepository)
    user_repo_mock.get.return_value = mock_user(uuid=user_id, subscribed_to=[subscription_id])
    subs_repo_mock = MagicMock()
    subs_repo_mock.get.return_value = mock_sub(uuid=subscription_id)
    topic_repo_mock = AsyncMock(spec=TopicRepository)
    topic_repo_mock.get.return_value = Topic.new(
        uuid=topic_id,
        name="Topic 1",
        user_id=user_id,
    )
    handler = AssignSubscriptionToTopicHandler(
        user_repository=user_repo_mock,
        subscription_repository=subs_repo_mock,
        topic_repository=topic_repo_mock)

    await handler.handle(user_id, subscription_id, topic_id)

    assert user_repo_mock.get.called
    assert subs_repo_mock.get.called
    assert topic_repo_mock.get.called
    assert topic_repo_mock.update.called
    updated_topic: Topic = topic_repo_mock.update.call_args[0][0]
    assert topic_id == updated_topic.uuid
    assert subscription_id in updated_topic.subscriptions_ids


@pytest.mark.asyncio()
async def test_assign_subscription_to_topic_handler_user_not_found_raises_an_error() -> None:
    user_id = UUID("b9534313-5dbf-4596-9493-779b55ead651")
    subscription_id = UUID("942ad011-362c-4b12-accb-a5c8f273e8db")
    topic_id = UUID("9b3020f8-6f72-4a78-bff6-c315e36808de")

    user_repo_mock = AsyncMock(spec=UserRepository)
    user_repo_mock.get.return_value = None
    handler = AssignSubscriptionToTopicHandler(
        user_repository=user_repo_mock,
        subscription_repository=MagicMock(),
        topic_repository=MagicMock())

    with pytest.raises(UserNotFoundError):
        await handler.handle(user_id, subscription_id, topic_id)


@pytest.mark.asyncio()
async def test_assign_subscription_to_topic_handler_subscription_not_found_raises_an_error() -> None:
    user_id = UUID("b9534313-5dbf-4596-9493-779b55ead651")
    subscription_id = UUID("942ad011-362c-4b12-accb-a5c8f273e8db")
    topic_id = UUID("9b3020f8-6f72-4a78-bff6-c315e36808de")

    user_repo_mock = AsyncMock(spec=UserRepository)
    user_repo_mock.get.return_value = mock_user(uuid=user_id)
    subs_repo_mock = MagicMock()
    subs_repo_mock.get.return_value = None
    handler = AssignSubscriptionToTopicHandler(
        user_repository=user_repo_mock,
        subscription_repository=subs_repo_mock,
        topic_repository=MagicMock())

    with pytest.raises(SubscriptionNotFoundError):
        await handler.handle(user_id, subscription_id, topic_id)


@pytest.mark.asyncio()
async def test_assign_subscription_to_topic_handler_user_not_subscribed_to_subscription_raises_an_error() -> None:
    user_id = UUID("b9534313-5dbf-4596-9493-779b55ead651")
    subscription_id = UUID("942ad011-362c-4b12-accb-a5c8f273e8db")
    topic_id = UUID("9b3020f8-6f72-4a78-bff6-c315e36808de")

    user_repo_mock = AsyncMock(spec=UserRepository)
    user_repo_mock.get.return_value = mock_user(uuid=user_id, subscribed_to=[])
    subs_repo_mock = MagicMock()
    subs_repo_mock.get.return_value = mock_sub(uuid=subscription_id)
    handler = AssignSubscriptionToTopicHandler(
        user_repository=user_repo_mock,
        subscription_repository=subs_repo_mock,
        topic_repository=MagicMock())

    with pytest.raises(SubscriptionNotFoundError):
        await handler.handle(user_id, subscription_id, topic_id)


@pytest.mark.asyncio()
async def test_assign_subscription_to_topic_handler_topic_not_found_raises_an_error() -> None:
    user_id = UUID("b9534313-5dbf-4596-9493-779b55ead651")
    subscription_id = UUID("942ad011-362c-4b12-accb-a5c8f273e8db")
    topic_id = UUID("9b3020f8-6f72-4a78-bff6-c315e36808de")

    user_repo_mock = AsyncMock(spec=UserRepository)
    user_repo_mock.get.return_value = mock_user(uuid=user_id, subscribed_to=[subscription_id])
    subs_repo_mock = MagicMock()
    subs_repo_mock.get.return_value = mock_sub(uuid=subscription_id)
    topic_repo_mock = AsyncMock(spec=TopicRepository)
    topic_repo_mock.get.return_value = None
    handler = AssignSubscriptionToTopicHandler(
        user_repository=user_repo_mock,
        subscription_repository=subs_repo_mock,
        topic_repository=topic_repo_mock)

    with pytest.raises(TopicNotFoundError):
        await handler.handle(user_id, subscription_id, topic_id)


@pytest.mark.asyncio()
async def test_assign_subscription_to_topic_handler_topic_does_not_belong_to_user_raises_an_error() -> None:
    user_id = UUID("b9534313-5dbf-4596-9493-779b55ead651")
    subscription_id = UUID("942ad011-362c-4b12-accb-a5c8f273e8db")
    topic_id = UUID("9b3020f8-6f72-4a78-bff6-c315e36808de")

    user_repo_mock = AsyncMock(spec=UserRepository)
    user_repo_mock.get.return_value = mock_user(uuid=user_id, subscribed_to=[subscription_id])
    subs_repo_mock = MagicMock()
    subs_repo_mock.get.return_value = mock_sub(uuid=subscription_id)
    topic_repo_mock = AsyncMock(spec=TopicRepository)
    topic_repo_mock.get.return_value = Topic.new(
        uuid=topic_id,
        name="Topic 1",
        user_id=UUID("9b3020f8-6f72-4a78-bff6-c315e36808de"),
    )
    handler = AssignSubscriptionToTopicHandler(
        user_repository=user_repo_mock,
        subscription_repository=subs_repo_mock,
        topic_repository=topic_repo_mock)

    with pytest.raises(TopicNotFoundError):
        await handler.handle(user_id, subscription_id, topic_id)
