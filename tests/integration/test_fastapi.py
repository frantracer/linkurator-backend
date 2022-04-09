from fastapi.testclient import TestClient
from linkurator_core.infrastructure.fastapi.app import Handlers, create_app


def test_health_returns_200() -> None:
    client = TestClient(create_app(Handlers(message="Hello")))

    response = client.get('/health')
    assert response.content == b'"Hello"'
    assert response.status_code == 200


def test_health_returns_bye() -> None:
    client = TestClient(create_app(Handlers(message="Bye")))

    response = client.get('/health')
    assert response.content == b'"Bye"'
    assert response.status_code == 200
