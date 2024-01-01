from datetime import datetime, timezone
from ipaddress import IPv4Address
from unittest import mock
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from linkurator_core.domain.common import utils
from linkurator_core.domain.common.mock_factory import mock_item
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import ItemFilterCriteria
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBItem, MongoDBItemRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


@pytest.fixture(name="item_repo", scope="session")
def fixture_item_repo(db_name: str) -> MongoDBItemRepository:
    return MongoDBItemRepository(IPv4Address('127.0.0.1'), 27017, db_name, "develop", "develop")


def test_exception_is_raised_if_items_collection_is_not_created() -> None:
    non_existent_db_name = f"test-{uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        MongoDBItemRepository(IPv4Address('127.0.0.1'), 27017, non_existent_db_name, "develop", "develop")


def test_get_item(item_repo: MongoDBItemRepository) -> None:
    item = Item(name="test",
                description="some description with emojis 🙂",
                uuid=UUID("9cedfb45-70fb-4283-bfee-993941b05b53"),
                subscription_uuid=UUID("6ae3792e-6427-4b61-bdc1-66cc9c61fe29"),
                url=utils.parse_url('https://test.com'),
                thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
                published_at=datetime.now(tz=timezone.utc),
                version=2,
                duration=10,
                provider=ItemProvider.YOUTUBE)
    item_repo.upsert_bulk([item])
    the_item = item_repo.get(item.uuid)

    assert the_item is not None
    assert the_item == item


def test_get_item_that_does_not_exist(item_repo: MongoDBItemRepository) -> None:
    the_item = item_repo.get(UUID("88aa425f-28d9-4a25-a87a-8c877cac772d"))

    assert the_item is None


def test_get_item_with_invalid_format_raises_an_exception(item_repo: MongoDBItemRepository) -> None:
    item_dict = MongoDBItem(
        uuid=UUID("67a06616-e127-4bf0-bcc0-faa221d554c5"),
        subscription_uuid=UUID("9753d304-3a43-414e-a5cd-496672b27c34"),
        name="test",
        description="",
        url='https://test.com',
        thumbnail='https://test.com/thumbnail.png',
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
        published_at=datetime.fromtimestamp(0, tz=timezone.utc)
    ).model_dump()
    item_dict['uuid'] = 'invalid_uuid'
    item_collection_mock = MagicMock()
    item_collection_mock.find_one = MagicMock(return_value=item_dict)
    with mock.patch.object(MongoDBItemRepository, '_item_collection',
                           return_value=item_collection_mock):
        with pytest.raises(ValueError):
            item_repo.get(UUID("756b6b0d-5f54-4099-ae7e-c900666f0a0d"))


def test_delete_item(item_repo: MongoDBItemRepository) -> None:
    item = mock_item(item_uuid=UUID("4bf64498-239e-4bcb-a5a1-b84a7708ad01"))

    item_repo.upsert_bulk([item])
    the_item = item_repo.get(item.uuid)
    assert the_item is not None

    item_repo.delete(item.uuid)
    deleted_item = item_repo.get(item.uuid)
    assert deleted_item is None


def test_create_and_update_items(item_repo: MongoDBItemRepository) -> None:
    item1 = mock_item(item_uuid=UUID("72ab4421-f2b6-499a-bbf1-5105f2ed549b"))
    item2 = mock_item(item_uuid=UUID("a5a908e6-aa2c-4240-9a6d-d4340d38b8fc"))

    item_repo.upsert_bulk([item1, item2])

    item1_found = item_repo.get(item1.uuid)
    item2_found = item_repo.get(item2.uuid)

    assert item1_found == item1
    assert item2_found == item2

    item1_updated = Item(
        uuid=item1.uuid,
        subscription_uuid=item1.subscription_uuid,
        name="updated name",
        description="updated description",
        url=utils.parse_url('https://updated.com'),
        thumbnail=utils.parse_url('https://updated.com/thumbnail.png'),
        created_at=item1.created_at,
        updated_at=datetime.now(tz=timezone.utc),
        published_at=item1.published_at,
        version=2,
        duration=10,
        provider=ItemProvider.YOUTUBE
    )
    item2_updated = Item(
        uuid=item2.uuid,
        subscription_uuid=item2.subscription_uuid,
        name="updated name",
        description="updated description",
        url=utils.parse_url('https://updated.com'),
        thumbnail=utils.parse_url('https://updated.com/thumbnail.png'),
        created_at=item2.created_at,
        updated_at=datetime.now(tz=timezone.utc),
        published_at=item2.published_at,
        version=2,
        duration=10,
        provider=ItemProvider.YOUTUBE
    )

    item_repo.upsert_bulk([item1_updated, item2_updated])

    item1_found = item_repo.get(item1.uuid)
    item2_found = item_repo.get(item2.uuid)

    assert item1_found == item1_updated
    assert item2_found == item2_updated


