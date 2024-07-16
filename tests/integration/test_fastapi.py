import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from linkurator_core.application.items.get_subscription_items_handler import GetSubscriptionItemsHandler
from linkurator_core.application.items.get_topic_items_handler import GetTopicItemsHandler
from linkurator_core.application.users.get_user_profile_handler import GetUserProfileHandler
from linkurator_core.application.users.validate_token_handler import ValidateTokenHandler
from linkurator_core.domain.common import utils
from linkurator_core.domain.common.exceptions import SubscriptionNotFoundError, TopicNotFoundError
from linkurator_core.domain.items.item import Item
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.user import User
from linkurator_core.infrastructure.fastapi.create_app import Handlers, create_app_from_handlers

USER_UUID = uuid.UUID("8efe1fe3-906d-4aa4-8fbe-b47810c197d8")


@pytest.fixture(name="handlers", scope="function")
def dummy_handlers() -> Handlers:
    dummy_validate_token_handler = AsyncMock(spec=ValidateTokenHandler)
    dummy_validate_token_handler.handle.return_value = Session(
        user_id=USER_UUID,
        expires_at=datetime.fromisoformat('3000-01-01T00:00:00+00:00'),
        token='token')

    return Handlers(
        validate_token=dummy_validate_token_handler,
        register_user=AsyncMock(),
        google_client=AsyncMock(),
        get_subscription=AsyncMock(),
        get_user_subscriptions=AsyncMock(),
        get_subscription_items_handler=AsyncMock(),
        delete_subscription_items_handler=AsyncMock(),
        refresh_subscription_handler=AsyncMock(),
        get_user_profile_handler=AsyncMock(),
        delete_user_handler=AsyncMock(),
        get_topic_handler=AsyncMock(),
        get_topic_items_handler=AsyncMock(),
        get_user_topics_handler=AsyncMock(),
        create_topic_handler=AsyncMock(),
        assign_subscription_to_topic_handler=AsyncMock(),
        delete_topic_handler=AsyncMock(),
        unassign_subscription_from_topic_handler=AsyncMock(),
        update_topic_handler=AsyncMock(),
        get_item_handler=AsyncMock(),
        create_item_interaction_handler=AsyncMock(),
        delete_item_interaction_handler=AsyncMock(),
        get_user_external_credentials_handler=AsyncMock(),
        add_external_credentials_handler=AsyncMock(),
        delete_external_credential_handler=AsyncMock(),
    )


def test_health_returns_200(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers))

    response = client.get('/health')
    assert response.content == b'"OK"'
    assert response.status_code == 200


def test_user_profile_returns_200(handlers: Handlers) -> None:
    dummy_get_user_profile_handler = AsyncMock(spec=GetUserProfileHandler)
    dummy_get_user_profile_handler.handle.return_value = User(
        uuid=uuid.UUID("cb856f4f-8371-4648-af75-38fb34231092"),
        first_name="first name",
        last_name="last name",
        email="test@email.com",
        avatar_url=utils.parse_url('https://test.com/avatar.png'),
        locale="en-US",
        updated_at=datetime.fromtimestamp(0, tz=timezone.utc),
        created_at=datetime.fromtimestamp(0, tz=timezone.utc),
        scanned_at=datetime.fromtimestamp(0, tz=timezone.utc),
        last_login_at=datetime.fromtimestamp(0, tz=timezone.utc),
        subscription_uuids=[],
        google_refresh_token="refresh token",
        is_admin=False
    )
    handlers.get_user_profile_handler = dummy_get_user_profile_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.get('/profile')
    assert response.status_code == 200
    assert response.json()['uuid'] == 'cb856f4f-8371-4648-af75-38fb34231092'
    assert response.json()['first_name'] == 'first name'
    assert response.json()['last_name'] == 'last name'
    assert response.json()['email'] == 'test@email.com'
    assert response.json()['created_at'] == '1970-01-01T00:00:00+00:00'
    assert response.json()['last_scanned_at'] == '1970-01-01T00:00:00+00:00'


