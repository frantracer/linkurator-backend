import uuid
from datetime import datetime, timezone
from ipaddress import IPv4Address
from math import floor
from typing import Any

import pytest
import pytest_asyncio

from linkurator_core.domain.common import utils
from linkurator_core.domain.common.mock_factory import mock_sub
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import (
    SubscriptionFilterCriteria,
    SubscriptionRepository,
)
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized
from linkurator_core.infrastructure.mongodb.subscription_repository import MongoDBSubscriptionRepository


@pytest_asyncio.fixture(name="subscription_repo", scope="session", params=["mongodb", "in_memory"])
async def fixture_subscription_repo(db_name: str, request: Any) -> SubscriptionRepository:
    if request.param == "in_memory":
        return InMemorySubscriptionRepository()
    return MongoDBSubscriptionRepository(IPv4Address("127.0.0.1"), 27017, db_name, "develop", "develop")


@pytest.mark.asyncio()
async def test_exception_is_raised_if_subscriptions_collection_is_not_created() -> None:
    non_existent_db_name = f"test-{uuid.uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        repo = MongoDBSubscriptionRepository(
            IPv4Address("127.0.0.1"), 27017, non_existent_db_name, "develop", "develop")
        await repo.check_connection()


@pytest.mark.asyncio()
async def test_add_subscription(subscription_repo: SubscriptionRepository) -> None:
    subscription = Subscription.new(
        name="test",
        uuid=uuid.UUID("8d9e9e1f-c9b4-4b8f-b8c4-c8f1e7b7d9a1"),
        url=utils.parse_url("https://test.com"),
        thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
        external_data=None,
        provider=SubscriptionProvider.YOUTUBE)

    await subscription_repo.add(subscription)
    the_subscription = await subscription_repo.get(subscription.uuid)

    assert the_subscription is not None
    assert the_subscription.name == subscription.name
    assert the_subscription.uuid == subscription.uuid
    assert the_subscription.url == subscription.url
    assert the_subscription.thumbnail == subscription.thumbnail
    assert the_subscription.external_data == {}
    assert int(the_subscription.created_at.timestamp() * 100) == floor(subscription.created_at.timestamp() * 100)
    assert int(the_subscription.updated_at.timestamp() * 100) == floor(subscription.updated_at.timestamp() * 100)
    assert int(the_subscription.scanned_at.timestamp() * 100) == floor(subscription.scanned_at.timestamp() * 100)
    assert int(the_subscription.last_published_at.timestamp() * 100) == floor(
        subscription.last_published_at.timestamp() * 100)


@pytest.mark.asyncio()
async def test_add_subscriptions_stores_any_external_data(subscription_repo: SubscriptionRepository) -> None:
    subscription = Subscription.new(
        name="test",
        uuid=uuid.UUID("31a2ba8e-e3a5-405a-ae41-43eaaab56fdf"),
        url=utils.parse_url("https://31a2ba8e-e3a5-405a-ae41-43eaaab56fdf.com"),
        thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
        external_data={"test": "test"},
        provider=SubscriptionProvider.YOUTUBE)

    await subscription_repo.add(subscription)
    the_subscription = await subscription_repo.get(subscription.uuid)

    assert the_subscription is not None
    assert the_subscription.external_data == {"test": "test"}


@pytest.mark.asyncio()
async def test_find_a_subscription_that_already_exist(subscription_repo: SubscriptionRepository) -> None:
    sub1 = Subscription.new(name="test",
                            uuid=uuid.UUID("e329b931-9bf0-410f-9789-d48ea4eb816b"),
                            url=utils.parse_url("https://the-same-url.com"),
                            thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
                            provider=SubscriptionProvider.YOUTUBE)
    sub2 = Subscription.new(name="test",
                            uuid=uuid.UUID("92fd4909-6d56-427a-acc4-3215e56375d0"),
                            url=utils.parse_url("https://the-same-url.com"),
                            thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
                            provider=SubscriptionProvider.YOUTUBE)

    await subscription_repo.add(sub1)
    found_subscription = await subscription_repo.find_by_url(sub2.url)
    assert found_subscription is not None
    assert found_subscription.uuid == sub1.uuid


@pytest.mark.asyncio()
async def test_find_a_subscription_that_does_not_exist(subscription_repo: SubscriptionRepository) -> None:
    sub1 = Subscription.new(name="test",
                            uuid=uuid.UUID("391f6292-b677-494f-b60d-791e51d22f08"),
                            url=utils.parse_url("https://391f6292-b677-494f-b60d-791e51d22f08.com"),
                            thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
                            provider=SubscriptionProvider.YOUTUBE)

    found_subscription = await subscription_repo.find_by_url(sub1.url)
    assert found_subscription is None