def test_create_and_update_items_with_no_items(item_repo: MongoDBItemRepository) -> None:
    item_repo.upsert_bulk([])
    assert True


def test_get_items_by_subscription_uuid(item_repo: MongoDBItemRepository) -> None:
    subscription_uuid_1 = UUID("49e16717-3b41-4e1b-a2d8-8fccf1b6c184")
    subscription_uuid_2 = UUID("d3e22c40-c767-468b-8a61-cc61bcfd55ec")
    subscription_uuid_3 = UUID("9753d304-3a43-414e-a5cd-496672b27c34")

    item1 = mock_item(item_uuid=UUID("6469596f-5128-4c12-87f1-9b7b462517f3"), sub_uuid=subscription_uuid_1)
    item2 = mock_item(item_uuid=UUID("2dcc5c6b-3d95-421d-a9cf-81ac475cee4c"), sub_uuid=subscription_uuid_1)
    item3 = mock_item(item_uuid=UUID("199f25cc-ff99-4a5c-9329-edebc3fdc0e5"), sub_uuid=subscription_uuid_2)

    item_repo.upsert_bulk([item1, item2, item3])

    items_from_sub1 = item_repo.find_items(
        criteria=ItemFilterCriteria(subscription_ids=[subscription_uuid_1]), page_number=0, limit=10)
    items_from_sub2 = item_repo.find_items(
        criteria=ItemFilterCriteria(subscription_ids=[subscription_uuid_2]), page_number=0, limit=10)
    items_from_sub3 = item_repo.find_items(
        criteria=ItemFilterCriteria(subscription_ids=[subscription_uuid_3]), page_number=0, limit=10)

    assert len(items_from_sub1[0]) == 2
    assert len(items_from_sub2[0]) == 1
    assert len(items_from_sub3[0]) == 0


def test_find_items_by_uuid(item_repo: MongoDBItemRepository) -> None:
    item1 = mock_item(item_uuid=UUID("cd79132f-ad0a-4206-b118-2c958bc28506"))
    item2 = mock_item(item_uuid=UUID("8e014a74-ddf9-4ad1-a354-22e1c9dd7acc"))

    item_repo.upsert_bulk([item1, item2])

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(item_ids={item1.uuid, uuid4()}), page_number=0, limit=10)

    assert len(found_items) == 1
    assert total_items == 1
    assert found_items[0] == item1

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(item_ids=set()), page_number=0, limit=10)

    assert len(found_items) == 0
    assert total_items == 0


def test_find_items_by_subscription_uuids(item_repo: MongoDBItemRepository) -> None:
    item1 = mock_item(item_uuid=UUID("9559fa81-e968-4d0d-8390-070908f66985"),
                      sub_uuid=UUID("e887b865-8aa2-47a5-a133-a6eb7ba0f957"))
    item2 = mock_item(item_uuid=UUID("16f3a929-82a1-4cee-be30-70861d9266f2"),
                      sub_uuid=UUID("22da439a-b9e0-4837-9b52-12ad15374832"))

    item_repo.upsert_bulk([item1, item2])

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(subscription_ids=[item1.subscription_uuid, uuid4()]), page_number=0, limit=10)

    assert len(found_items) == 1
    assert total_items == 1
    assert found_items[0] == item1

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(subscription_ids=[]), page_number=0, limit=10)

    assert len(found_items) == 0
    assert total_items == 0


