import datetime
from ipaddress import IPv4Address
from unittest import mock
from unittest.mock import MagicMock
import uuid

from math import floor
import pytest

from linkurator_core.common import utils
from linkurator_core.domain.item import Item
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBItem, MongoDBItemRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


@pytest.fixture(name="item_repo", scope="session")
def fixture_item_repo(db_name) -> MongoDBItemRepository:
    return MongoDBItemRepository(IPv4Address('127.0.0.1'), 27017, db_name, "develop", "develop")


def test_exception_is_raised_if_items_collection_is_not_created():
    non_existent_db_name = f"test-{uuid.uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        MongoDBItemRepository(IPv4Address('127.0.0.1'), 27017, non_existent_db_name, "develop", "develop")


def test_get_item(item_repo: MongoDBItemRepository):
    item = Item(name="test", uuid=uuid.UUID("9cedfb45-70fb-4283-bfee-993941b05b53"),
                subscription_uuid=uuid.UUID("6ae3792e-6427-4b61-bdc1-66cc9c61fe29"),
                url=utils.parse_url('https://test.com'),
                thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    item_repo.add(item)
    the_item = item_repo.get(item.uuid)

    assert the_item is not None
    assert the_item.name == item.name
    assert the_item.uuid == item.uuid
    assert the_item.url == item.url
    assert the_item.thumbnail == item.thumbnail
    assert int(the_item.created_at.timestamp() * 100) == floor(item.created_at.timestamp() * 100)
    assert int(the_item.updated_at.timestamp() * 100) == floor(item.updated_at.timestamp() * 100)


def test_get_item_that_does_not_exist(item_repo: MongoDBItemRepository):
    the_item = item_repo.get(uuid.UUID("88aa425f-28d9-4a25-a87a-8c877cac772d"))

    assert the_item is None


def test_get_item_with_invalid_format_raises_an_exception(item_repo: MongoDBItemRepository):
    item_dict = dict(MongoDBItem(uuid=uuid.UUID("67a06616-e127-4bf0-bcc0-faa221d554c5"),
                                 subscription_uuid=uuid.UUID("9753d304-3a43-414e-a5cd-496672b27c34"),
                                 name="test", url=utils.parse_url('https://test.com'),
                                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                                 created_at=datetime.datetime.now(), updated_at=datetime.datetime.now()))
    item_dict['uuid'] = 'invalid_uuid'
    item_collection_mock = MagicMock()
    item_collection_mock.find_one = MagicMock(return_value=item_dict)
    with mock.patch.object(MongoDBItemRepository, '_item_collection',
                           return_value=item_collection_mock):
        with pytest.raises(ValueError):
            item_repo.get(uuid.UUID("756b6b0d-5f54-4099-ae7e-c900666f0a0d"))


def test_delete_item(item_repo: MongoDBItemRepository):
    item = Item(name="test", uuid=uuid.UUID("4bf64498-239e-4bcb-a5a1-b84a7708ad01"),
                subscription_uuid=uuid.UUID("d1dc868b-598c-4547-92d6-011e9b7e38e6"),
                url=utils.parse_url('https://test.com'),
                thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    item_repo.add(item)
    the_item = item_repo.get(item.uuid)
    assert the_item is not None

    item_repo.delete(item.uuid)
    deleted_item = item_repo.get(item.uuid)
    assert deleted_item is None


def test_get_items_by_subscription_uuid(item_repo: MongoDBItemRepository):
    subscription_uuid_1 = uuid.UUID("49e16717-3b41-4e1b-a2d8-8fccf1b6c184")
    subscription_uuid_2 = uuid.UUID("d3e22c40-c767-468b-8a61-cc61bcfd55ec")
    subscription_uuid_3 = uuid.UUID("9753d304-3a43-414e-a5cd-496672b27c34")

    item1 = Item(name="item1", uuid=uuid.UUID("6469596f-5128-4c12-87f1-9b7b462517f3"),
                 subscription_uuid=subscription_uuid_1,
                 url=utils.parse_url('https://test.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    item2 = Item(name="item2", uuid=uuid.UUID("2dcc5c6b-3d95-421d-a9cf-81ac475cee4c"),
                 subscription_uuid=subscription_uuid_1,
                 url=utils.parse_url('https://test.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    item3 = Item(name="item3", uuid=uuid.UUID("2f7fa436-e1db-4ac7-bcce-6299c246e39f"),
                 subscription_uuid=subscription_uuid_2,
                 url=utils.parse_url('https://test.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
    item_repo.add(item1)
    item_repo.add(item2)
    item_repo.add(item3)

    items_from_sub1 = item_repo.get_by_subscription_id(subscription_uuid_1)
    items_from_sub2 = item_repo.get_by_subscription_id(subscription_uuid_2)
    items_from_sub3 = item_repo.get_by_subscription_id(subscription_uuid_3)

    assert len(items_from_sub1) == 2
    assert len(items_from_sub2) == 1
    assert len(items_from_sub3) == 0
