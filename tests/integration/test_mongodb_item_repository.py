from datetime import datetime, timezone
from ipaddress import IPv4Address
from unittest import mock
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from linkurator_core.domain.common import utils
from linkurator_core.domain.common.mock_factory import mock_item
from linkurator_core.domain.items.interaction import Interaction, InteractionType
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import ItemFilterCriteria, AnyItemInteraction
from linkurator_core.infrastructure.mongodb.item_repository import MongoDBItem, MongoDBItemRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized


@pytest.fixture(name="item_repo", scope="session")
def fixture_item_repo(db_name: str) -> MongoDBItemRepository:
    return MongoDBItemRepository(IPv4Address('127.0.0.1'), 27017, db_name,
                                 "develop", "develop")


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
    item_repo.upsert_items([item])
    the_item = item_repo.get_item(item.uuid)

    assert the_item is not None
    assert the_item == item


def test_get_item_that_does_not_exist(item_repo: MongoDBItemRepository) -> None:
    the_item = item_repo.get_item(UUID("88aa425f-28d9-4a25-a87a-8c877cac772d"))

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
            item_repo.get_item(UUID("756b6b0d-5f54-4099-ae7e-c900666f0a0d"))


def test_delete_item(item_repo: MongoDBItemRepository) -> None:
    item = mock_item(item_uuid=UUID("4bf64498-239e-4bcb-a5a1-b84a7708ad01"))

    item_repo.upsert_items([item])
    the_item = item_repo.get_item(item.uuid)
    assert the_item is not None

    item_repo.delete_item(item.uuid)
    deleted_item = item_repo.get_item(item.uuid)
    assert deleted_item is None


def test_create_and_update_items(item_repo: MongoDBItemRepository) -> None:
    item1 = mock_item(item_uuid=UUID("72ab4421-f2b6-499a-bbf1-5105f2ed549b"))
    item2 = mock_item(item_uuid=UUID("a5a908e6-aa2c-4240-9a6d-d4340d38b8fc"))

    item_repo.upsert_items([item1, item2])

    item1_found = item_repo.get_item(item1.uuid)
    item2_found = item_repo.get_item(item2.uuid)

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

    item_repo.upsert_items([item1_updated, item2_updated])

    item1_found = item_repo.get_item(item1.uuid)
    item2_found = item_repo.get_item(item2.uuid)

    assert item1_found == item1_updated
    assert item2_found == item2_updated


def test_create_and_update_items_with_no_items(item_repo: MongoDBItemRepository) -> None:
    item_repo.upsert_items([])
    assert True


def test_get_items_by_subscription_uuid(item_repo: MongoDBItemRepository) -> None:
    subscription_uuid_1 = UUID("49e16717-3b41-4e1b-a2d8-8fccf1b6c184")
    subscription_uuid_2 = UUID("d3e22c40-c767-468b-8a61-cc61bcfd55ec")
    subscription_uuid_3 = UUID("9753d304-3a43-414e-a5cd-496672b27c34")

    item1 = mock_item(item_uuid=UUID("6469596f-5128-4c12-87f1-9b7b462517f3"), sub_uuid=subscription_uuid_1)
    item2 = mock_item(item_uuid=UUID("2dcc5c6b-3d95-421d-a9cf-81ac475cee4c"), sub_uuid=subscription_uuid_1)
    item3 = mock_item(item_uuid=UUID("199f25cc-ff99-4a5c-9329-edebc3fdc0e5"), sub_uuid=subscription_uuid_2)

    item_repo.upsert_items([item1, item2, item3])

    items_from_sub1 = item_repo.find_items(
        criteria=ItemFilterCriteria(subscription_ids=[subscription_uuid_1]), page_number=0, limit=10)
    items_from_sub2 = item_repo.find_items(
        criteria=ItemFilterCriteria(subscription_ids=[subscription_uuid_2]), page_number=0, limit=10)
    items_from_sub3 = item_repo.find_items(
        criteria=ItemFilterCriteria(subscription_ids=[subscription_uuid_3]), page_number=0, limit=10)

    assert len(items_from_sub1) == 2
    assert len(items_from_sub2) == 1
    assert len(items_from_sub3) == 0


