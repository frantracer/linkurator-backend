from unittest.mock import MagicMock
from uuid import UUID

import pytest

from linkurator_core.domain.common.exceptions import UserNotFoundError
from linkurator_core.application.topics.get_user_topics_handler import GetUserTopicsHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.users.user import User


def test_get_user_topics_handler():
    user_repo_mock = MagicMock()
    user = User.new(
        uuid=UUID('ac32894a-d568-4def-9cfd-08779845018f'),
        first_name='John',
        last_name='Doe',
        email='test@email.com',
        locale='en',
        avatar_url=utils.parse_url('https://example.com/avatar.png'),
        google_refresh_token='refresh_token'
    )
    user_repo_mock.get.return_value = user
    topic_repo_mock = MagicMock()
    topic1 = Topic.new(
        uuid=UUID('ac32894a-d568-4def-9cfd-08779845018f'),
        name='Topic 1',
        user_id=user.uuid
    )
    topic_repo_mock.get_by_user_id.return_value = [topic1]

    handler = GetUserTopicsHandler(user_repo_mock, topic_repo_mock)

    topics = handler.handle(user.uuid)

    assert len(topics) == 1
    assert topics[0] == topic1


def test_get_user_topics_handler_user_not_found():
    user_repo_mock = MagicMock()
    user_repo_mock.get.return_value = None

    topic_repo_mock = MagicMock()

    handler = GetUserTopicsHandler(user_repo_mock, topic_repo_mock)

    with pytest.raises(UserNotFoundError):
        handler.handle(UUID('7b444729-aaea-4f0c-8fa3-ef307e164a80'))
