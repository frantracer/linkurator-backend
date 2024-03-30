from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from linkurator_core.domain.common.exceptions import InvalidYoutubeRssFeedError
from linkurator_core.infrastructure.asyncio_impl.http_client import AsyncHttpClient, HttpResponse
from linkurator_core.infrastructure.google.youtube_rss_client import YoutubeRssClient, YoutubeRssItem


@pytest.mark.asyncio
async def test_youtube_rss_client() -> None:
    client = YoutubeRssClient()
    items = await client.get_youtube_items("PLdRReisHNBRiQ9IBRA0J4IeIVPI-mzTU8")
    assert len(items) > 0
    assert items[0] == YoutubeRssItem(
        title="Linkurator logo",
        link="https://www.youtube.com/watch?v=FdjkBWJz5eU",
        published=datetime(2023, 7, 30, 18, 42, 26, 0, tzinfo=timezone.utc)
    )


@pytest.mark.asyncio
async def test_youtube_rss_client_with_invalid_playlist_id_returns_nothing() -> None:
    client = YoutubeRssClient()
    items = await client.get_youtube_items("invalid")
    assert items == []


@pytest.mark.asyncio
async def test_youtube_rss_client_with_invalid_response_status_raises_exception() -> None:
    aiohttp_client = AsyncMock(spec=AsyncHttpClient)
    aiohttp_client.get = AsyncMock(return_value=HttpResponse(text="", status=500))
    client = YoutubeRssClient(http_client=aiohttp_client)
    with pytest.raises(InvalidYoutubeRssFeedError):
        await client.get_youtube_items("mocked_playlist_id")