def test_user_profile_returns_404_when_user_not_found(handlers: Handlers) -> None:
    dummy_get_user_profile_handler = AsyncMock(spec=GetUserProfileHandler)
    dummy_get_user_profile_handler.handle.return_value = None
    handlers.get_user_profile_handler = dummy_get_user_profile_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.get('/profile')
    assert response.status_code == 404


def test_item_pagination_returns_one_page(handlers: Handlers) -> None:
    item1 = Item.new(name="item1",
                     description="",
                     uuid=uuid.UUID("ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8"),
                     subscription_uuid=uuid.UUID("3e9232e7-fa87-4e14-a642-9df94d619c1a"),
                     url=utils.parse_url('https://ae1b82ee.com'),
                     thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                     published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    dummy_get_subscription_items_handler = AsyncMock(spec=GetSubscriptionItemsHandler)
    dummy_get_subscription_items_handler.handle.return_value = [(item1, [])]
    handlers.get_subscription_items_handler = dummy_get_subscription_items_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.get(
        '/subscriptions/3e9232e7-fa87-4e14-a642-9df94d619c1a/items?'
        'created_before_ts=777.0&page_number=0&page_size=1')
    assert response.status_code == 200
    assert len(response.json()['elements']) == 1
    assert response.json()['next_page'] == (
        "http://testserver/subscriptions/3e9232e7-fa87-4e14-a642-9df94d619c1a/items?"
        "created_before_ts=777.0&page_number=1&page_size=1")
    assert response.json()['previous_page'] is None


def test_get_subscription_items_parses_query_parameters(handlers: Handlers) -> None:
    dummy_get_subscription_items_handler = AsyncMock(spec=GetSubscriptionItemsHandler)
    dummy_get_subscription_items_handler.handle.return_value = []
    handlers.get_subscription_items_handler = dummy_get_subscription_items_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    client.get(
        '/subscriptions/3e9232e7-fa87-4e14-a642-9df94d619c1a/items?'
        'page_number=0&page_size=1&search=test&created_before_ts=0&'
        'max_duration=100&min_duration=10&'
        'include_interactions=without_interactions,recommended,viewed,hidden,discouraged')
    dummy_get_subscription_items_handler.handle.assert_called_once_with(
        user_id=USER_UUID,
        subscription_id=uuid.UUID("3e9232e7-fa87-4e14-a642-9df94d619c1a"),
        created_before=datetime.fromtimestamp(0, tz=timezone.utc),
        page_number=0,
        page_size=1,
        text_filter='test',
        min_duration=10,
        max_duration=100,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=True,
        include_viewed_items=True,
        include_hidden_items=True)


def test_get_subscription_items_recommended_and_without_interactions(handlers: Handlers) -> None:
    dummy_get_subscription_items_handler = AsyncMock(spec=GetSubscriptionItemsHandler)
    dummy_get_subscription_items_handler.handle.return_value = []
    handlers.get_subscription_items_handler = dummy_get_subscription_items_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    client.get(
        '/subscriptions/3e9232e7-fa87-4e14-a642-9df94d619c1a/items?'
        'page_number=0&page_size=1&search=test&created_before_ts=0&'
        'include_interactions=without_interactions,recommended')
    dummy_get_subscription_items_handler.handle.assert_called_once_with(
        user_id=USER_UUID,
        subscription_id=uuid.UUID("3e9232e7-fa87-4e14-a642-9df94d619c1a"),
        created_before=datetime.fromtimestamp(0, tz=timezone.utc),
        page_number=0,
        page_size=1,
        text_filter='test',
        min_duration=None,
        max_duration=None,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=False,
        include_viewed_items=False,
        include_hidden_items=False)


def test_create_user_topic_returns_201(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.post(
        '/topics/',
        json={
            'uuid': 'ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8',
            'name': 'topic1',
            'subscriptions_ids': []
        })
    assert response.status_code == 201
    assert response.content == b''


def test_delete_topic_returns_204(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.delete('/topics/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8')
    assert response.status_code == 204
    assert response.content == b''


def test_delete_non_existing_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = TopicNotFoundError
    handlers.delete_topic_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.delete('/topics/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8')
    assert response.status_code == 404


def test_get_topics_returns_200(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.return_value = [Topic.new(
        uuid=uuid.UUID("f22b92da-5b90-455f-8141-fb4a37f07805"),
        name="topic1",
        user_id=uuid.UUID("24060726-9ee6-450e-bec2-0edf8e7b33b2"),
        subscription_ids=[]
    )]
    handlers.get_user_topics_handler = dummy_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.get('/topics')
    assert response.status_code == 200
    assert len(response.json()['elements']) == 1
    assert response.json()['next_page'] is None
    assert response.json()['previous_page'] is None


def test_get_topic_returns_200(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.return_value = Topic.new(
        uuid=uuid.UUID("f8be01d6-98b3-4ba7-a540-d2f008d1adbc"),
        name="topic1",
        user_id=uuid.UUID("f5b11947-0203-45b5-9c55-f3bd391ed150"),
        subscription_ids=[uuid.UUID("00ff1b4a-aeed-4321-8e40-53e78c13685d")]
    )
    handlers.get_topic_handler = dummy_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.get('/topics/f8be01d6-98b3-4ba7-a540-d2f008d1adbc')
    assert response.status_code == 200
    assert response.json()['uuid'] == 'f8be01d6-98b3-4ba7-a540-d2f008d1adbc'
    assert response.json()['name'] == 'topic1'
    assert response.json()['user_id'] == 'f5b11947-0203-45b5-9c55-f3bd391ed150'
    assert response.json()['subscriptions_ids'] == ['00ff1b4a-aeed-4321-8e40-53e78c13685d']


def test_get_topic_returns_404_when_topic_not_found(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = TopicNotFoundError
    handlers.get_topic_handler = dummy_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.get('/topics/925df229-e3cf-4435-88f0-9153b7ff37d6')
    assert response.status_code == 404


def test_get_topic_items_returns_200(handlers: Handlers) -> None:
    dummy_handler = AsyncMock(spec=GetTopicItemsHandler)
    item1 = Item.new(
        uuid=uuid.UUID("1f897d4d-e4bc-40fb-8b58-5d7168c5c5ac"),
        name="item1",
        description="",
        subscription_uuid=uuid.UUID("df836d19-1e78-4880-bf5f-af1c18e4d57d"),
        url=utils.parse_url('https://ae1b82ee.com'),
        thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
        published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    dummy_handler.handle.return_value = [(item1, [])]
    handlers.get_topic_items_handler = dummy_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.get(
        '/topics/1f897d4d-e4bc-40fb-8b58-5d7168c5c5ac/items?'
        'created_before_ts=888.0&page_number=0&page_size=1')
    assert response.status_code == 200
    assert len(response.json()['elements']) == 1
    assert response.json()['next_page'] == ("http://testserver/topics/1f897d4d-e4bc-40fb-8b58-5d7168c5c5ac/items?"
                                            "created_before_ts=888.0&page_number=1&page_size=1")
    assert response.json()['previous_page'] is None


def test_get_topic_items_for_non_existing_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = TopicNotFoundError
    handlers.get_topic_items_handler = dummy_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.get('/topics/925df229-e3cf-4435-88f0-9153b7ff37d6/items?page_number=0&page_size=1')
    assert response.status_code == 404


def test_get_topic_items_parses_query_parameters(handlers: Handlers) -> None:
    dummy_get_topic_items_handler = AsyncMock(spec=GetTopicItemsHandler)
    dummy_get_topic_items_handler.handle.return_value = []
    handlers.get_topic_items_handler = dummy_get_topic_items_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    client.get(
        '/topics/3e9232e7-fa87-4e14-a642-9df94d619c1a/items?'
        'page_number=0&page_size=1&search=test&created_before_ts=0&'
        'max_duration=100&min_duration=10&'
        'include_interactions=without_interactions,recommended,viewed,hidden,discouraged')
    dummy_get_topic_items_handler.handle.assert_called_once_with(
        user_id=USER_UUID,
        topic_id=uuid.UUID("3e9232e7-fa87-4e14-a642-9df94d619c1a"),
        created_before=datetime.fromtimestamp(0, tz=timezone.utc),
        page_number=0,
        page_size=1,
        text_filter='test',
        min_duration=10,
        max_duration=100,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=True,
        include_viewed_items=True,
        include_hidden_items=True)


def test_get_topic_items_recommended_and_without_interactions(handlers: Handlers) -> None:
    dummy_get_topic_items_handler = AsyncMock(spec=GetTopicItemsHandler)
    dummy_get_topic_items_handler.handle.return_value = []
    handlers.get_topic_items_handler = dummy_get_topic_items_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    client.get(
        '/topics/3e9232e7-fa87-4e14-a642-9df94d619c1a/items?'
        'page_number=0&page_size=1&search=test&created_before_ts=0&'
        'include_interactions=without_interactions,recommended')
    dummy_get_topic_items_handler.handle.assert_called_once_with(
        user_id=USER_UUID,
        topic_id=uuid.UUID("3e9232e7-fa87-4e14-a642-9df94d619c1a"),
        created_before=datetime.fromtimestamp(0, tz=timezone.utc),
        page_number=0,
        page_size=1,
        text_filter='test',
        min_duration=None,
        max_duration=None,
        include_items_without_interactions=True,
        include_recommended_items=True,
        include_discouraged_items=False,
        include_viewed_items=False,
        include_hidden_items=False)


def test_assign_subscription_to_topic_returns_200(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.post(
        '/topics/f22b92da-5b90-455f-8141-fb4a37f07805/subscriptions/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8')
    assert response.status_code == 201
    assert response.content == b''


def test_assign_non_existing_subscription_to_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = SubscriptionNotFoundError
    handlers.assign_subscription_to_topic_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.post(
        '/topics/f22b92da-5b90-455f-8141-fb4a37f07805/subscriptions/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8')
    assert response.status_code == 404


def test_assign_subscription_to_non_existing_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = TopicNotFoundError
    handlers.assign_subscription_to_topic_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.post(
        '/topics/f22b92da-5b90-455f-8141-fb4a37f07805/subscriptions/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8')
    assert response.status_code == 404


def test_unassign_subscription_from_topic_returns_204(handlers: Handlers) -> None:
    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.delete(
        '/topics/f22b92da-5b90-455f-8141-fb4a37f07805/subscriptions/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8')
    assert response.status_code == 204
    assert response.content == b''


def test_unassign_non_existing_subscription_from_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = SubscriptionNotFoundError
    handlers.unassign_subscription_from_topic_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.delete(
        '/topics/f22b92da-5b90-455f-8141-fb4a37f07805/subscriptions/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8')
    assert response.status_code == 404


def test_unassign_subscription_from_non_existing_topic_returns_404(handlers: Handlers) -> None:
    dummy_handler = AsyncMock()
    dummy_handler.handle.side_effect = TopicNotFoundError
    handlers.unassign_subscription_from_topic_handler = dummy_handler
    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.delete(
        '/topics/f22b92da-5b90-455f-8141-fb4a37f07805/subscriptions/ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8')
    assert response.status_code == 404


def test_get_subscriptions_items_returns_200(handlers: Handlers) -> None:
    dummy_handler = AsyncMock(spec=GetSubscriptionItemsHandler)
    item1 = Item.new(
        uuid=uuid.UUID("1f897d4d-e4bc-40fb-8b58-5d7168c5c5ac"),
        name="item1",
        description="",
        subscription_uuid=uuid.UUID("df836d19-1e78-4880-bf5f-af1c18e4d57d"),
        url=utils.parse_url('https://ae1b82ee.com'),
        thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
        published_at=datetime.fromtimestamp(0, tz=timezone.utc))
    dummy_handler.handle.return_value = [(item1, [])]
    handlers.get_subscription_items_handler = dummy_handler

    client = TestClient(create_app_from_handlers(handlers), cookies={'token': 'token'})

    response = client.get(
        '/subscriptions/df836d19-1e78-4880-bf5f-af1c18e4d57d/items?'
        'created_before_ts=999.0&page_number=0&page_size=1')
    assert response.status_code == 200
    assert len(response.json()['elements']) == 1
    assert response.json()['next_page'] == (
        'http://testserver/subscriptions/df836d19-1e78-4880-bf5f-af1c18e4d57d/items?'
        'created_before_ts=999.0&page_number=1&page_size=1')
    assert response.json()['previous_page'] is None