@pytest.mark.asyncio()
async def test_find_subscriptions_scanned_before_a_date(subscription_repo: SubscriptionRepository) -> None:
    sub1 = Subscription(
        name="test",
        uuid=uuid.UUID("2e17788f-0411-4383-a3f6-69c2c1a07901"),
        url=utils.parse_url("https://2e17788f.com"),
        thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
        provider=SubscriptionProvider.YOUTUBE,
        created_at=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        scanned_at=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        last_published_at=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        external_data={},
    )
    sub2 = Subscription(
        name="test",
        uuid=uuid.UUID("9270daf8-1c06-4566-adfd-ace610c67811"),
        url=utils.parse_url("https://9270daf8.com"),
        thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
        provider=SubscriptionProvider.YOUTUBE,
        created_at=datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        scanned_at=datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        last_published_at=datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        external_data={},
    )

    current_subscriptions = await subscription_repo.find_latest_scan_before(
        datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc))
    await subscription_repo.add(sub1)
    await subscription_repo.add(sub2)
    updated_subscriptions = await subscription_repo.find_latest_scan_before(
        datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc))

    assert len(updated_subscriptions) - len(current_subscriptions) == 1


@pytest.mark.asyncio()
async def test_find_subspcriptions_updated_before_a_date(subscription_repo: SubscriptionRepository) -> None:
    sub1 = Subscription.new(
        name="test",
        uuid=uuid.UUID("ee17d49f-2e7d-4439-b563-7eba54623e5c"),
        url=utils.parse_url("https://ee17d49f-2e7d-4439-b563-7eba54623e5c.com"),
        provider=SubscriptionProvider.YOUTUBE,
        thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
        external_data={},
    )
    sub1.updated_at = datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
    sub2 = Subscription.new(
        name="test",
        uuid=uuid.UUID("f3b1b3b4-1b3b-4b3b-8b3b-3b3b3b3b3b3b"),
        url=utils.parse_url("https://f3b1b3b4-1b3b-4b3b-8b3b-3b3b3b3b3b3b.com"),
        provider=SubscriptionProvider.YOUTUBE,
        thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
        external_data={},
    )
    sub2.updated_at = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    filter_criteria = SubscriptionFilterCriteria(updated_before=datetime(2022, 1, 2, 0, 0, 0, tzinfo=timezone.utc))
    current_subscriptions = await subscription_repo.find(filter_criteria)
    await subscription_repo.add(sub1)
    await subscription_repo.add(sub2)

    updated_subscriptions = await subscription_repo.find(filter_criteria)
    assert len(updated_subscriptions) - len(current_subscriptions) == 1


@pytest.mark.asyncio()
async def test_get_subscription_that_does_not_exist(subscription_repo: SubscriptionRepository) -> None:
    the_subscription = await subscription_repo.get(uuid.UUID("0af092ed-e3f9-4919-8202-c19bfd0627a9"))

    assert the_subscription is None


