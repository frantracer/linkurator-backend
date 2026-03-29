import datetime
from unittest.mock import AsyncMock

import pytest

from linkurator_core.domain.common.mock_factory import mock_sub
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository
from linkurator_core.infrastructure.spotify.spotify_api_client import SpotifyApiClient, SpotifyApiNotFoundError
from linkurator_core.infrastructure.spotify.spotify_service import SpotifySubscriptionService


@pytest.mark.asyncio()
async def test_get_subscription_items_returns_empty_when_show_not_found() -> None:
    spotify_api_client = AsyncMock(spec=SpotifyApiClient)
    spotify_api_client.get_show_episodes.side_effect = SpotifyApiNotFoundError("Show not found: abc123")

    sub_repo = InMemorySubscriptionRepository()
    sub = mock_sub(provider="spotify", url="https://open.spotify.com/show/abc123")
    sub.external_data = {"show_id": "abc123"}
    await sub_repo.add(sub)

    spotify_service = SpotifySubscriptionService(
        spotify_client=spotify_api_client,
        user_repository=InMemoryUserRepository(),
        item_repository=InMemoryItemRepository(),
        subscription_repository=sub_repo,
    )

    items = await spotify_service.get_subscription_items(
        sub_id=sub.uuid,
        from_date=datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
    )

    assert items == []
