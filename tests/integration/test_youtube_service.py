from datetime import timezone, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.user import User
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.google.youtube_service import YoutubeService, YoutubeApiClient, YoutubeChannel, \
    YoutubeVideo


@pytest.mark.asyncio
async def test_youtube_service_returns_subscriptions_from_user():
    user_repo_mock = MagicMock(spec=UserRepository)
    user_repo_mock.get.return_value = User(
        uuid=UUID("8fed9938-d8f3-4d8d-adc2-8ef0683dbdce"),
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        email="user_email",
        subscription_uuids=[],
        locale="en_US",
        is_admin=False,
        last_name="user_last_name",
        first_name="user_first_name",
        avatar_url=parse_url("https://user_avatar_url.com/image"),
        scanned_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        last_login_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        google_refresh_token="user_google_refresh_token")

    google_service_mock = MagicMock(spec=GoogleAccountService)
    google_service_mock.generate_access_token_from_refresh_token.return_value = "access_token"

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_user_channel.return_value = YoutubeChannel(
        channel_id="channel_id",
        title="channel_title",
        description="channel_description",
        thumbnail_url="https://thumbnail.com/image",
        published_at="2020-01-01T00:00:00Z",
        playlist_id="playlist_id",
        channel_title="channel_title",
        country="country",
        url="https://channel_url.com/channel_id")
    client_mock.get_youtube_subscriptions.return_value = [
        YoutubeChannel(
            channel_id="channel_id",
            title="channel_title",
            description="channel_description",
            thumbnail_url="https://thumbnail.com/image",
            published_at="2020-01-01T00:00:00Z",
            playlist_id="playlist_id",
            channel_title="channel_title",
            country="country",
            url="https://channel_url.com/channel_id")
    ]
    service = YoutubeService(youtube_client=client_mock, api_key="api_key", google_account_service=google_service_mock,
                             user_repository=MagicMock(), subscription_repository=MagicMock())

    subscriptions = await service.get_subscriptions(UUID("8fed9938-d8f3-4d8d-adc2-8ef0683dbdce"))

    assert client_mock.get_youtube_user_channel.call_count == 1
    client_mock.get_youtube_user_channel.assert_called_with("access_token")

    assert client_mock.get_youtube_subscriptions.call_count == 1
    assert len(subscriptions) == 1
    assert subscriptions[0].name == "channel_title"


@pytest.mark.asyncio
async def test_youtube_service_returns_a_single_subscription():
    subs_repo_mock = MagicMock(spec=SubscriptionRepository)
    subs_repo_mock.get.return_value = Subscription(
        uuid=UUID("321cbb52-1398-406e-b278-0a81e85d3274"),
        scanned_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        name="channel_title",
        provider="youtube",
        url=parse_url("https://channel_url.com/channel_id"),
        thumbnail=parse_url("https://thumbnail.com/image"),
        external_data={
            "channel_id": "channel_id",
        },
    )

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_channel.return_value = YoutubeChannel(
        channel_id="channel_id",
        title="channel_title",
        description="channel_description",
        thumbnail_url="https://thumbnail.com/image",
        published_at="2020-01-01T00:00:00Z",
        playlist_id="playlist_id",
        channel_title="channel_title",
        country="country",
        url="https://channel_url.com/channel_id")
    service = YoutubeService(youtube_client=client_mock, api_key="api_key", google_account_service=MagicMock(),
                             user_repository=MagicMock(), subscription_repository=subs_repo_mock)

    subscription = await service.get_subscription(UUID("321cbb52-1398-406e-b278-0a81e85d3274"))

    assert client_mock.get_youtube_channel.call_count == 1
    client_mock.get_youtube_channel.assert_called_with(api_key='api_key', channel_id="channel_id")
    assert subscription is not None
    assert subscription.name == "channel_title"


@pytest.mark.asyncio
async def test_youtube_service_returns_subscription_items():
    subs_repo_mock = MagicMock(spec=SubscriptionRepository)
    subs_repo_mock.get.return_value = Subscription(
        uuid=UUID("321cbb52-1398-406e-b278-0a81e85d3274"),
        scanned_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        name="channel_title",
        provider="youtube",
        url=parse_url("https://channel_url.com/channel_id"),
        thumbnail=parse_url("https://thumbnail.com/image"),
        external_data={
            "channel_id": "channel_123",
            "playlist_id": "playlist_123"
        },
    )

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_videos.return_value = [
        YoutubeVideo(
            video_id="video_id",
            channel_id="channel_123",
            title="video_title",
            country="country",
            channel_url="https://channel_url.com/channel_id",
            thumbnail_url="https://thumbnail.com/image",
            description="video_description",
            published_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            url="https://video_url.com/video_id",
        )
    ]
    service = YoutubeService(youtube_client=client_mock, api_key="api_key", google_account_service=MagicMock(),
                             user_repository=MagicMock(), subscription_repository=subs_repo_mock)

    from_date = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    items = await service.get_items(
        sub_id=UUID("321cbb52-1398-406e-b278-0a81e85d3274"),
        from_date=from_date)

    assert client_mock.get_youtube_videos.call_count == 1
    client_mock.get_youtube_videos.assert_called_with(api_key='api_key',
                                                      playlist_id="playlist_123",
                                                      from_date=from_date)
    assert len(items) == 1
    assert items[0].name == "video_title"