def test_find_items_by_uuid(item_repo: MongoDBItemRepository) -> None:
    item1 = mock_item(item_uuid=UUID("cd79132f-ad0a-4206-b118-2c958bc28506"))
    item2 = mock_item(item_uuid=UUID("8e014a74-ddf9-4ad1-a354-22e1c9dd7acc"))

    item_repo.upsert_items([item1, item2])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(item_ids={item1.uuid, uuid4()}), page_number=0, limit=10)

    assert len(found_items) == 1
    assert found_items[0] == item1

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(item_ids=set()), page_number=0, limit=10)

    assert len(found_items) == 0


def test_find_items_by_subscription_uuids(item_repo: MongoDBItemRepository) -> None:
    item1 = mock_item(item_uuid=UUID("9559fa81-e968-4d0d-8390-070908f66985"),
                      sub_uuid=UUID("e887b865-8aa2-47a5-a133-a6eb7ba0f957"))
    item2 = mock_item(item_uuid=UUID("16f3a929-82a1-4cee-be30-70861d9266f2"),
                      sub_uuid=UUID("22da439a-b9e0-4837-9b52-12ad15374832"))

    item_repo.upsert_items([item1, item2])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(subscription_ids=[item1.subscription_uuid, uuid4()]), page_number=0, limit=10)

    assert len(found_items) == 1
    assert found_items[0] == item1

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(subscription_ids=[]), page_number=0, limit=10)

    assert len(found_items) == 0


def test_find_item_with_same_url(item_repo: MongoDBItemRepository) -> None:
    item1 = mock_item(item_uuid=UUID("8fc4fbca-439c-4c0e-937d-4147ef3b299c"),
                      url='https://item-with-same-url.com')

    item_repo.upsert_items([item1])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(url=utils.parse_url('https://item-with-same-url.com')),
        page_number=0, limit=10)

    assert len(found_items) == 1
    assert found_items[0].uuid == item1.uuid


def test_find_item_with_different_url_returns_none(item_repo: MongoDBItemRepository) -> None:
    item1 = mock_item(item_uuid=UUID("00fbe982-1c90-4e7a-bf73-4716fa565b3c"),
                      url='https://item-with-same-url.com')

    item_repo.upsert_items([item1])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(url=utils.parse_url('https://item-with-different-url.com')),
        page_number=0, limit=10)

    assert len(found_items) == 0


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

    item_repo.upsert_items([item1, item2, item3, item4])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub_uuid],
            published_after=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
            created_before=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc)),
        page_number=0,
        limit=1)

    assert len(found_items) == 1
    assert found_items[0].uuid == item4.uuid

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub_uuid],
            published_after=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
            created_before=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc)),
        page_number=1,
        limit=1)

    assert len(found_items) == 1
    assert found_items[0].uuid == item1.uuid

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub_uuid],
            published_after=datetime(2020, 1, 1, 4, 4, 4, tzinfo=timezone.utc),
            created_before=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc)),
        page_number=2,
        limit=1)

    assert len(found_items) == 0