@pytest.mark.asyncio()
async def test_get_list_of_subscriptions_ordered_by_created_at(
        subscription_repo: SubscriptionRepository) -> None:
    sub1 = Subscription(
        name="test",
        uuid=uuid.UUID("83ea331c-fa87-4654-89d0-055972a64e5b"),
        url=utils.parse_url("https://83ea331c-fa87-4654-89d0-055972a64e5b.com"),
        thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
        provider=SubscriptionProvider.YOUTUBE,
        external_data={},
        created_at=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime.fromtimestamp(0, tz=timezone.utc),
        scanned_at=datetime.fromtimestamp(0, tz=timezone.utc),
        last_published_at=datetime.fromtimestamp(0, tz=timezone.utc),
    )
    sub2 = Subscription(
        name="test",
        uuid=uuid.UUID("5745b75b-9a0a-49ff-85c5-b69c03bd1ba2"),
        url=utils.parse_url("https://5745b75b-9a0a-49ff-85c5-b69c03bd1ba2.com"),
        thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
        provider=SubscriptionProvider.YOUTUBE,
        external_data={},
        created_at=datetime(2020, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime.fromtimestamp(0, tz=timezone.utc),
        scanned_at=datetime.fromtimestamp(0, tz=timezone.utc),
        last_published_at=datetime.fromtimestamp(0, tz=timezone.utc),
    )
    sub3 = Subscription(
        name="test",
        uuid=uuid.UUID("d30ca1c8-40c4-4bcd-8b4f-81f0e315c975"),
        url=utils.parse_url("https://d30ca1c8-40c4-4bcd-8b4f-81f0e315c975.com"),
        thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
        provider=SubscriptionProvider.YOUTUBE,
        external_data={},
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime.fromtimestamp(0, tz=timezone.utc),
        scanned_at=datetime.fromtimestamp(0, tz=timezone.utc),
        last_published_at=datetime.fromtimestamp(0, tz=timezone.utc),
    )

    await subscription_repo.add(sub1)
    await subscription_repo.add(sub2)
    await subscription_repo.add(sub3)

    subscriptions = await subscription_repo.get_list([sub1.uuid, sub2.uuid, sub3.uuid])
    assert len(subscriptions) == 3
    assert subscriptions[0].uuid == sub2.uuid
    assert subscriptions[1].uuid == sub1.uuid
    assert subscriptions[2].uuid == sub3.uuid


@pytest.mark.asyncio()
async def test_update_subscription(subscription_repo: SubscriptionRepository) -> None:
    sub = Subscription(
        name="test",
        uuid=uuid.UUID("1515c810-e22a-4b13-bf34-329f8ebe2491"),
        url=utils.parse_url("https://1515c810-e22a-4b13-bf34-329f8ebe2491.com"),
        thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
        provider=SubscriptionProvider.YOUTUBE,
        external_data={},
        created_at=datetime.fromtimestamp(0, tz=timezone.utc),
        updated_at=datetime.fromtimestamp(0, tz=timezone.utc),
        scanned_at=datetime.fromtimestamp(0, tz=timezone.utc),
        last_published_at=datetime.fromtimestamp(0, tz=timezone.utc),
    )
    await subscription_repo.add(sub)

    sub.name = "new name"
    sub.url = utils.parse_url("https://new.com")
    sub.thumbnail = utils.parse_url("https://new.com/thumbnail.png")
    sub.provider = SubscriptionProvider.YOUTUBE
    sub.external_data = {"new": "data"}
    sub.created_at = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    sub.updated_at = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    sub.scanned_at = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    sub.last_published_at = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    await subscription_repo.update(sub)
    updated_subscription = await subscription_repo.get(sub.uuid)
    assert updated_subscription is not None
    assert updated_subscription.name == "new name"
    assert updated_subscription.url == utils.parse_url("https://new.com")
    assert updated_subscription.thumbnail == utils.parse_url("https://new.com/thumbnail.png")
    assert updated_subscription.provider == SubscriptionProvider.YOUTUBE
    assert updated_subscription.external_data == {"new": "data"}
    assert updated_subscription.created_at == datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert updated_subscription.updated_at == datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert updated_subscription.scanned_at == datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert updated_subscription.last_published_at == datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio()
async def test_delete_subscription(subscription_repo: SubscriptionRepository) -> None:
    subscription = Subscription.new(name="test",
                                    uuid=uuid.UUID("5f0430b3-6044-4cca-b739-d63c75794b3c"),
                                    url=utils.parse_url("https://5f0430b3-6044-4cca-b739-d63c75794b3c.com"),
                                    thumbnail=utils.parse_url("https://test.com/thumbnail.png"),
                                    provider=SubscriptionProvider.YOUTUBE)

    await subscription_repo.add(subscription)
    the_subscription = await subscription_repo.get(subscription.uuid)
    assert the_subscription is not None

    await subscription_repo.delete(subscription.uuid)
    deleted_subscription = await subscription_repo.get(subscription.uuid)
    assert deleted_subscription is None


@pytest.mark.asyncio()
async def test_find_subscriptions_by_name(subscription_repo: SubscriptionRepository) -> None:
    sub1 = mock_sub(name="Leyendas y videojuegos")
    sub2 = mock_sub(name="Fútbol y más")
    sub3 = mock_sub(name="leyendas del fútbol")

    await subscription_repo.delete_all()
    await subscription_repo.add(sub1)
    await subscription_repo.add(sub2)
    await subscription_repo.add(sub3)

    found_subscriptions = await subscription_repo.find_by_name("videojuegos")
    assert len(found_subscriptions) == 1
    assert found_subscriptions[0].uuid == sub1.uuid

    found_subscriptions = await subscription_repo.find_by_name("Leyendas")
    assert len(found_subscriptions) == 2
    assert {sub1.uuid, sub3.uuid} == {sub.uuid for sub in found_subscriptions}

    found_subscriptions = await subscription_repo.find_by_name("futbol")
    assert len(found_subscriptions) == 2
    assert {sub2.uuid, sub3.uuid} == {sub.uuid for sub in found_subscriptions}

    found_subscriptions = await subscription_repo.find_by_name("mas fútbol")
    assert len(found_subscriptions) == 1
    assert found_subscriptions[0].uuid == sub2.uuid

    found_subscriptions = await subscription_repo.find_by_name("baloncesto")
    assert len(found_subscriptions) == 0


@pytest.mark.asyncio()
async def test_count_subscriptions(subscription_repo: SubscriptionRepository) -> None:
    sub1 = mock_sub(name="Leyendas y videojuegos")
    sub2 = mock_sub(name="Fútbol y más")
    sub3 = mock_sub(name="leyendas del fútbol", provider=SubscriptionProvider.SPOTIFY)

    await subscription_repo.delete_all()
    await subscription_repo.add(sub1)
    await subscription_repo.add(sub2)
    await subscription_repo.add(sub3)

    assert await subscription_repo.count_subscriptions() == 3
    assert await subscription_repo.count_subscriptions(SubscriptionProvider.YOUTUBE) == 2
    assert await subscription_repo.count_subscriptions(SubscriptionProvider.SPOTIFY) == 1
