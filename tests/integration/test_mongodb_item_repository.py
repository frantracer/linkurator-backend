import uuid
from datetime import datetime, timezone
from ipaddress import IPv4Address
from unittest import mock
from unittest.mock import MagicMock

from math import floor
import pytest

from linkurator_core.domain.common import utils
from linkurator_core.domain.items.item import Item
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
    item = Item(name="test",
                description="some description with emojis 🙂",
                uuid=uuid.UUID("9cedfb45-70fb-4283-bfee-993941b05b53"),
                subscription_uuid=uuid.UUID("6ae3792e-6427-4b61-bdc1-66cc9c61fe29"),
                url=utils.parse_url('https://test.com'),
                thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
                published_at=datetime.now(tz=timezone.utc))
    item_repo.add(item)
    the_item = item_repo.get(item.uuid)

    assert the_item is not None
    assert the_item.name == item.name
    assert the_item.description == item.description
    assert the_item.uuid == item.uuid
    assert the_item.url == item.url
    assert the_item.thumbnail == item.thumbnail
    assert int(the_item.created_at.timestamp() * 100) == floor(item.created_at.timestamp() * 100)
    assert int(the_item.updated_at.timestamp() * 100) == floor(item.updated_at.timestamp() * 100)
    assert int(the_item.published_at.timestamp() * 100) == floor(item.published_at.timestamp() * 100)


def test_get_item_that_does_not_exist(item_repo: MongoDBItemRepository):
    the_item = item_repo.get(uuid.UUID("88aa425f-28d9-4a25-a87a-8c877cac772d"))

    assert the_item is None


def test_get_item_with_invalid_format_raises_an_exception(item_repo: MongoDBItemRepository):
    item_dict = dict(MongoDBItem(
        uuid=uuid.UUID("67a06616-e127-4bf0-bcc0-faa221d554c5"),
        subscription_uuid=uuid.UUID("9753d304-3a43-414e-a5cd-496672b27c34"),
        name="test",
        description="",
        url=utils.parse_url('https://test.com'),
        thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
        published_at=datetime.fromtimestamp(0, tz=timezone.utc)))
    item_dict['uuid'] = 'invalid_uuid'
    item_collection_mock = MagicMock()
    item_collection_mock.find_one = MagicMock(return_value=item_dict)
    with mock.patch.object(MongoDBItemRepository, '_item_collection',
                           return_value=item_collection_mock):
        with pytest.raises(ValueError):
            item_repo.get(uuid.UUID("756b6b0d-5f54-4099-ae7e-c900666f0a0d"))


