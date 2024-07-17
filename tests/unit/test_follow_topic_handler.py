from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from linkurator_core.application.topics.follow_topic_handler import FollowTopicHandler
from linkurator_core.domain.common.exceptions import CannotFollowOwnedTopicError, TopicNotFoundError
from linkurator_core.domain.common.mock_factory import mock_topic
from linkurator_core.domain.topics.followed_topics_repository import FollowedTopicsRepository
from linkurator_core.domain.topics.topic_repository import TopicRepository


@pytest.mark.asyncio
async def test_follow_topic() -> None:
    user_id = UUID('eb685364-b25a-4c0f-aef4-530c38a5e9ed')
    topic_id = UUID('595074aa-702a-4237-a42c-2f80095822ae')

    followed_topics_repo = AsyncMock(spec=FollowedTopicsRepository)
    topic_repo = MagicMock(spec=TopicRepository)
    handler = FollowTopicHandler(topic_repository=topic_repo,
                                 followed_topics_repository=followed_topics_repo)

    await handler.handle(user_id, topic_id)

    assert followed_topics_repo.follow_topic.await_args_list == [((user_id, topic_id),)]


@pytest.mark.asyncio
async def test_user_cannot_follow_a_topic_that_belongs_to_the_same_user() -> None:
    user_id = UUID('66301437-6b1c-44f0-bcd3-0d34a4ed1d1c')
    topic_id = UUID('c7e25003-3839-49d4-b6a5-6662441bcd29')
    topic = mock_topic(uuid=topic_id, user_uuid=user_id)

    followed_topics_repo = AsyncMock(spec=FollowedTopicsRepository)
    topic_repo = MagicMock(spec=TopicRepository)
    topic_repo.get.return_value = topic

    handler = FollowTopicHandler(topic_repository=topic_repo,
                                 followed_topics_repository=followed_topics_repo)

    with pytest.raises(CannotFollowOwnedTopicError):
        await handler.handle(user_id, topic_id)


@pytest.mark.asyncio
async def test_cannot_follow_non_existent_topic() -> None:
    user_id = UUID('e13c55e6-ff00-4451-8fff-c69ec8b1ba32')
    topic_id = UUID('436e6e05-3d5d-454a-ad1e-409807863d4c')

    followed_topics_repo = AsyncMock(spec=FollowedTopicsRepository)
    topic_repo = MagicMock(spec=TopicRepository)
    topic_repo.get.return_value = None

    handler = FollowTopicHandler(topic_repository=topic_repo,
                                 followed_topics_repository=followed_topics_repo)

    with pytest.raises(TopicNotFoundError):
        await handler.handle(user_id, topic_id)