def test_find_item_with_same_url(item_repo: MongoDBItemRepository) -> None:
    item1 = mock_item(item_uuid=UUID("8fc4fbca-439c-4c0e-937d-4147ef3b299c"),
                      url='https://item-with-same-url.com')

    item_repo.upsert_bulk([item1])

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(url=utils.parse_url('https://item-with-same-url.com')),
        page_number=0, limit=10)

    assert len(found_items) == 1
    assert total_items == 1
    assert found_items[0].uuid == item1.uuid


def test_find_item_with_different_url_returns_none(item_repo: MongoDBItemRepository) -> None:
    item1 = mock_item(item_uuid=UUID("00fbe982-1c90-4e7a-bf73-4716fa565b3c"),
                      url='https://item-with-same-url.com')

    item_repo.upsert_bulk([item1])

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(url=utils.parse_url('https://item-with-different-url.com')),
        page_number=0, limit=10)

    assert len(found_items) == 0
    assert total_items == 0


def test_find_items_published_after_and_created_before_a_date_are_sorted_by_publish_date(
        item_repo: MongoDBItemRepository) -> None:
    sub_uuid = UUID("480e5b4d-c193-4548-a987-c125d1699d10")
    item1 = mock_item(item_uuid=UUID("72e47bdc-793e-4420-b6b6-f6a415cb1e3c"),
                      sub_uuid=sub_uuid,
                      published_at=datetime(2020, 1, 1, 8, 8, 8, tzinfo=timezone.utc),
                      created_at=datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    item2 = mock_item(item_uuid=UUID("1db7ac48-4388-49a6-94c2-1a28657ec2f9"),
                      sub_uuid=sub_uuid,
                      published_at=datetime(2021, 1, 1, 6, 6, 6, tzinfo=timezone.utc),
                      created_at=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc))
    item3 = mock_item(item_uuid=UUID("a45500be-967a-47fc-93f9-9b7642f51a52"),
                      sub_uuid=sub_uuid,
                      published_at=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
                      created_at=datetime(2023, 2, 2, 0, 0, 0, tzinfo=timezone.utc))
    item4 = mock_item(item_uuid=UUID("0a4c8807-0876-4ee0-82b6-333133bb66ee"),
                      sub_uuid=sub_uuid,
                      published_at=datetime(2020, 1, 1, 8, 8, 9, tzinfo=timezone.utc),
                      created_at=datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc))

    item_repo.upsert_bulk([item1, item2, item3, item4])

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub_uuid],
            published_after=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
            created_before=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc)),
        page_number=0,
        limit=1)

    assert len(found_items) == 1
    assert total_items == 2
    assert found_items[0].uuid == item4.uuid

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub_uuid],
            published_after=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
            created_before=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc)),
        page_number=1,
        limit=1)

    assert len(found_items) == 1
    assert total_items == 2
    assert found_items[0].uuid == item1.uuid

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub_uuid],
            published_after=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
            created_before=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc)),
        page_number=2,
        limit=1)

    assert len(found_items) == 0
    assert total_items == 2


def test_get_items_created_before_a_certain_date(item_repo: MongoDBItemRepository) -> None:
    item_repo.delete_all_items()

    item1 = mock_item(item_uuid=UUID("e1f898c2-bcfb-435a-97c0-9f462f73e95b"),
                      created_at=datetime(2000, 1, 1, 0, 0, 10, tzinfo=timezone.utc),
                      published_at=datetime(2000, 1, 1, 0, 0, 10, tzinfo=timezone.utc))

    item_repo.upsert_bulk([item1])

    found_items, _ = item_repo.find_items(
        criteria=ItemFilterCriteria(created_before=datetime(2000, 1, 1, 0, 0, 11, tzinfo=timezone.utc)),
        page_number=0,
        limit=1)
    assert item1.uuid in [item.uuid for item in found_items]

    found_items, _ = item_repo.find_items(
        criteria=ItemFilterCriteria(created_before=datetime(2000, 1, 1, 0, 0, 10, tzinfo=timezone.utc)),
        page_number=0,
        limit=1)
    assert item1.uuid not in [item.uuid for item in found_items]

    found_items, _ = item_repo.find_items(
        criteria=ItemFilterCriteria(created_before=datetime(2000, 1, 1, 0, 0, 9, tzinfo=timezone.utc)),
        page_number=0,
        limit=1)
    assert item1.uuid not in [item.uuid for item in found_items]