def test_get_items_created_before_a_certain_date(item_repo: MongoDBItemRepository) -> None:
    item_repo.delete_all_items()

    item1 = mock_item(item_uuid=UUID("e1f898c2-bcfb-435a-97c0-9f462f73e95b"),
                      created_at=datetime(2000, 1, 1, 0, 0, 10, tzinfo=timezone.utc),
                      published_at=datetime(2000, 1, 1, 0, 0, 10, tzinfo=timezone.utc))

    item_repo.upsert_items([item1])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(created_before=datetime(2000, 1, 1, 0, 0, 11, tzinfo=timezone.utc)),
        page_number=0,
        limit=1)
    assert item1.uuid in [item.uuid for item in found_items]

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(created_before=datetime(2000, 1, 1, 0, 0, 10, tzinfo=timezone.utc)),
        page_number=0,
        limit=1)
    assert item1.uuid not in [item.uuid for item in found_items]

    found_items = item_repo.find_items(
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
    item_repo.upsert_items([item1, item2, item3, item4])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub1_uuid],
            text="videogames"),
        page_number=0,
        limit=4
    )
    assert len(found_items) == 2
    assert found_items[0].uuid == item4.uuid
    assert found_items[1].uuid == item2.uuid

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub1_uuid],
            text="cool videogames"),
        limit=4,
        page_number=0,
    )
    assert len(found_items) == 1
    assert found_items[0].uuid == item2.uuid

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub1_uuid],
            text="\"football free\""),
        limit=4,
        page_number=0,
    )
    assert len(found_items) == 1
    assert found_items[0].uuid == item1.uuid

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            subscription_ids=[sub1_uuid],
            text="swim"),
        limit=4,
        page_number=0,
    )
    assert len(found_items) == 0


def test_filter_with_empty_string_returns_all_items(item_repo: MongoDBItemRepository) -> None:
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

    item_repo.delete_all_items()
    item_repo.upsert_items([item1, item2])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(text=""),
        page_number=0,
        limit=2
    )
    assert len(found_items) == 2


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

    item_repo.upsert_items([item1, item2, item3, item4])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            last_version=2,
            provider=ItemProvider.YOUTUBE,
        ),
        limit=4,
        page_number=0)
    assert len(found_items) == 2
    assert {item.uuid for item in found_items} == {item1.uuid, item4.uuid}

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            last_version=3,
            provider=ItemProvider.YOUTUBE,
        ),
        limit=1,
        page_number=0)
    assert len(found_items) == 1
    assert found_items[0].uuid == item4.uuid


