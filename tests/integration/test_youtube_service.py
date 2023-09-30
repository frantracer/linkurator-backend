from datetime import timezone, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from linkurator_core.domain.common.exceptions import InvalidCredentialTypeError
from linkurator_core.domain.common.mock_factory import mock_user, mock_credential, mock_sub
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.external_service_credential import ExternalServiceType
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.google.youtube_service import YoutubeService, YoutubeApiClient, YoutubeChannel, \
    YoutubeVideo


def mock_youtube_channel(channel_id: str = "channel_id") -> YoutubeChannel:
    return YoutubeChannel(
        channel_id=channel_id,
        title=f"Title for {channel_id}",
        description=f"Description for {channel_id}",
        thumbnail_url=f"https://thumbnail.com/{channel_id}/image",
        published_at="2020-01-01T00:00:00Z",
        playlist_id=f"playlist_id_{channel_id}",
        channel_title=f"Title for {channel_id}",
        country="country",
        url=f"https://channel_url.com/{channel_id}")


@pytest.mark.asyncio
async def test_youtube_service_returns_subscriptions_from_user():
    sub = mock_sub()
    sub_repo_mock = MagicMock(spec=SubscriptionRepository)
    sub_repo_mock.get.return_value = [sub]

    user_repo_mock = MagicMock(spec=UserRepository)
    user = mock_user()
    user_repo_mock.find_users_subscribed_to_subscription.return_value = [user]

    google_service_mock = MagicMock(spec=GoogleAccountService)
    google_service_mock.generate_access_token_from_refresh_token.return_value = "access_token"

    credentials_repo = AsyncMock(spec=ExternalCredentialRepository)
    credentials_repo.find_by_users_and_type.return_value = [mock_credential()]

    client_mock = AsyncMock(spec=YoutubeApiClient)
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
                             user_repository=MagicMock(), subscription_repository=sub_repo_mock,
                             credentials_repository=credentials_repo)

    subscriptions = await service.get_subscriptions(sub.uuid)

    assert client_mock.get_youtube_subscriptions.call_count == 1
    client_mock.get_youtube_subscriptions.assert_called_with(access_token="access_token", api_key="api_key")
    assert len(subscriptions) == 1
    assert subscriptions[0].name == "channel_title"


@pytest.mark.asyncio
async def test_youtube_service_returns_a_single_subscription_using_the_key_from_a_subscribed_user():
    youtube_channel = mock_youtube_channel()

    subs_repo_mock = MagicMock(spec=SubscriptionRepository)
    sub = mock_sub()
    sub.external_data = {"channel_id": youtube_channel.channel_id}
    subs_repo_mock.get.return_value = sub

    user_repo_mock = MagicMock(spec=UserRepository)
    user = mock_user()
    user_repo_mock.find_users_subscribed_to_subscription.return_value = [user]

    credentials_repo = AsyncMock(spec=ExternalCredentialRepository)
    credential = mock_credential(user_id=user.uuid)
    credentials_repo.find_by_users_and_type.return_value = [credential]

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
    service = YoutubeService(youtube_client=client_mock,
                             api_key="api_key",
                             google_account_service=MagicMock(),
                             user_repository=user_repo_mock,
                             subscription_repository=subs_repo_mock,
                             credentials_repository=credentials_repo)

    subscription = await service.get_subscription(sub_id=sub.uuid)

    assert client_mock.get_youtube_channel.call_count == 1
    client_mock.get_youtube_channel.assert_called_with(api_key=credential.credential_value,
                                                       channel_id=youtube_channel.channel_id)
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
        provider=SubscriptionProvider.YOUTUBE,
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
                             user_repository=MagicMock(), subscription_repository=subs_repo_mock,
                             credentials_repository=AsyncMock())

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


@pytest.mark.asyncio
async def test_get_youtube_subscriptions_uses_provided_credentials():
    user_repo_mock = MagicMock(spec=UserRepository)
    user = mock_user()
    user_repo_mock.get.return_value = user

    google_service_mock = MagicMock(spec=GoogleAccountService)
    google_service_mock.generate_access_token_from_refresh_token.return_value = "access_token"

    credential = mock_credential(user_id=user.uuid)

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_subscriptions.return_value = []
    service = YoutubeService(youtube_client=client_mock, api_key="api_key", google_account_service=google_service_mock,
                             user_repository=MagicMock(), subscription_repository=MagicMock(),
                             credentials_repository=AsyncMock())

    await service.get_subscriptions(user_id=user.uuid, credential=credential)

    assert client_mock.get_youtube_subscriptions.call_count == 1
    assert client_mock.get_youtube_subscriptions.call_args[1]['api_key'] == credential.credential_value


