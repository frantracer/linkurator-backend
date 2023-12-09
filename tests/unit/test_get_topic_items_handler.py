from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from linkurator_core.domain.common.exceptions import TopicNotFoundError
from linkurator_core.application.items.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.items.item_repository import ItemRepository
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository


def test_get_topic_items_handler() -> None:
    item1 = Item.new(
        uuid=UUID('4c6d9062-613a-4a94-a369-158975883a00'),
        name='Item 1',
        description='Description 1',
        thumbnail=utils.parse_url('http://example.com/thumbnail1.png'),
        url=utils.parse_url('http://example.com/item1.html'),
        subscription_uuid=UUID('bbdc7d52-0c03-4cbe-b924-91e3b8e60957'),
        published_at=datetime(2020, 1, 1, tzinfo=timezone.utc)
    )

    item_repo_mock = MagicMock(spec=ItemRepository)
    item_repo_mock.find_items.return_value = ([item1], 1)
    item_repo_mock.get_user_interactions_by_item_id.return_value = {}

    topic1 = Topic.new(
        uuid=UUID('04d6483c-f24d-4077-a722-a6d6e3dc3d65'),
        name='Topic 1',
        user_id=UUID('98028b50-86c2-4d2f-8787-414f0f470d15'),
        subscription_ids=[UUID('bbdc7d52-0c03-4cbe-b924-91e3b8e60957')]
    )
    topic_repo_mock = MagicMock(spec=TopicRepository)
    topic_repo_mock.get.return_value = topic1

    handler = GetTopicItemsHandler(topic_repo_mock, item_repo_mock)
    items, total_items = handler.handle(
        user_id=UUID('98028b50-86c2-4d2f-8787-414f0f470d15'),
        topic_id=UUID('04d6483c-f24d-4077-a722-a6d6e3dc3d65'),
        created_before=datetime(2020, 1, 1, tzinfo=timezone.utc),
        page_number=0,
        page_size=10
    )

    assert items == [(item1, [])]
    assert total_items == 1


def test_get_topic_items_handler_not_found_topic_raises_exception() -> None:
    item_repo_mock = MagicMock(spec=ItemRepository)
    item_repo_mock.find_items.return_value = ([], 0)
    item_repo_mock.get_user_interactions_by_item_id.return_value = {}

    topic_repo_mock = MagicMock(spec=TopicRepository)
    topic_repo_mock.get.return_value = None

    handler = GetTopicItemsHandler(topic_repo_mock, item_repo_mock)
    with pytest.raises(TopicNotFoundError):
        handler.handle(
            user_id=UUID('98028b50-86c2-4d2f-8787-414f0f470d15'),
            topic_id=UUID('04d6483c-f24d-4077-a722-a6d6e3dc3d65'),
            created_before=datetime(2020, 1, 1, tzinfo=timezone.utc),
            page_number=0,
            page_size=10
        )