def test_find_items_with_every_interaction(
        item_repo: MongoDBItemRepository
) -> None:
    item_repo.delete_all_items()

    item1 = mock_item(item_uuid=UUID("9e7d23e7-c8fb-44c7-806b-ec87a61d4986"),
                      published_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    item2 = mock_item(item_uuid=UUID("841ce05f-baf8-45b1-80c2-82c4b716339b"),
                      published_at=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc))
    item3 = mock_item(item_uuid=UUID("b4449f1d-4a96-4541-b037-0ae357864e9f"),
                      published_at=datetime(2020, 1, 3, 0, 0, 0, tzinfo=timezone.utc))
    item4 = mock_item(item_uuid=UUID("6f9f5f02-eb83-4358-8794-ef452dea2f2f"),
                      published_at=datetime(2020, 1, 4, 0, 0, 0, tzinfo=timezone.utc))
    item5 = mock_item(item_uuid=UUID("c109fc31-2ddd-4db3-9552-c7f123095174"),
                      published_at=datetime(2020, 1, 5, 0, 0, 0, tzinfo=timezone.utc))
    item6 = mock_item(item_uuid=UUID("99d2ce12-c934-4434-957a-b30571fd6ffa"),
                      published_at=datetime(2020, 1, 6, 0, 0, 0, tzinfo=timezone.utc))
    item7 = mock_item(item_uuid=UUID("81c3b2a0-cdbb-44f3-a6f9-df7952742265"),
                      published_at=datetime(2020, 1, 7, 0, 0, 0, tzinfo=timezone.utc))
    item8 = mock_item(item_uuid=UUID("57c5d6ef-8238-47e6-821a-4aaecf25eb85"),
                      published_at=datetime(2020, 1, 8, 0, 0, 0, tzinfo=timezone.utc))
    item9 = mock_item(item_uuid=UUID("e495299e-9bdc-4635-85eb-4bba735c155d"),
                      published_at=datetime(2020, 1, 9, 0, 0, 0, tzinfo=timezone.utc))
    item10 = mock_item(item_uuid=UUID("d1f63104-f42d-4b3a-84d4-70fb3f68ba56"),
                       published_at=datetime(2020, 1, 10, 0, 0, 0, tzinfo=timezone.utc))

    item_repo.upsert_items([item1, item2, item3, item4, item5, item6, item7, item8, item9, item10])

    user1_id = UUID("52819cca-4de6-4b8b-b313-5cbd5b169161")
    user2_id = UUID("6b1a1205-0288-46c4-a65c-78489af00184")
    item_repo.add_interaction(Interaction(
        uuid=UUID("76551ba4-1757-4cd6-9f98-5ef14b7c1209"),
        item_uuid=item3.uuid,
        user_uuid=user1_id,
        type=InteractionType.VIEWED,
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    ))
    item_repo.add_interaction(Interaction(
        uuid=UUID("f3a71119-00ac-4778-a34b-bde39d70c0ed"),
        item_uuid=item4.uuid,
        user_uuid=user2_id,
        type=InteractionType.VIEWED,
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    ))
    item_repo.add_interaction(Interaction(
        uuid=UUID("6bdba327-2f79-4411-a265-4db8cb752210"),
        item_uuid=item5.uuid,
        user_uuid=user1_id,
        type=InteractionType.RECOMMENDED,
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    ))
    item_repo.add_interaction(Interaction(
        uuid=UUID("b8a1ae8d-aa15-424c-9c96-36640bb9d38a"),
        item_uuid=item6.uuid,
        user_uuid=user2_id,
        type=InteractionType.RECOMMENDED,
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    ))
    item_repo.add_interaction(Interaction(
        uuid=UUID("38846b36-b895-4af5-9392-bcaaef4f7d71"),
        item_uuid=item7.uuid,
        user_uuid=user1_id,
        type=InteractionType.DISCOURAGED,
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    ))
    item_repo.add_interaction(Interaction(
        uuid=UUID("28f1a32a-2b20-4487-b271-55e0650174c4"),
        item_uuid=item8.uuid,
        user_uuid=user2_id,
        type=InteractionType.DISCOURAGED,
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    ))
    item_repo.add_interaction(Interaction(
        uuid=UUID("d139da93-0eae-4601-84fa-ff5e3cf01c32"),
        item_uuid=item9.uuid,
        user_uuid=user1_id,
        type=InteractionType.HIDDEN,
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    ))
    item_repo.add_interaction(Interaction(
        uuid=UUID("cae18e14-681b-4e3b-b3ca-c8813e50d7f1"),
        item_uuid=item10.uuid,
        user_uuid=user2_id,
        type=InteractionType.HIDDEN,
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    ))

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            interactions=AnyItemInteraction(
                without_interactions=True,
            ),
            interactions_from_user=user1_id
        ),
        limit=10,
        page_number=0)

    assert len(found_items) == 6
    assert [item10, item8, item6, item4, item2, item1] == found_items

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            interactions=AnyItemInteraction(
                viewed=True,
            ),
            interactions_from_user=user1_id
        ),
        limit=10,
        page_number=0)

    assert len(found_items) == 1
    assert [item3] == found_items

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            interactions=AnyItemInteraction(
                recommended=True,
            ),
            interactions_from_user=user1_id
        ),
        limit=10,
        page_number=0)

    assert len(found_items) == 1
    assert [item5] == found_items

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            interactions=AnyItemInteraction(
                discouraged=True,
            ),
            interactions_from_user=user1_id
        ),
        limit=10,
        page_number=0)

    assert len(found_items) == 1
    assert [item7] == found_items

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            interactions=AnyItemInteraction(
                hidden=True,
            ),
            interactions_from_user=user1_id
        ),
        limit=10,
        page_number=0)

    assert len(found_items) == 1
    assert [item9] == found_items


