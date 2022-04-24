from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from linkurator_core.infrastructure.fastapi.create_app import Handlers, create_app


def test_health_returns_200() -> None:
    handlers = Handlers(
        validate_token=MagicMock(),
        register_user=MagicMock(),
        google_client=MagicMock()
    )
    client = TestClient(create_app(handlers))

    response = client.get('/health')
    assert response.content == b'"OK"'
    assert response.status_code == 200
