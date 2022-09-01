from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from linkurator_core.application.delete_subscription_items_handler import DeleteSubscriptionItemsHandler
from linkurator_core.common import utils
from linkurator_core.domain.item import Item
from linkurator_core.domain.item_repository import ItemRepository
from linkurator_core.domain.subscription import Subscription
from linkurator_core.domain.subscription_repository import SubscriptionRepository
from linkurator_core.domain.user import User
from linkurator_core.domain.user_repository import UserRepository


def test_delete_subscription_items_handler():
    user_repo_mock = MagicMock(spec=UserRepository)
    user_repo_mock.get.return_value = User.new(
        uuid=UUID('1ae708ad-0cf8-4212-9bb7-a7aeb6440546'),
        first_name='John',
        last_name='Doe',
        email='john@doe.com',
        avatar_url=utils.parse_url('https://avatars0.githubusercontent.com/u/1234?v=4'),
        locale='en',
        google_refresh_token=None,
        is_admin=True)

    subscription_repo_mock = MagicMock(spec=SubscriptionRepository)
    subscription_repo_mock.update.return_value = None
    subscription_repo_mock.get.return_value = Subscription.new(
        uuid=UUID('0a46b804-a370-480b-b64e-c2079aaaa64b'),
        name='Subscription 1',
        provider='rss',
        url=utils.parse_url('https://www.example.com/rss.xml'),
        thumbnail=utils.parse_url('https://www.example.com/thumbnail.png'),
        external_data=None)

    item_repo_mock = MagicMock(spec=ItemRepository)
    item_repo_mock.get_by_subscription_id.return_value = [
        Item.new(uuid=UUID('1ae708ad-0cf8-4212-9bb7-a7aeb6440546'),
                 name='Item 1',
                 url=utils.parse_url('https://www.example.com/item1.html'),
                 thumbnail=utils.parse_url('https://www.example.com/item1.png'),
                 subscription_uuid=UUID('1ae708ad-0cf8-4212-9bb7-a7aeb6440546'),
                 description='Item 1 description',
                 published_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
    ]

    handler = DeleteSubscriptionItemsHandler(
        user_repository=user_repo_mock,
        subscription_repository=subscription_repo_mock,
        item_repository=item_repo_mock)

    handler.handle(
        user_id=UUID('1ae708ad-0cf8-4212-9bb7-a7aeb6440546'),
        subscription_id=UUID('0a46b804-a370-480b-b64e-c2079aaaa64b'))

    assert user_repo_mock.get.called
    assert subscription_repo_mock.get.called
    assert item_repo_mock.get_by_subscription_id.called


def test_user_requires_to_be_admin_to_delete_subscription_items():
    user_repo_mock = MagicMock(spec=UserRepository)
    user_repo_mock.get.return_value = User.new(
        uuid=UUID('f12c465f-4aa3-4e1f-ba04-389791080c6a'),
        first_name='John',
        last_name='Doe',
        email='john@doe.com',
        avatar_url=utils.parse_url('https://avatars0.githubusercontent.com/u/1234?v=4'),
        locale='en',
        google_refresh_token=None,
        is_admin=False)

    subscription_repo_mock = MagicMock(spec=SubscriptionRepository)
    item_repo_mock = MagicMock(spec=ItemRepository)

    handler = DeleteSubscriptionItemsHandler(
        user_repository=user_repo_mock,
        subscription_repository=subscription_repo_mock,
        item_repository=item_repo_mock)

    with pytest.raises(PermissionError):
        handler.handle(
            user_id=UUID('f12c465f-4aa3-4e1f-ba04-389791080c6a'),
            subscription_id=UUID('0a46b804-a370-480b-b64e-c2079aaaa64b'))