def test_find_user_recommended_or_without_interaction_items(
        item_repo: MongoDBItemRepository
) -> None:
    item_repo.delete_all_items()

    item1 = mock_item(item_uuid=UUID("197041bc-fecf-4591-8dcd-5d823635301d"),
                      published_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    item2 = mock_item(item_uuid=UUID("a2b2d76a-4fb8-42d8-83da-9ebce0908aaa"),
                      published_at=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc))
    item3 = mock_item(item_uuid=UUID("cc3596f9-512a-4bd0-94eb-9a2640ba1b51"))

    item_repo.upsert_items([item1, item2, item3])

    user1_id = UUID("06e9d257-7edb-419d-bb42-b0d3773e74d8")
    user2_id = UUID("c789dbe8-d880-47f4-930b-6ad4dc99c3da")
    item_repo.add_interaction(Interaction(
        uuid=UUID("487887be-ff8b-4b3a-a772-860d9e9deaaf"),
        item_uuid=item1.uuid,
        user_uuid=user1_id,
        type=InteractionType.RECOMMENDED,
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    ))
    item_repo.add_interaction(Interaction(
        uuid=UUID("bc7ca62e-1348-44c9-8f09-b38f6d33dbd4"),
        item_uuid=item2.uuid,
        user_uuid=user1_id,
        type=InteractionType.VIEWED,
        created_at=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
    ))
    item_repo.add_interaction(Interaction(
        uuid=UUID("5a0c9349-7041-4bc1-b0a3-3b387e258f4d"),
        item_uuid=item3.uuid,
        user_uuid=user2_id,
        type=InteractionType.RECOMMENDED,
        created_at=datetime(2020, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
    ))

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            interactions=AnyItemInteraction(
                without_interactions=True,
                recommended=True,
            ),
            interactions_from_user=user1_id
        ),
        limit=3,
        page_number=0)

    assert len(found_items) == 2
    assert [item3, item1] == found_items


def test_get_interaction(item_repo: MongoDBItemRepository) -> None:
    interaction = Interaction.new(
        uuid=UUID("74cf7cb9-e86e-4d7d-9bb8-3881dc2ebd82"),
        item_uuid=UUID("77c0d137-b8d7-4424-836f-d9f4b546f2e9"),
        user_uuid=UUID("3b1b3369-f7f7-4f61-926f-bdbe3c49160a"),
        interaction_type=InteractionType.RECOMMENDED
    )
    item_repo.add_interaction(interaction)
    assert item_repo.get_interaction(interaction.uuid) == interaction


def test_delete_interaction(item_repo: MongoDBItemRepository) -> None:
    interaction = Interaction.new(
        uuid=UUID("20e413a1-4600-4c7e-bab8-bb692ec51921"),
        user_uuid=UUID("60f53698-9cc6-47e5-994c-25c6cded6f62"),
        item_uuid=UUID("3ee43c65-2792-4c04-bc63-b3952988d954"),
        interaction_type=InteractionType.RECOMMENDED
    )
    item_repo.add_interaction(interaction)
    assert item_repo.get_interaction(interaction.uuid) is not None

    item_repo.delete_interaction(interaction.uuid)
    assert item_repo.get_interaction(interaction.uuid) is None


def test_get_interactions_by_item(item_repo: MongoDBItemRepository) -> None:
    interaction0 = Interaction.new(
        uuid=UUID("99f8c2ce-bc34-45ed-8368-139033acf32e"),
        user_uuid=UUID("22bb661b-f298-435e-9bab-0e9a24c18638"),
        item_uuid=UUID("e29bf8f6-639e-4eb0-9d1e-fd452a7e6c3d"),
        interaction_type=InteractionType.RECOMMENDED,
    )

    interaction1 = Interaction.new(
        uuid=UUID("7b4eee4a-95a6-47af-9cf1-46f5a23cbde7"),
        user_uuid=UUID("e306a421-e191-4f50-874d-1f9e78e13694"),
        item_uuid=UUID("581402ec-8043-4098-9995-735e9e427571"),
        interaction_type=InteractionType.RECOMMENDED
    )
    item_repo.add_interaction(interaction1)

    interactions = item_repo.get_user_interactions_by_item_id(
        user_id=interaction1.user_uuid,
        item_ids=[interaction0.item_uuid, interaction1.item_uuid])

    assert interaction0.item_uuid in interactions
    assert interactions[interaction0.item_uuid] == []
    assert interaction1.item_uuid in interactions
    assert interactions[interaction1.item_uuid] == [interaction1]