def test_delete_item(item_repo: MongoDBItemRepository):
    item = Item(name="test",
                description="",
                uuid=uuid.UUID("4bf64498-239e-4bcb-a5a1-b84a7708ad01"),
                subscription_uuid=uuid.UUID("d1dc868b-598c-4547-92d6-011e9b7e38e6"),
                url=utils.parse_url('https://test.com'),
                thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
                published_at=datetime.fromtimestamp(0, tz=timezone.utc))
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

    item1 = Item(name="item1",
                 description="",
                 uuid=uuid.UUID("6469596f-5128-4c12-87f1-9b7b462517f3"),
                 subscription_uuid=subscription_uuid_1,
                 url=utils.parse_url('https://test.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 created_at=datetime.now(tz=timezone.utc),
                 updated_at=datetime.now(tz=timezone.utc),
                 published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    item2 = Item(name="item2",
                 description="",
                 uuid=uuid.UUID("2dcc5c6b-3d95-421d-a9cf-81ac475cee4c"),
                 subscription_uuid=subscription_uuid_1,
                 url=utils.parse_url('https://test.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 created_at=datetime.now(tz=timezone.utc),
                 updated_at=datetime.now(tz=timezone.utc),
                 published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    item3 = Item(name="item3",
                 description="",
                 uuid=uuid.UUID("2f7fa436-e1db-4ac7-bcce-6299c246e39f"),
                 subscription_uuid=subscription_uuid_2,
                 url=utils.parse_url('https://test.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 created_at=datetime.now(tz=timezone.utc),
                 updated_at=datetime.now(tz=timezone.utc),
                 published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    item_repo.add(item1)
    item_repo.add(item2)
    item_repo.add(item3)

    items_from_sub1 = item_repo.get_by_subscription_id(subscription_uuid_1)
    items_from_sub2 = item_repo.get_by_subscription_id(subscription_uuid_2)
    items_from_sub3 = item_repo.get_by_subscription_id(subscription_uuid_3)

    assert len(items_from_sub1) == 2
    assert len(items_from_sub2) == 1
    assert len(items_from_sub3) == 0


def test_find_item_with_same_url(item_repo: MongoDBItemRepository):
    item1 = Item.new(name="item1",
                     description="",
                     uuid=uuid.UUID("8fc4fbca-439c-4c0e-937d-4147ef3b299c"),
                     subscription_uuid=uuid.UUID("5113d45e-04a5-4f82-9eba-5b7ebb87ab79"),
                     url=utils.parse_url('https://item-with-same-url.com'),
                     thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                     published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    item2 = Item.new(name="item2",
                     description="",
                     uuid=uuid.UUID("fe5542fa-276e-461f-aa20-d52b1b3ce4e1"),
                     subscription_uuid=uuid.UUID("5113d45e-04a5-4f82-9eba-5b7ebb87ab79"),
                     url=utils.parse_url('https://item-with-same-url.com'),
                     thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                     published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    item_repo.add(item1)

    found_item = item_repo.find(item2)
    assert found_item is not None
    assert found_item.uuid == item1.uuid


def test_find_item_with_different_url_returns_none(item_repo: MongoDBItemRepository):
    item1 = Item.new(name="item1",
                     description="",
                     uuid=uuid.UUID("40f3edbf-66a4-4074-9f26-53a7a9832fe7"),
                     subscription_uuid=uuid.UUID("5113d45e-04a5-4f82-9eba-5b7ebb87ab79"),
                     url=utils.parse_url('https://40f3edbf.com'),
                     thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                     published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    item2 = Item.new(name="item2",
                     description="",
                     uuid=uuid.UUID("b996a1fb-91db-44de-9c4f-c111c056d299"),
                     subscription_uuid=uuid.UUID("5113d45e-04a5-4f82-9eba-5b7ebb87ab79"),
                     url=utils.parse_url('https://b996a1fb.com'),
                     thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                     published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    item_repo.add(item1)

    found_item = item_repo.find(item2)
    assert found_item is None


def test_find_items_published_after_and_created_before_a_date_are_sorted_by_publish_date(
        item_repo: MongoDBItemRepository):
    item1 = Item(name="item1",
                 description="",
                 uuid=uuid.UUID("72e47bdc-793e-4420-b6b6-f6a415cb1e3c"),
                 subscription_uuid=uuid.UUID("480e5b4d-c193-4548-a987-c125d1699d10"),
                 url=utils.parse_url('https://72e47bdc.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 published_at=datetime(2020, 1, 1, 8, 8, 8, tzinfo=timezone.utc),
                 created_at=datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                 updated_at=datetime.fromtimestamp(0, tz=timezone.utc))
    item2 = Item(name="item2",
                 description="",
                 uuid=uuid.UUID("1db7ac48-4388-49a6-94c2-1a28657ec2f9"),
                 subscription_uuid=uuid.UUID("480e5b4d-c193-4548-a987-c125d1699d10"),
                 url=utils.parse_url('https://1db7ac48.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 published_at=datetime(2021, 1, 1, 6, 6, 6, tzinfo=timezone.utc),
                 created_at=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
                 updated_at=datetime.fromtimestamp(0, tz=timezone.utc))
    item3 = Item(name="item3",
                 description="",
                 uuid=uuid.UUID("a45500be-967a-47fc-93f9-9b7642f51a52"),
                 subscription_uuid=uuid.UUID("480e5b4d-c193-4548-a987-c125d1699d10"),
                 url=utils.parse_url('https://a45500be.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 published_at=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
                 created_at=datetime(2023, 2, 2, 0, 0, 0, tzinfo=timezone.utc),
                 updated_at=datetime.fromtimestamp(0, tz=timezone.utc))
    item4 = Item(name="item4",
                 description="",
                 uuid=uuid.UUID("0a4c8807-0876-4ee0-82b6-333133bb66ee"),
                 subscription_uuid=uuid.UUID("480e5b4d-c193-4548-a987-c125d1699d10"),
                 url=utils.parse_url('https://0a4c8807.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 published_at=datetime(2020, 1, 1, 8, 8, 9, tzinfo=timezone.utc),
                 created_at=datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                 updated_at=datetime.fromtimestamp(0, tz=timezone.utc))
    item_repo.add(item1)
    item_repo.add(item2)
    item_repo.add(item3)
    item_repo.add(item4)

    found_items, total_items = item_repo.find_sorted_by_publish_date(
        sub_ids=[uuid.UUID("480e5b4d-c193-4548-a987-c125d1699d10")],
        published_after=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        created_before=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        page_number=0,
        max_results=1)

    assert len(found_items) == 1
    assert total_items == 2
    assert found_items[0].uuid == item4.uuid

    found_items, total_items = item_repo.find_sorted_by_publish_date(
        sub_ids=[uuid.UUID("480e5b4d-c193-4548-a987-c125d1699d10")],
        published_after=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        created_before=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        page_number=1,
        max_results=1)

    assert len(found_items) == 1
    assert total_items == 2
    assert found_items[0].uuid == item1.uuid

    found_items, total_items = item_repo.find_sorted_by_publish_date(
        sub_ids=[uuid.UUID("480e5b4d-c193-4548-a987-c125d1699d10")],
        published_after=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
        created_before=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        page_number=2,
        max_results=1)

    assert len(found_items) == 0
    assert total_items == 2


def test_add_two_items_in_bulk(item_repo: MongoDBItemRepository):
    item1 = Item(name="item1",
                 description="",
                 uuid=uuid.UUID("1875c0e6-5ad4-40c4-b68a-b5b47c05d675"),
                 subscription_uuid=uuid.UUID("480e5b4d-c193-4548-a987-c125d1699d10"),
                 url=utils.parse_url('https://72e47bdc.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 published_at=datetime(2020, 1, 1, 8, 8, 8, tzinfo=timezone.utc),
                 created_at=datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                 updated_at=datetime.fromtimestamp(0, tz=timezone.utc))
    item2 = Item(name="item2",
                 description="",
                 uuid=uuid.UUID("765a121c-8e67-45da-b5e4-1ced03af68c4"),
                 subscription_uuid=uuid.UUID("480e5b4d-c193-4548-a987-c125d1699d10"),
                 url=utils.parse_url('https://1db7ac48.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 published_at=datetime(2021, 1, 1, 6, 6, 6, tzinfo=timezone.utc),
                 created_at=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
                 updated_at=datetime.fromtimestamp(0, tz=timezone.utc))

    item_repo.add_bulk([item1, item2])

    item1_found = item_repo.get(item1.uuid)
    item2_found = item_repo.get(item2.uuid)

    assert item1_found == item1
    assert item2_found == item2


def test_add_empty_list_of_items_raises_no_error(item_repo: MongoDBItemRepository):
    item_repo.add_bulk([])


def test_get_items_created_before_a_certain_date(item_repo: MongoDBItemRepository):
    item1 = Item(name="item1",
                 description="",
                 uuid=uuid.UUID("e1f898c2-bcfb-435a-97c0-9f462f73e95b"),
                 subscription_uuid=uuid.UUID("480e5b4d-c193-4548-a987-c125d1699d10"),
                 url=utils.parse_url('https://72e47bdc.com'),
                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                 published_at=datetime(2000, 1, 1, 0, 0, 10, tzinfo=timezone.utc),
                 created_at=datetime(2000, 1, 1, 0, 0, 10, tzinfo=timezone.utc),
                 updated_at=datetime(2000, 1, 1, 0, 0, 10, tzinfo=timezone.utc))

    item_repo.add(item1)

    found_items = item_repo.get_items_created_before(date=datetime(2000, 1, 1, 0, 0, 11, tzinfo=timezone.utc), limit=1)
    assert item1.uuid in [item.uuid for item in found_items]

    found_items = item_repo.get_items_created_before(date=datetime(2000, 1, 1, 0, 0, 10, tzinfo=timezone.utc), limit=1)
    assert item1.uuid not in [item.uuid for item in found_items]

    found_items = item_repo.get_items_created_before(date=datetime(2000, 1, 1, 0, 0, 9, tzinfo=timezone.utc), limit=1)
    assert item1.uuid not in [item.uuid for item in found_items]

    found_items = item_repo.get_items_created_before(date=datetime(2000, 1, 1, 0, 0, 11, tzinfo=timezone.utc), limit=0)
    assert len(found_items) == 0
