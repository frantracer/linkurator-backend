import datetime
from ipaddress import IPv4Address
from unittest import mock
from unittest.mock import MagicMock
import uuid

from math import floor
import pytest

from linkurator_core.common import utils
from linkurator_core.domain.subscription import Subscription
from linkurator_core.infrastructure.mongodb.repositories import CollectionIsNotInitialized
from linkurator_core.infrastructure.mongodb.subscription_repository import MongoDBSubscription, \
    MongoDBSubscriptionRepository


@pytest.fixture(name="subscription_repo", scope="session")
def fixture_subscription_repo(db_name) -> MongoDBSubscriptionRepository:
    return MongoDBSubscriptionRepository(IPv4Address('127.0.0.1'), 27017, db_name, "develop", "develop")


def test_exception_is_raised_if_subscriptions_collection_is_not_created():
    non_existent_db_name = f"test-{uuid.uuid4()}"
    with pytest.raises(CollectionIsNotInitialized):
        MongoDBSubscriptionRepository(IPv4Address('127.0.0.1'), 27017, non_existent_db_name, "develop", "develop")


def test_add_subscription(subscription_repo: MongoDBSubscriptionRepository):
    subscription = Subscription.new(name="test", uuid=uuid.UUID("8d9e9e1f-c9b4-4b8f-b8c4-c8f1e7b7d9a1"),
                                    url=utils.parse_url('https://test.com'),
                                    thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                                    external_id='1', provider="test")

    subscription_repo.add(subscription)
    the_subscription = subscription_repo.get(subscription.uuid)

    assert the_subscription is not None
    assert the_subscription.name == subscription.name
    assert the_subscription.uuid == subscription.uuid
    assert the_subscription.url == subscription.url
    assert the_subscription.thumbnail == subscription.thumbnail
    assert int(the_subscription.created_at.timestamp() * 100) == floor(subscription.created_at.timestamp() * 100)
    assert int(the_subscription.updated_at.timestamp() * 100) == floor(subscription.updated_at.timestamp() * 100)
    assert int(the_subscription.scanned_at.timestamp() * 100) == floor(subscription.scanned_at.timestamp() * 100)


def test_find_a_subscription_that_already_exist(subscription_repo: MongoDBSubscriptionRepository):
    sub1 = Subscription.new(name="test", uuid=uuid.UUID("e329b931-9bf0-410f-9789-d48ea4eb816b"),
                            url=utils.parse_url('https://the-same-url.com'),
                            thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                            external_id='1', provider="test")
    sub2 = Subscription.new(name="test", uuid=uuid.UUID("92fd4909-6d56-427a-acc4-3215e56375d0"),
                            url=utils.parse_url('https://the-same-url.com'),
                            thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                            external_id='1', provider="test")

    subscription_repo.add(sub1)
    found_subscription = subscription_repo.find(sub2)
    assert found_subscription is not None
    assert found_subscription.uuid == sub1.uuid


def test_find_a_subscription_that_does_not_exist(subscription_repo: MongoDBSubscriptionRepository):
    sub1 = Subscription.new(name="test", uuid=uuid.UUID("391f6292-b677-494f-b60d-791e51d22f08"),
                            url=utils.parse_url('https://391f6292-b677-494f-b60d-791e51d22f08.com'),
                            thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                            external_id='1', provider="test")

    found_subscription = subscription_repo.find(sub1)
    assert found_subscription is None


def test_get_subscription_that_does_not_exist(subscription_repo: MongoDBSubscriptionRepository):
    the_subscription = subscription_repo.get(uuid.UUID("0af092ed-e3f9-4919-8202-c19bfd0627a9"))

    assert the_subscription is None


def test_get_subscription_with_invalid_format_raises_an_exception(subscription_repo: MongoDBSubscriptionRepository):
    subscription_dict = dict(MongoDBSubscription(uuid=uuid.UUID("3ab7068b-1412-46ed-bc1f-46d5f03542e7"),
                                                 provider="test", external_id="1",
                                                 name="test", url=utils.parse_url('https://test.com'),
                                                 thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                                                 created_at=datetime.datetime.now(), updated_at=datetime.datetime.now(),
                                                 scanned_at=datetime.datetime(1970, 1, 1, 0, 0, 0, 0)))
    subscription_dict['uuid'] = 'invalid_uuid'
    subscription_collection_mock = MagicMock()
    subscription_collection_mock.find_one = MagicMock(return_value=subscription_dict)
    with mock.patch.object(MongoDBSubscriptionRepository, '_subscription_collection',
                           return_value=subscription_collection_mock):
        with pytest.raises(ValueError):
            subscription_repo.get(uuid.UUID("81f7d26c-4a7f-4a27-a081-bb77e034fb30"))


def test_get_list_of_subscriptions_ordered_by_created_at(subscription_repo: MongoDBSubscriptionRepository):
    sub1 = Subscription(
        name="test",
        uuid=uuid.UUID("83ea331c-fa87-4654-89d0-055972a64e5b"),
        url=utils.parse_url('https://url.com'),
        thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
        external_id='1',
        provider="test",
        created_at=datetime.datetime.fromisoformat("2020-01-02T00:00:00.000000"),
        updated_at=datetime.datetime.fromtimestamp(0),
        scanned_at=datetime.datetime.fromtimestamp(0))
    sub2 = Subscription(
        name="test",
        uuid=uuid.UUID("5745b75b-9a0a-49ff-85c5-b69c03bd1ba2"),
        url=utils.parse_url('https://url.com'),
        thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
        external_id='2',
        provider="test",
        created_at=datetime.datetime.fromisoformat("2020-01-03T00:00:00.000000"),
        updated_at=datetime.datetime.fromtimestamp(0),
        scanned_at=datetime.datetime.fromtimestamp(0))
    sub3 = Subscription(
        name="test",
        uuid=uuid.UUID("d30ca1c8-40c4-4bcd-8b4f-81f0e315c975"),
        url=utils.parse_url('https://url.com'),
        thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
        external_id='3',
        provider="test",
        created_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00.000000"),
        updated_at=datetime.datetime.fromtimestamp(0),
        scanned_at=datetime.datetime.fromtimestamp(0))

    subscription_repo.add(sub1)
    subscription_repo.add(sub2)
    subscription_repo.add(sub3)

    subscriptions = subscription_repo.get_list([sub1.uuid, sub2.uuid, sub3.uuid])
    assert len(subscriptions) == 3
    assert subscriptions[0].uuid == sub2.uuid
    assert subscriptions[1].uuid == sub1.uuid
    assert subscriptions[2].uuid == sub3.uuid


def test_delete_subscription(subscription_repo: MongoDBSubscriptionRepository):
    subscription = Subscription.new(name="test", uuid=uuid.UUID("0af092ed-e3f9-4919-8202-c19bfd0627a9"),
                                    url=utils.parse_url('https://test.com'),
                                    thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                                    external_id='1', provider="test")

    subscription_repo.add(subscription)
    the_subscription = subscription_repo.get(subscription.uuid)
    assert the_subscription is not None

    subscription_repo.delete(subscription.uuid)
    deleted_subscription = subscription_repo.get(subscription.uuid)
    assert deleted_subscription is None
