import datetime
from unittest.mock import AsyncMock

import pytest
from pydantic import AnyUrl

from linkurator_core.domain.common.mock_factory import mock_sub, mock_item
from linkurator_core.domain.items.item import ItemProvider
from linkurator_core.domain.subscriptions.subscription import SubscriptionProvider
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.in_memory.user_repository import InMemoryUserRepository
from linkurator_core.infrastructure.spotify.spotify_api_client import Show, ShowImage, SpotifyApiClient, Episode, \
    ReleaseDataPrecision
from linkurator_core.infrastructure.spotify.spotify_service import SpotifySubscriptionService


def mock_spotify_show(
        show_id: str = '0sGGLIDnnijRPLef7InllD',
        show_name: str = 'Entiende Tu Mente',
        total_episodes: int = 20
) -> Show:
    return Show(
        id=show_id,
        name=show_name,
        total_episodes=total_episodes,
        images=[
            ShowImage(url=AnyUrl('https://show.com/image/big.jpg'),
                      height=640, width=640),
            ShowImage(url=AnyUrl('https://show.com/image/medium.jpg'),
                      height=300, width=300),
            ShowImage(url=AnyUrl('https://show.com/image/small.jpg'),
                      height=64, width=64)
        ],
    )


def mock_spotify_episode(
        description: str = '¿Sientes que ciertas creencias del pasado te están limitando en el presente?',
        duration_ms: int = 986984,
        episode_id: str = '0ChojfC3l3XHOWy6uV7vQb',
        name: str = 'Aprender a desaprender | 360',
        release_date: str = '2024-11-20',
        release_date_precision: ReleaseDataPrecision = ReleaseDataPrecision.DAY
) -> Episode:
    return Episode(
        description=description,
        duration_ms=duration_ms,
        id=episode_id,
        name=name,
        release_date=release_date,
        release_date_precision=release_date_precision,
        images=[
            ShowImage(url=AnyUrl('https://episode.com/image/big.jpg'),
                      height=640, width=640),
            ShowImage(url=AnyUrl('https://episode.com/image/medium.jpg'),
                      height=300, width=300),
            ShowImage(url=AnyUrl('https://episode.com/image/small.jpg'),
                      height=64, width=64)
        ],
    )


def mock_spotify_service() -> SpotifySubscriptionService:
    return SpotifySubscriptionService(
        spotify_client=AsyncMock(spec=SpotifyApiClient),
        user_repository=InMemoryUserRepository(),
        item_repository=InMemoryItemRepository(),
        subscription_repository=InMemorySubscriptionRepository()
    )


@pytest.mark.asyncio
async def test_get_subscription_from_name() -> None:
    spotify_show = mock_spotify_show()

    spotify_api_client = AsyncMock(spec=SpotifyApiClient)
    spotify_api_client.find_show.return_value = spotify_show

    spotify_service = mock_spotify_service()
    spotify_service.spotify_client = spotify_api_client

    subscriptions = await spotify_service.get_subscriptions_from_name("Entiende Tu Mente")

    assert len(subscriptions) == 1
    subscription = subscriptions[0]
    assert subscription.uuid is not None
    assert subscription.name == spotify_show.name
    assert subscription.provider == SubscriptionProvider.SPOTIFY
    assert subscription.url == AnyUrl(f"https://open.spotify.com/show/{spotify_show.id}")
    assert subscription.thumbnail == AnyUrl("https://show.com/image/medium.jpg")
    assert subscription.external_data == {
        "show_id": spotify_show.id,
    }
    assert subscription.created_at is not None
    assert subscription.updated_at is not None
    assert subscription.scanned_at is not None
    assert subscription.last_published_at is not None
    spotify_api_client.find_show.assert_called_once_with(spotify_show.name)


@pytest.mark.asyncio
async def test_get_subscription_from_url() -> None:
    spotify_show = mock_spotify_show()

    spotify_api_client = AsyncMock(spec=SpotifyApiClient)
    spotify_api_client.get_shows.return_value = [spotify_show]

    spotify_service = mock_spotify_service()
    spotify_service.spotify_client = spotify_api_client

    subscription = await spotify_service.get_subscription_from_url(
        AnyUrl(f"https://open.spotify.com/show/{spotify_show.id}"))

    assert subscription is not None
    assert subscription.uuid is not None
    assert subscription.name == "Entiende Tu Mente"
    assert subscription.provider == SubscriptionProvider.SPOTIFY
    assert subscription.url == AnyUrl(f"https://open.spotify.com/show/{spotify_show.id}")
    assert subscription.thumbnail == AnyUrl("https://show.com/image/medium.jpg")
    assert subscription.external_data == {
        "show_id": spotify_show.id,
    }
    assert subscription.created_at is not None
    assert subscription.updated_at is not None
    assert subscription.scanned_at is not None
    assert subscription.last_published_at is not None
    spotify_api_client.get_shows.assert_called_once_with([spotify_show.id])


@pytest.mark.asyncio
async def test_get_subscription_from_id() -> None:
    spotify_show = mock_spotify_show()

    spotify_api_client = AsyncMock(spec=SpotifyApiClient)
    spotify_api_client.get_shows.return_value = [spotify_show]

    sub_repo = InMemorySubscriptionRepository()
    sub = mock_sub()
    sub.external_data = {
        "show_id": spotify_show.id,
    }
    await sub_repo.add(sub)

    spotify_service = mock_spotify_service()
    spotify_service.spotify_client = spotify_api_client
    spotify_service.subscription_repository = sub_repo

    subscription = await spotify_service.get_subscription(sub.uuid)

    assert subscription is not None
    assert subscription.uuid == sub.uuid
    assert subscription.name == spotify_show.name
    assert subscription.provider == SubscriptionProvider.SPOTIFY
    assert subscription.url == AnyUrl(f"https://open.spotify.com/show/{spotify_show.id}")
    assert subscription.thumbnail == AnyUrl("https://show.com/image/medium.jpg")
    assert subscription.external_data == {
        "show_id": spotify_show.id,
    }
    assert subscription.created_at is not None
    assert subscription.updated_at is not None
    assert subscription.scanned_at is not None
    assert subscription.last_published_at is not None
    spotify_api_client.get_shows.assert_called_once_with([spotify_show.id])


@pytest.mark.asyncio
async def test_get_items() -> None:
    spotify_episode = mock_spotify_episode(
        duration_ms=999500
    )

    spotify_api_client = AsyncMock(spec=SpotifyApiClient)
    spotify_api_client.get_episodes.return_value = [spotify_episode]

    item_repo = InMemoryItemRepository()
    item = mock_item()
    item.provider = ItemProvider.SPOTIFY
    item.url = AnyUrl(f"https://open.spotify.com/episode/{spotify_episode.id}")
    await item_repo.upsert_items([item])

    spotify_service = mock_spotify_service()
    spotify_service.spotify_client = spotify_api_client
    spotify_service.item_repository = item_repo

    items = list(await spotify_service.get_items(item_ids={item.uuid}))

    assert len(items) == 1
    assert items[0].uuid == item.uuid
    assert items[0].name == spotify_episode.name
    assert items[0].url == item.url
    assert items[0].thumbnail == AnyUrl("https://episode.com/image/medium.jpg")
    assert items[0].description == spotify_episode.description
    assert items[0].duration == 1000
    assert items[0].published_at == datetime.datetime(2024, 11, 20, tzinfo=datetime.timezone.utc)
    assert items[0].created_at is not None
    assert items[0].updated_at is not None
    spotify_api_client.get_episodes.assert_called_once_with([spotify_episode.id])
