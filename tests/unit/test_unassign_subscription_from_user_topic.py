from copy import copy
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from linkurator_core.application.exceptions import TopicNotFoundError
from linkurator_core.application.unassign_subscription_from_user_topic_handler \
    import UnassignSubscriptionFromUserTopicHandler
from linkurator_core.domain.topic import Topic


def test_unassign_subscription_from_user_topic_handler():
    user_id = UUID('ba591aa7-b216-4874-8742-e83768192d05')
    subscription_id = UUID('2f84755f-58fb-4dfa-9246-b0567fa95bd4')
    topic_id = UUID('b1ae60e2-5cb3-4914-8b8a-5127e22611f0')

    topic = Topic.new(
        user_id=user_id,
        uuid=topic_id,
        name='Test Topic',
        subscription_ids=[subscription_id]
    )

    topic_repo_mock = MagicMock()
    topic_repo_mock.get.return_value = copy(topic)
    topic_repo_mock.update.return_value = None

    handler = UnassignSubscriptionFromUserTopicHandler(
        topic_repository=topic_repo_mock,
    )

    handler.handle(user_id=user_id, subscription_id=subscription_id, topic_id=topic_id)

    assert topic_repo_mock.get.called_once()
    assert topic_repo_mock.update.called_once()
    updated_topic: Topic = topic_repo_mock.update.call_args[0][0]
    assert subscription_id not in updated_topic.subscriptions_ids


def test_unassign_subscription_from_non_existent_topic_raises_an_exception():
    user_id = UUID('97d12652-241c-4b23-9382-21053f66d2b2')
    subscription_id = UUID('5543fc75-2c64-43b6-8dc1-22d68fffee94')
    topic_id = UUID('2642a2b7-0d9d-4b68-8b13-c7dc8370d33e')

    topic_repo_mock = MagicMock()
    topic_repo_mock.get.return_value = None

    handler = UnassignSubscriptionFromUserTopicHandler(
        topic_repository=topic_repo_mock,
    )

    with pytest.raises(TopicNotFoundError):
        handler.handle(user_id=user_id, subscription_id=subscription_id, topic_id=topic_id)


def test_unassign_subscription_from_a_different_user_topic_raises_an_exception():
    user_id = UUID('fab3941a-7ea3-467b-9038-a92a6f2455ec')
    subscription_id = UUID('61d53cfe-cae2-429e-8bb2-a2d676e24eba')
    topic_id = UUID('136105fc-f2ac-486f-bc9f-784092275f93')

    topic = Topic.new(
        user_id=UUID('eb490e85-7878-4d22-aa0c-0adb49b4a9a8'),
        uuid=topic_id,
        name='Test Topic',
        subscription_ids=[subscription_id]
    )

    topic_repo_mock = MagicMock()
    topic_repo_mock.get.return_value = copy(topic)
    topic_repo_mock.update.return_value = None

    handler = UnassignSubscriptionFromUserTopicHandler(
        topic_repository=topic_repo_mock,
    )

    with pytest.raises(TopicNotFoundError):
        handler.handle(user_id=user_id, subscription_id=subscription_id, topic_id=topic_id)


def test_unassign_non_existent_subscription_from_user_topic_does_nothing():
    user_id = UUID('1165fd68-8172-4c1b-9d07-1de26d5f20dc')
    subscription_id = UUID('3b8bb357-c56a-4fae-bd64-74d32b3e1d37')
    topic_id = UUID('417ae6ca-df0b-4342-a855-dd3f65df2da1')

    topic = Topic.new(
        user_id=user_id,
        uuid=topic_id,
        name='Test Topic',
        subscription_ids=[]
    )

    topic_repo_mock = MagicMock()
    topic_repo_mock.get.return_value = copy(topic)
    topic_repo_mock.update.return_value = None

    handler = UnassignSubscriptionFromUserTopicHandler(
        topic_repository=topic_repo_mock,
    )

    handler.handle(user_id=user_id, subscription_id=subscription_id, topic_id=topic_id)

    assert topic_repo_mock.get.called_once()
    assert topic_repo_mock.update.called_once()
    updated_topic: Topic = topic_repo_mock.update.call_args[0][0]
    assert updated_topic == topic