def test_find_items_for_a_subscription_with_text_search_criteria(item_repo: MongoDBItemRepository) -> None:
    sub1_uuid = UUID("b76f981e-083f-4cee-9e5c-9f46f010546f")
    item1 = mock_item(
        name="Football is cool and it is almost free!",
        description="Let's discover where you can play football and how to get a new ball",
        item_uuid=UUID("412ec7ea-b5ba-48aa-b370-771352858795"),
        sub_uuid=sub1_uuid,
    )
    item2 = mock_item(
        name="Videogames are cool",
        item_uuid=UUID("1f63bdf9-5cf5-43e1-a5b1-6e4d97842005"),
        sub_uuid=sub1_uuid,
    )
    item3 = mock_item(
        name="What you should do in your free time?",
        description="Videogames is the answer",
        item_uuid=UUID("0183fd38-501d-442c-ac90-d2baad84f6eb"),
        sub_uuid=sub1_uuid,
    )
    item4 = mock_item(
        name="Are videogames culture?",
        description="Let's find out!",
        item_uuid=UUID("88ec8038-45ec-4d45-bd4b-f1ab01d33fd8"),
        sub_uuid=sub1_uuid,
    )

    item_repo.delete_all_items()
    item_repo.upsert_bulk([item1, item2, item3, item4])

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub1_uuid],
            text="videogames"),
        page_number=0,
        limit=4
    )
    assert len(found_items) == 2
    assert total_items == 2
    assert found_items[0].uuid == item4.uuid
    assert found_items[1].uuid == item2.uuid

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub1_uuid],
            text="cool -videogames"),
        limit=4,
        page_number=0,
    )
    assert len(found_items) == 1
    assert total_items == 1
    assert found_items[0].uuid == item1.uuid

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub1_uuid],
            text="\"free time\""),
        limit=4,
        page_number=0,
    )
    assert len(found_items) == 1
    assert total_items == 1
    assert found_items[0].uuid == item3.uuid

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub1_uuid],
            text="swim"),
        limit=4,
        page_number=0,
    )
    assert len(found_items) == 0
    assert total_items == 0


def test_find_deprecated_items(item_repo: MongoDBItemRepository) -> None:
    item_repo.delete_all_items()

    item1 = mock_item(item_uuid=UUID("656fbb48-7897-4528-ae8b-cc4abc81aec7"), version=1,
                      published_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    item2 = mock_item(item_uuid=UUID("ecb31594-491d-4fa4-b216-e198ab3d5ca2"), version=2,
                      published_at=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc))
    item3 = mock_item(item_uuid=UUID("0e829ca3-4e4c-42f6-960d-0f79b815587d"), version=3,
                      published_at=datetime(2020, 1, 3, 0, 0, 0, tzinfo=timezone.utc))
    item4 = mock_item(item_uuid=UUID("6f9f5f02-eb83-4358-8794-ef452dea2f2f"), version=1,
                      published_at=datetime(2020, 1, 4, 0, 0, 0, tzinfo=timezone.utc))

    item_repo.upsert_bulk([item1, item2, item3, item4])

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            last_version=2,
            provider=ItemProvider.YOUTUBE,
        ),
        limit=4,
        page_number=0)
    assert len(found_items) == 2
    assert total_items == 2
    assert {item.uuid for item in found_items} == {item1.uuid, item4.uuid}

    found_items, total_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            last_version=3,
            provider=ItemProvider.YOUTUBE,
        ),
        limit=1,
        page_number=0)
    assert len(found_items) == 1
    assert total_items == 3
    assert found_items[0].uuid == item4.uuid
