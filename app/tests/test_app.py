from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from pytest import mark
from server import app


@pytest.fixture(name="client")
async def fixture_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get('/health')
    assert response.status_code == 200