@pytest.mark.asyncio
async def test_get_youtube_subscriptions_raise_error_if_credential_is_not_a_youtube_api_key():
    user_repo_mock = MagicMock(spec=UserRepository)
    user = mock_user()
    user_repo_mock.get.return_value = user

    google_service_mock = MagicMock(spec=GoogleAccountService)
    google_service_mock.generate_access_token_from_refresh_token.return_value = "access_token"

    credential = mock_credential(user_id=user.uuid)
    credential.credential_type = ExternalServiceType.OPENAI_API_KEY

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_subscriptions.return_value = []
    service = YoutubeService(youtube_client=client_mock, api_key="api_key", google_account_service=google_service_mock,
                             user_repository=MagicMock(), subscription_repository=MagicMock(),
                             credentials_repository=AsyncMock())

    with pytest.raises(InvalidCredentialTypeError):
        await service.get_subscriptions(user_id=user.uuid, credential=credential)


@pytest.mark.asyncio
async def test_get_youtube_channel_uses_provided_credentials():
    youtube_channel = mock_youtube_channel()

    sub = mock_sub()
    sub.external_data = {"channel_id": youtube_channel.channel_id}
    subs_repo_mock = MagicMock(spec=SubscriptionRepository)
    subs_repo_mock.get.return_value = sub

    google_service_mock = MagicMock(spec=GoogleAccountService)
    google_service_mock.generate_access_token_from_refresh_token.return_value = "access_token"

    credential = mock_credential()

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_channel.return_value = youtube_channel
    service = YoutubeService(youtube_client=client_mock, api_key="api_key", google_account_service=google_service_mock,
                             user_repository=MagicMock(), subscription_repository=subs_repo_mock,
                             credentials_repository=AsyncMock())

    await service.get_subscription(sub_id=sub.uuid, credential=credential)

    assert client_mock.get_youtube_channel.call_count == 1
    assert client_mock.get_youtube_channel.call_args[1]['api_key'] == credential.credential_value


@pytest.mark.asyncio
async def test_get_youtube_channel_raise_error_if_credential_is_not_a_youtube_api_key():
    youtube_channel = mock_youtube_channel()

    sub = mock_sub()
    sub.external_data = {"channel_id": youtube_channel.channel_id}
    subs_repo_mock = MagicMock(spec=SubscriptionRepository)
    subs_repo_mock.get.return_value = sub

    google_service_mock = MagicMock(spec=GoogleAccountService)

    credential = mock_credential()
    credential.credential_type = ExternalServiceType.OPENAI_API_KEY

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_channel.return_value = youtube_channel
    service = YoutubeService(youtube_client=client_mock, api_key="api_key", google_account_service=google_service_mock,
                             user_repository=MagicMock(), subscription_repository=subs_repo_mock,
                             credentials_repository=AsyncMock())

    with pytest.raises(InvalidCredentialTypeError):
        await service.get_subscription(sub_id=sub.uuid, credential=credential)


@pytest.mark.asyncio
async def test_get_youtube_videos_uses_provided_credential():
    youtube_channel = mock_youtube_channel()

    sub = mock_sub()
    sub.external_data = {"playlist_id": youtube_channel.playlist_id}
    subs_repo_mock = MagicMock(spec=SubscriptionRepository)
    subs_repo_mock.get.return_value = sub

    google_service_mock = MagicMock(spec=GoogleAccountService)

    credential = mock_credential()

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_channel.return_value = youtube_channel

    service = YoutubeService(youtube_client=client_mock, api_key="api_key", google_account_service=google_service_mock,
                             user_repository=MagicMock(), subscription_repository=subs_repo_mock,
                             credentials_repository=AsyncMock())

    await service.get_items(sub_id=sub.uuid, from_date=datetime.now(), credential=credential)

    assert client_mock.get_youtube_videos.call_count == 1
    assert client_mock.get_youtube_videos.call_args[1]['api_key'] == credential.credential_value


@pytest.mark.asyncio
async def test_get_youtube_videos_raise_error_if_credential_is_not_a_youtube_api_key():
    youtube_channel = mock_youtube_channel()

    sub = mock_sub()
    sub.external_data = {"playlist_id": youtube_channel.playlist_id}
    subs_repo_mock = MagicMock(spec=SubscriptionRepository)
    subs_repo_mock.get.return_value = sub

    google_service_mock = MagicMock(spec=GoogleAccountService)

    credential = mock_credential()
    credential.credential_type = ExternalServiceType.OPENAI_API_KEY

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_channel.return_value = youtube_channel

    service = YoutubeService(youtube_client=client_mock, api_key="api_key", google_account_service=google_service_mock,
                             user_repository=MagicMock(), subscription_repository=subs_repo_mock,
                             credentials_repository=AsyncMock())

    with pytest.raises(InvalidCredentialTypeError):
        await service.get_items(sub_id=sub.uuid, from_date=datetime.now(), credential=credential)
