from datetime import datetime
from unittest.mock import MagicMock
import uuid

from fastapi.testclient import TestClient
import pytest

from linkurator_core.common import utils
from linkurator_core.domain.item import Item
from linkurator_core.domain.session import Session
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
        get_subscription_items_handler=MagicMock()
    )


def test_health_returns_200(handlers: Handlers) -> None:
    client = TestClient(create_app(handlers))

    response = client.get('/health')
    assert response.content == b'"OK"'
    assert response.status_code == 200


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