def test_find_items_with_max_and_min_duration(item_repo: MongoDBItemRepository) -> None:
    item_repo.delete_all_items()

    item1 = mock_item(item_uuid=UUID("ea04f10a-8c2b-4f3f-82be-0534eb5a0326"),
                      duration=600)
    item2 = mock_item(item_uuid=UUID("841ce05f-baf8-45b1-80c2-82c4b716339b"),
                      duration=None)
    item3 = mock_item(item_uuid=UUID("cc3596f9-512a-4bd0-94eb-9a2640ba1b51"),
                      duration=601)
    item4 = mock_item(item_uuid=UUID("1a2de48e-c2f9-47c5-b91f-a98d86cdb25d"),
                      duration=599)

    item_repo.upsert_items([item1, item2, item3, item4])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            max_duration=600
        ),
        limit=10,
        page_number=0)

    assert len(found_items) == 2
    assert {item4, item1} == set(found_items)

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            min_duration=600
        ),
        limit=10,
        page_number=0)

    assert len(found_items) == 2
    assert {item3, item1} == set(found_items)

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            min_duration=600,
            max_duration=600
        ),
        limit=10,
        page_number=0)

    assert len(found_items) == 1
    assert {item1} == set(found_items)


def test_find_zero_duration_items(item_repo: MongoDBItemRepository) -> None:
    item_repo.delete_all_items()

    item1 = mock_item(item_uuid=UUID("ea04f10a-8c2b-4f3f-82be-0534eb5a0326"),
                      duration=0)
    item2 = mock_item(item_uuid=UUID("841ce05f-baf8-45b1-80c2-82c4b716339b"),
                      duration=None)
    item3 = mock_item(item_uuid=UUID("cc3596f9-512a-4bd0-94eb-9a2640ba1b51"),
                      duration=1)

    item_repo.upsert_items([item1, item2, item3])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            max_duration=0
        ),
        limit=10,
        page_number=0)

    assert len(found_items) == 1
    assert {item1} == set(found_items)


def test_find_items_updated_before_a_date(item_repo: MongoDBItemRepository) -> None:
    item_repo.delete_all_items()

    item1 = mock_item(item_uuid=UUID("ea04f10a-8c2b-4f3f-82be-0534eb5a0326"),
                      updated_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    item2 = mock_item(item_uuid=UUID("841ce05f-baf8-45b1-80c2-82c4b716339b"),
                      updated_at=datetime(2020, 1, 1, 0, 0, 1, tzinfo=timezone.utc))
    item3 = mock_item(item_uuid=UUID("cc3596f9-512a-4bd0-94eb-9a2640ba1b51"),
                      updated_at=datetime(2020, 1, 1, 0, 0, 2, tzinfo=timezone.utc))

    item_repo.upsert_items([item1, item2, item3])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(
            updated_before=datetime(2020, 1, 1, 0, 0, 1, tzinfo=timezone.utc)),
        page_number=0,
        limit=10)
    assert len(found_items) == 1
    assert found_items == [item1]


def test_update_video_with_deleted_at_date(item_repo: MongoDBItemRepository) -> None:
    item_repo.delete_all_items()

    item1 = mock_item(item_uuid=UUID("cf567af9-09dc-4719-b7d4-1a50c293f3b3"))

    item_repo.upsert_items([item1])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(),
        page_number=0,
        limit=10)
    assert len(found_items) == 1
    assert found_items == [item1]

    item1.deleted_at = datetime.now(tz=timezone.utc)
    item_repo.upsert_items([item1])

    found_items = item_repo.find_items(
        criteria=ItemFilterCriteria(),
        page_number=0,
        limit=10)
    assert len(found_items) == 0
