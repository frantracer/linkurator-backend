from unittest.mock import MagicMock, call
from uuid import UUID

import pytest

from linkurator_core.application.items.delete_subscription_items_handler import DeleteSubscriptionItemsHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError
from linkurator_core.domain.common.mock_factory import mock_item, mock_sub, mock_user
from linkurator_core.domain.items.item_repository import ItemRepository
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository


def test_delete_subscription_items_handler():
    user_repo_mock = MagicMock(spec=UserRepository)
    user = mock_user(uuid=UUID('1ae708ad-0cf8-4212-9bb7-a7aeb6440546'), is_admin=True)
    user_repo_mock.get.return_value = user

    subscription_repo_mock = MagicMock(spec=SubscriptionRepository)
    subscription_repo_mock.update.return_value = None
    sub1 = mock_sub(uuid=UUID('0a46b804-a370-480b-b64e-c2079aaaa64b'))
    subscription_repo_mock.get.return_value = sub1

    item_repo_mock = MagicMock(spec=ItemRepository)
    item1 = mock_item(item_uuid=UUID('1ae708ad-0cf8-4212-9bb7-a7aeb6440546'),
                      sub_uuid=sub1.uuid)
    item2 = mock_item(item_uuid=UUID('6e2013d9-d608-4b5b-848a-2b0278e8364b'),
                      sub_uuid=sub1.uuid)

    # mock find_items to be called twice, one with item1 and another with item2
    item_repo_mock.find_items.side_effect = [
        ([item1], 2),
        ([item2], 2),
    ]
    handler = DeleteSubscriptionItemsHandler(
        user_repository=user_repo_mock,
        subscription_repository=subscription_repo_mock,
        item_repository=item_repo_mock)

    handler.handle(
        user_id=UUID('1ae708ad-0cf8-4212-9bb7-a7aeb6440546'),
        subscription_id=UUID('0a46b804-a370-480b-b64e-c2079aaaa64b'))

    assert user_repo_mock.get.call_count == 1
    assert subscription_repo_mock.get.call_count == 1
    assert item_repo_mock.find_items.call_count == 2
    assert item_repo_mock.delete.call_count == 2
    assert item_repo_mock.delete.call_args_list == [call(item1.uuid), call(item2.uuid)]
    assert subscription_repo_mock.update.call_count == 1


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


def test_delete_items_handler_raises_exception_if_subscription_does_not_exist():
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
    subscription_repo_mock.get.return_value = None

    item_repo_mock = MagicMock(spec=ItemRepository)

    handler = DeleteSubscriptionItemsHandler(
        user_repository=user_repo_mock,
        subscription_repository=subscription_repo_mock,
        item_repository=item_repo_mock)

    with pytest.raises(SubscriptionNotFoundError):
        handler.handle(
            user_id=UUID('1ae708ad-0cf8-4212-9bb7-a7aeb6440546'),
            subscription_id=UUID('0a46b804-a370-480b-b64e-c2079aaaa64b'))
