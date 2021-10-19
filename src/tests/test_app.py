from typing import AsyncGenerator
from httpx import AsyncClient
from pytest import fixture
from pytest import mark
from main import app


@fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get('/health')
    assert response.status_code == 200
