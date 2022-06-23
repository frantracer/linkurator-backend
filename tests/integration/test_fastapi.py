from datetime import datetime, timezone
from unittest.mock import MagicMock
import uuid

from fastapi.testclient import TestClient
import pytest

from linkurator_core.common import utils
from linkurator_core.domain.item import Item
from linkurator_core.domain.session import Session
from linkurator_core.domain.user import User
from linkurator_core.infrastructure.fastapi.create_app import Handlers, create_app


@pytest.fixture(name="handlers")
def dummy_handlers() -> Handlers:
    dummy_validate_token_handler = MagicMock()
    dummy_validate_token_handler.handle.return_value = Session(
        user_id=uuid.uuid4(),
        expires_at=datetime.fromisoformat('3000-01-01T00:00:00'),
        token='token')

    return Handlers(
        validate_token=dummy_validate_token_handler,
        google_client=MagicMock(),
        get_user_subscriptions=MagicMock(),
        get_subscription_items_handler=MagicMock(),
        get_user_profile_handler=MagicMock()
    )


def test_health_returns_200(handlers: Handlers) -> None:
    client = TestClient(create_app(handlers))

    response = client.get('/health')
    assert response.content == b'"OK"'
    assert response.status_code == 200


def test_user_profile_returns_200(handlers: Handlers) -> None:
    dummy_get_user_profile_handler = MagicMock()
    dummy_get_user_profile_handler.handle.return_value = User(
        uuid=uuid.UUID("cb856f4f-8371-4648-af75-38fb34231092"),
        first_name="first name",
        last_name="last name",
        email="test@email.com",
        updated_at=datetime.fromtimestamp(0, tz=timezone.utc),
        created_at=datetime.fromtimestamp(0, tz=timezone.utc),
        scanned_at=datetime.fromtimestamp(0, tz=timezone.utc),
        subscription_uuids=[],
        google_refresh_token="refresh token"
    )
    handlers.get_user_profile_handler = dummy_get_user_profile_handler

    client = TestClient(create_app(handlers))

    response = client.get('/profile', cookies={'token': 'token'})
    assert response.status_code == 200
    assert response.json()['uuid'] == 'cb856f4f-8371-4648-af75-38fb34231092'
    assert response.json()['first_name'] == 'first name'
    assert response.json()['last_name'] == 'last name'
    assert response.json()['email'] == 'test@email.com'
    assert response.json()['created_at'] == '1970-01-01T00:00:00Z'
    assert response.json()['last_scanned_at'] == '1970-01-01T00:00:00Z'


def test_user_profile_returns_404_when_user_not_found(handlers: Handlers) -> None:
    dummy_get_user_profile_handler = MagicMock()
    dummy_get_user_profile_handler.handle.return_value = None
    handlers.get_user_profile_handler = dummy_get_user_profile_handler

    client = TestClient(create_app(handlers))

    response = client.get('/profile', cookies={'token': 'token'})
    assert response.status_code == 404


def test_item_pagination_returns_one_page(handlers: Handlers) -> None:
    item1 = Item.new(name="item1",
                     description="",
                     uuid=uuid.UUID("ae1b82ee-f870-4a1f-a1c8-898c10ce9eb8"),
                     subscription_uuid=uuid.UUID("3e9232e7-fa87-4e14-a642-9df94d619c1a"),
                     url=utils.parse_url('https://ae1b82ee.com'),
                     thumbnail=utils.parse_url('https://test.com/thumbnail.png'),
                     published_at=datetime.fromtimestamp(0))
    dummy_get_subscription_items_handler = MagicMock()
    dummy_get_subscription_items_handler.handle.return_value = ([item1], 1)
    handlers.get_subscription_items_handler = dummy_get_subscription_items_handler

    client = TestClient(create_app(handlers))

    response = client.get(
        '/subscriptions/3e9232e7-fa87-4e14-a642-9df94d619c1a/items?page_number=0&page_size=1',
        cookies={'token': 'token'})
    assert response.status_code == 200
    assert len(response.json()['elements']) == 1
    assert response.json()['next_page'] is None
    assert response.json()['previous_page'] is None
