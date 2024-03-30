from datetime import datetime, timezone

import pytest

from linkurator_core.domain.common.exceptions import InvalidYoutubeRssFeedError
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
async def test_youtube_rss_client_with_invalid_playlist_id() -> None:
    client = YoutubeRssClient()
    with pytest.raises(InvalidYoutubeRssFeedError):
        await client.get_youtube_items("invalid")
