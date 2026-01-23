from unittest.mock import MagicMock

from linkurator_core.application.subscriptions.get_providers_handler import GetProvidersHandler
from linkurator_core.domain.subscriptions.subscription_service import SubscriptionService


def mock_subscription_service(name: str, alias: str, thumbnail: str) -> SubscriptionService:
    service = MagicMock(spec=SubscriptionService)
    service.provider_name.return_value = name
    service.provider_alias.return_value = alias
    service.provider_thumbnail.return_value = thumbnail
    return service


def test_get_providers_returns_all_providers() -> None:
    # Given
    youtube_service = mock_subscription_service(
        name="youtube",
        alias="YouTube",
        thumbnail="https://youtube.com/favicon.png",
    )
    spotify_service = mock_subscription_service(
        name="spotify",
        alias="Spotify",
        thumbnail="https://spotify.com/favicon.png",
    )
    rss_service = mock_subscription_service(
        name="rss",
        alias="RSS",
        thumbnail="https://rss.com/favicon.png",
    )

    handler = GetProvidersHandler(
        subscription_services=[youtube_service, spotify_service, rss_service],
    )

    # When
    providers = handler.handle()

    # Then
    assert len(providers) == 3
    assert providers[0].name == "youtube"
    assert providers[0].alias == "YouTube"
    assert providers[0].thumbnail == "https://youtube.com/favicon.png"
    assert providers[1].name == "spotify"
    assert providers[1].alias == "Spotify"
    assert providers[2].name == "rss"
    assert providers[2].alias == "RSS"


def test_get_providers_returns_empty_list_when_no_services() -> None:
    # Given
    handler = GetProvidersHandler(subscription_services=[])

    # When
    providers = handler.handle()

    # Then
    assert providers == []


def test_get_providers_returns_single_provider() -> None:
    # Given
    youtube_service = mock_subscription_service(
        name="youtube",
        alias="YouTube",
        thumbnail="https://youtube.com/favicon.png",
    )

    handler = GetProvidersHandler(subscription_services=[youtube_service])

    # When
    providers = handler.handle()

    # Then
    assert len(providers) == 1
    assert providers[0].name == "youtube"
