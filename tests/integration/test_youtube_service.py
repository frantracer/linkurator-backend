import json
from datetime import timezone, datetime, timedelta
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, call
from uuid import UUID, uuid4

import pytest

from linkurator_core.domain.common.exceptions import InvalidCredentialTypeError
from linkurator_core.domain.common.mock_factory import mock_user, mock_credential, mock_sub
from linkurator_core.domain.common.utils import parse_url
from linkurator_core.domain.items.item import YOUTUBE_ITEM_VERSION, ItemProvider
from linkurator_core.domain.items.item_repository import ItemRepository, ItemFilterCriteria
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.external_service_credential import ExternalServiceType
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.google.account_service import GoogleAccountService
from linkurator_core.infrastructure.google.youtube_api_client import (YoutubeChannel, YoutubeVideo,
                                                                      LiveBroadcastContent, YoutubeApiClient)
from linkurator_core.infrastructure.google.youtube_rss_client import YoutubeRssClient, YoutubeRssItem
from linkurator_core.infrastructure.google.youtube_service import YoutubeService


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


def mock_youtube_video(video_id: Optional[str] = None, channel_id: Optional[str] = None) -> YoutubeVideo:
    video_id = video_id or str(uuid4())
    channel_id = channel_id or str(uuid4())
    return YoutubeVideo(
        video_id=video_id,
        channel_id=channel_id,
        title=f"Title for {video_id}",
        country="country",
        channel_url=f"https://channel_url.com/{channel_id}",
        thumbnail_url=f"https://thumbnail.com/{video_id}",
        description=f"Description for {video_id}",
        published_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        url=f"https://www.youtube.com/watch?v={video_id}",
        duration="PT1H1M1S",
        live_broadcast_content=LiveBroadcastContent.NONE
    )


@pytest.mark.asyncio
async def test_youtube_service_returns_subscriptions_from_user() -> None:
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

    rss_client_mock = AsyncMock(spec=YoutubeRssClient)
    rss_client_mock.get_youtube_items.return_value = []

    service = YoutubeService(youtube_client=client_mock,
                             youtube_rss_client=rss_client_mock,
                             api_key="api_key",
                             google_account_service=google_service_mock,
                             user_repository=MagicMock(),
                             subscription_repository=sub_repo_mock,
                             item_repository=MagicMock(spec=ItemRepository),
                             credentials_repository=credentials_repo)

    subscriptions = await service.get_subscriptions(sub.uuid)

    assert client_mock.get_youtube_subscriptions.call_count == 1
    client_mock.get_youtube_subscriptions.assert_called_with(access_token="access_token", api_key="api_key")
    assert len(subscriptions) == 1
    assert subscriptions[0].name == "channel_title"


@pytest.mark.asyncio
async def test_youtube_service_returns_a_single_subscription_using_the_key_from_a_subscribed_user() -> None:
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

    rss_client_mock = AsyncMock(spec=YoutubeRssClient)
    rss_client_mock.get_youtube_items.return_value = []

    service = YoutubeService(youtube_client=client_mock,
                             youtube_rss_client=rss_client_mock,
                             api_key="api_key",
                             google_account_service=MagicMock(),
                             user_repository=user_repo_mock,
                             subscription_repository=subs_repo_mock,
                             item_repository=MagicMock(spec=ItemRepository),
                             credentials_repository=credentials_repo)

    subscription = await service.get_subscription(sub_id=sub.uuid)

    assert client_mock.get_youtube_channel.call_count == 1
    client_mock.get_youtube_channel.assert_called_with(api_key=credential.credential_value,
                                                       channel_id=youtube_channel.channel_id)
    assert subscription is not None
    assert subscription.name == "channel_title"


@pytest.mark.asyncio
async def test_youtube_service_returns_subscription_items() -> None:
    subs_repo_mock = MagicMock(spec=SubscriptionRepository)
    subs_repo_mock.get.return_value = Subscription(
        uuid=UUID("321cbb52-1398-406e-b278-0a81e85d3274"),
        scanned_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        last_published_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        name="channel_title",
        provider=SubscriptionProvider.YOUTUBE,
        url=parse_url("https://channel_url.com/channel_id"),
        thumbnail=parse_url("https://thumbnail.com/image"),
        external_data={
            "channel_id": "channel_123",
            "playlist_id": "playlist_123"
        },
    )

    video = YoutubeVideo(
        video_id="video_id",
        channel_id="channel_123",
        title="video_title",
        country="country",
        channel_url="https://channel_url.com/channel_id",
        thumbnail_url="https://thumbnail.com/image",
        description="video_description",
        published_at=datetime(2020, 1, 1, 2, 0, 0, tzinfo=timezone.utc),
        url="https://video_url.com/video_id",
        duration="PT1H1M1S",
        live_broadcast_content=LiveBroadcastContent.NONE
    )
    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_videos_from_playlist.return_value = [video]

    rss_client_mock = AsyncMock(spec=YoutubeRssClient)
    rss_client_mock.get_youtube_items.return_value = [
        YoutubeRssItem(
            title=video.title,
            link=video.url,
            published=video.published_at
        )
    ]

    service = YoutubeService(youtube_client=client_mock,
                             youtube_rss_client=rss_client_mock,
                             api_key="api_key",
                             google_account_service=MagicMock(),
                             user_repository=MagicMock(),
                             subscription_repository=subs_repo_mock,
                             item_repository=MagicMock(spec=ItemRepository),
                             credentials_repository=AsyncMock())

    from_date = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    items = await service.get_subscription_items(
        sub_id=UUID("321cbb52-1398-406e-b278-0a81e85d3274"),
        from_date=from_date)

    assert client_mock.get_youtube_videos_from_playlist.call_count == 1
    client_mock.get_youtube_videos_from_playlist.assert_called_with(api_key='api_key',
                                                                    playlist_id="playlist_123",
                                                                    from_date=from_date)
    assert len(items) == 1
    assert items[0].name == "video_title"


@pytest.mark.asyncio
async def test_get_youtube_subscriptions_uses_provided_credentials() -> None:
    user_repo_mock = MagicMock(spec=UserRepository)
    user = mock_user()
    user_repo_mock.get.return_value = user

    google_service_mock = MagicMock(spec=GoogleAccountService)
    google_service_mock.generate_access_token_from_refresh_token.return_value = "access_token"

    credential = mock_credential(user_id=user.uuid)

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_subscriptions.return_value = []

    rss_client_mock = AsyncMock(spec=YoutubeRssClient)
    rss_client_mock.get_youtube_items.return_value = []

    service = YoutubeService(youtube_client=client_mock,
                             youtube_rss_client=rss_client_mock,
                             api_key="api_key",
                             google_account_service=google_service_mock,
                             user_repository=MagicMock(),
                             subscription_repository=MagicMock(),
                             item_repository=MagicMock(spec=ItemRepository),
                             credentials_repository=AsyncMock())

    await service.get_subscriptions(user_id=user.uuid, credential=credential)

    assert client_mock.get_youtube_subscriptions.call_count == 1
    assert client_mock.get_youtube_subscriptions.call_args[1]['api_key'] == credential.credential_value


@pytest.mark.asyncio
async def test_get_youtube_subscriptions_raise_error_if_credential_is_not_a_youtube_api_key() -> None:
    user_repo_mock = MagicMock(spec=UserRepository)
    user = mock_user()
    user_repo_mock.get.return_value = user

    google_service_mock = MagicMock(spec=GoogleAccountService)
    google_service_mock.generate_access_token_from_refresh_token.return_value = "access_token"

    credential = mock_credential(user_id=user.uuid)
    credential.credential_type = ExternalServiceType.OPENAI_API_KEY

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_subscriptions.return_value = []

    rss_client_mock = AsyncMock(spec=YoutubeRssClient)
    rss_client_mock.get_youtube_items.return_value = []

    service = YoutubeService(youtube_client=client_mock,
                             youtube_rss_client=rss_client_mock,
                             api_key="api_key",
                             google_account_service=google_service_mock,
                             user_repository=MagicMock(),
                             subscription_repository=MagicMock(),
                             item_repository=MagicMock(spec=ItemRepository),
                             credentials_repository=AsyncMock())

    with pytest.raises(InvalidCredentialTypeError):
        await service.get_subscriptions(user_id=user.uuid, credential=credential)


@pytest.mark.asyncio
async def test_get_youtube_channel_uses_provided_credentials() -> None:
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

    rss_client_mock = AsyncMock(spec=YoutubeRssClient)
    rss_client_mock.get_youtube_items.return_value = []

    service = YoutubeService(youtube_client=client_mock,
                             youtube_rss_client=rss_client_mock,
                             api_key="api_key",
                             google_account_service=google_service_mock,
                             user_repository=MagicMock(),
                             subscription_repository=subs_repo_mock,
                             item_repository=MagicMock(spec=ItemRepository),
                             credentials_repository=AsyncMock())

    await service.get_subscription(sub_id=sub.uuid, credential=credential)

    assert client_mock.get_youtube_channel.call_count == 1
    assert client_mock.get_youtube_channel.call_args[1]['api_key'] == credential.credential_value


@pytest.mark.asyncio
async def test_get_youtube_channel_raise_error_if_credential_is_not_a_youtube_api_key() -> None:
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

    rss_client_mock = AsyncMock(spec=YoutubeRssClient)
    rss_client_mock.get_youtube_items.return_value = []

    service = YoutubeService(youtube_client=client_mock,
                             youtube_rss_client=rss_client_mock,
                             api_key="api_key",
                             google_account_service=google_service_mock,
                             user_repository=MagicMock(),
                             subscription_repository=subs_repo_mock,
                             item_repository=MagicMock(spec=ItemRepository),
                             credentials_repository=AsyncMock())

    with pytest.raises(InvalidCredentialTypeError):
        await service.get_subscription(sub_id=sub.uuid, credential=credential)


@pytest.mark.asyncio
async def test_get_youtube_videos_from_playlist_uses_provided_credential() -> None:
    youtube_channel = mock_youtube_channel()

    sub = mock_sub()
    sub.external_data = {"playlist_id": youtube_channel.playlist_id}
    subs_repo_mock = MagicMock(spec=SubscriptionRepository)
    subs_repo_mock.get.return_value = sub

    google_service_mock = MagicMock(spec=GoogleAccountService)

    credential = mock_credential()

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_channel.return_value = youtube_channel
    video = mock_youtube_video()
    client_mock.get_youtube_videos_from_playlist.return_value = [video]

    rss_client_mock = AsyncMock(spec=YoutubeRssClient)
    rss_client_mock.get_youtube_items.return_value = [
        YoutubeRssItem(
            title=video.title,
            link=video.url,
            published=video.published_at
        )
    ]

    service = YoutubeService(youtube_client=client_mock,
                             youtube_rss_client=rss_client_mock,
                             api_key="api_key",
                             google_account_service=google_service_mock,
                             user_repository=MagicMock(),
                             subscription_repository=subs_repo_mock,
                             item_repository=MagicMock(spec=ItemRepository),
                             credentials_repository=AsyncMock())

    from_date = video.published_at - timedelta(seconds=1)
    await service.get_subscription_items(sub_id=sub.uuid, from_date=from_date, credential=credential)

    assert client_mock.get_youtube_videos_from_playlist.call_count == 1
    assert client_mock.get_youtube_videos_from_playlist.call_args[1]['api_key'] == credential.credential_value


@pytest.mark.asyncio
async def test_youtube_videos_from_playlist_does_not_ask_youtube_api_if_there_is_no_newer_videos_in_rss() -> None:
    video = mock_youtube_video()

    youtube_channel = mock_youtube_channel()

    sub = mock_sub()
    sub.external_data = {"playlist_id": youtube_channel.playlist_id}
    subs_repo_mock = MagicMock(spec=SubscriptionRepository)
    subs_repo_mock.get.return_value = sub

    google_service_mock = MagicMock(spec=GoogleAccountService)

    credential = mock_credential()

    client_mock = AsyncMock(spec=YoutubeApiClient)
    client_mock.get_youtube_channel.return_value = youtube_channel
    client_mock.get_youtube_videos_from_playlist.return_value = [video]

    rss_client_mock = AsyncMock(spec=YoutubeRssClient)
    rss_client_mock.get_youtube_items.return_value = [
        YoutubeRssItem(
            title=video.title,
            link=video.url,
            published=video.published_at
        )
    ]

    service = YoutubeService(youtube_client=client_mock,
                             youtube_rss_client=rss_client_mock,
                             api_key="api_key",
                             google_account_service=google_service_mock,
                             user_repository=MagicMock(),
                             subscription_repository=subs_repo_mock,
                             item_repository=MagicMock(spec=ItemRepository),
                             credentials_repository=AsyncMock())

    items = await service.get_subscription_items(sub_id=sub.uuid,
                                                 from_date=video.published_at + timedelta(seconds=1),
                                                 credential=credential)

    assert len(items) == 0
    assert rss_client_mock.get_youtube_items.call_count == 1
    assert client_mock.get_youtube_videos_from_playlist.call_count == 0


@pytest.mark.asyncio
async def test_get_youtube_videos_raise_error_if_credential_is_not_a_youtube_api_key() -> None:
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
    video = mock_youtube_video()
    client_mock.get_youtube_videos_from_playlist.return_value = [video]

    rss_client_mock = AsyncMock(spec=YoutubeRssClient)
    rss_client_mock.get_youtube_items.return_value = [
        YoutubeRssItem(
            title=video.title,
            link=video.url,
            published=video.published_at
        )
    ]

    service = YoutubeService(youtube_client=client_mock,
                             youtube_rss_client=rss_client_mock,
                             api_key="api_key",
                             google_account_service=google_service_mock,
                             user_repository=MagicMock(),
                             subscription_repository=subs_repo_mock,
                             item_repository=MagicMock(spec=ItemRepository),
                             credentials_repository=AsyncMock())

    with pytest.raises(InvalidCredentialTypeError):
        from_date = video.published_at - timedelta(seconds=1)
        await service.get_subscription_items(sub_id=sub.uuid, from_date=from_date, credential=credential)


@pytest.mark.asyncio
async def test_get_youtube_videos_returns_all_available_videos() -> None:
    video1 = mock_youtube_video(video_id="video1")
    video2 = mock_youtube_video(video_id="video2")

    youtube_client_mock = AsyncMock(spec=YoutubeApiClient)
    youtube_client_mock.get_youtube_videos.return_value = [video1, video2]

    sub_uuid = UUID("f39fc4fe-be96-4771-a631-c40a3860c881")
    item1 = video1.to_item(item_id=UUID("df1f7fb3-fcf7-4d1b-9bcd-cd341359fe67"), sub_id=sub_uuid)
    item2 = video2.to_item(item_id=UUID("750db5f8-525c-4434-82a8-6cb7bef05481"), sub_id=sub_uuid)
    random_item_uuid = uuid4()

    item_repo_mock = MagicMock(spec=ItemRepository)
    item_repo_mock.find_items.return_value = [item1, item2]

    rss_client_mock = AsyncMock(spec=YoutubeRssClient)
    rss_client_mock.get_youtube_items.return_value = []

    service = YoutubeService(youtube_client=youtube_client_mock,
                             youtube_rss_client=rss_client_mock,
                             api_key="api_key",
                             google_account_service=MagicMock(spec=GoogleAccountService),
                             user_repository=MagicMock(spec=UserRepository),
                             subscription_repository=MagicMock(spec=SubscriptionRepository),
                             item_repository=item_repo_mock,
                             credentials_repository=AsyncMock(spec=ExternalCredentialRepository))

    updated_items = await service.get_items(item_ids={item1.uuid, item2.uuid, random_item_uuid}, credential=None)

    assert len(updated_items) == 2
    assert {item1.uuid, item2.uuid} == {item.uuid for item in updated_items}

    assert youtube_client_mock.get_youtube_videos.call_count == 1
    assert item_repo_mock.find_items.call_count == 1
    assert item_repo_mock.find_items.call_args == call(
        criteria=ItemFilterCriteria(item_ids={item1.uuid, item2.uuid, random_item_uuid}),
        page_number=0, limit=3)


def test_youtube_video_parsing() -> None:
    video_json = '''

    {
      "kind": "youtube#video",
      "etag": "je9B2E53VF3MnXHWrugb_rbPsqQ",
      "id": "Ks-_Mh1QhMc",
      "snippet": {
        "publishedAt": "2012-10-01T15:27:35Z",
        "channelId": "UCAuUUnT6oDeKwE6v1NGQxug",
        "title": "Your body language may shape who you are | Amy Cuddy",
        "description": "Body language affects how others see us, but it may also change how we see ourselves",
        "thumbnails": {
          "default": {
            "url": "https://i.ytimg.com/vi/Ks-_Mh1QhMc/default.jpg",
            "width": 120,
            "height": 90
          },
          "medium": {
            "url": "https://i.ytimg.com/vi/Ks-_Mh1QhMc/mqdefault.jpg",
            "width": 320,
            "height": 180
          },
          "high": {
            "url": "https://i.ytimg.com/vi/Ks-_Mh1QhMc/hqdefault.jpg",
            "width": 480,
            "height": 360
          },
          "standard": {
            "url": "https://i.ytimg.com/vi/Ks-_Mh1QhMc/sddefault.jpg",
            "width": 640,
            "height": 480
          },
          "maxres": {
            "url": "https://i.ytimg.com/vi/Ks-_Mh1QhMc/maxresdefault.jpg",
            "width": 1280,
            "height": 720
          }
        },
        "channelTitle": "TED",
        "tags": [
          "Amy Cuddy",
          "TED",
          "TEDTalk",
          "TEDTalks",
          "TED Talk",
          "TED Talks",
          "TEDGlobal",
          "brain",
          "business",
          "psychology",
          "self",
          "success"
        ],
        "categoryId": "22",
        "liveBroadcastContent": "none",
        "defaultLanguage": "en",
        "localized": {
          "title": "Your body language may shape who you are | Amy Cuddy",
          "description": "Body language affects how others see us, but it may also change how we see ourselves"
        },
        "defaultAudioLanguage": "en"
      },
      "contentDetails": {
        "duration": "PT21M3S",
        "dimension": "2d",
        "definition": "hd",
        "caption": "true",
        "licensedContent": true,
        "contentRating": {},
        "projection": "rectangular"
      },
      "statistics": {
        "viewCount": "23939769",
        "likeCount": "405624",
        "favoriteCount": "0",
        "commentCount": "9597"
      }
    }
    '''

    video = YoutubeVideo.from_dict(json.loads(video_json))
    item = video.to_item(item_id=UUID("321cbb52-1398-406e-b278-0a81e85d3274"),
                         sub_id=UUID("f1edd7fe-a588-485b-b85c-3c087b9f174f"))

    assert item.uuid == UUID("321cbb52-1398-406e-b278-0a81e85d3274")
    assert item.subscription_uuid == UUID("f1edd7fe-a588-485b-b85c-3c087b9f174f")
    assert item.name == "Your body language may shape who you are | Amy Cuddy"
    assert item.description == "Body language affects how others see us, but it may also change how we see ourselves"
    assert item.thumbnail == parse_url("https://i.ytimg.com/vi/Ks-_Mh1QhMc/mqdefault.jpg")
    assert item.url == parse_url("https://www.youtube.com/watch?v=Ks-_Mh1QhMc")
    assert item.duration == 1263
    assert item.version == YOUTUBE_ITEM_VERSION
    assert item.published_at == datetime(2012, 10, 1, 15, 27, 35, tzinfo=timezone.utc)
    assert item.provider == ItemProvider.YOUTUBE
    assert item.deleted_at is None


def test_youtube_video_with_upcoming_live_for_a_year_parsing() -> None:
    video_json = '''
    {
      "kind": "youtube#video",
      "etag": "je9B2E53VF3MnXHWrugb_rbPsqQ",
      "id": "Ks-_Mh1QhMc",
      "snippet": {
        "publishedAt": "2022-10-01T15:27:35Z",
        "channelId": "UCAuUUnT6oDeKwE6v1NGQxug",
        "title": "Your body language may shape who you are | Amy Cuddy",
        "description": "Body language affects how others see us, but it may also change how we see ourselves",
        "thumbnails": {
          "default": {
            "url": "https://i.ytimg.com/vi/Ks-_Mh1QhMc/default.jpg",
            "width": 120,
            "height": 90
          },
          "medium": {
            "url": "https://i.ytimg.com/vi/Ks-_Mh1QhMc/mqdefault.jpg",
            "width": 320,
            "height": 180
          },
          "high": {
            "url": "https://i.ytimg.com/vi/Ks-_Mh1QhMc/hqdefault.jpg",
            "width": 480,
            "height": 360
          },
          "standard": {
            "url": "https://i.ytimg.com/vi/Ks-_Mh1QhMc/sddefault.jpg",
            "width": 640,
            "height": 480
          },
          "maxres": {
            "url": "https://i.ytimg.com/vi/Ks-_Mh1QhMc/maxresdefault.jpg",
            "width": 1280,
            "height": 720
          }
        },
        "channelTitle": "TED",
        "tags": [],
        "categoryId": "22",
        "liveBroadcastContent": "upcoming",
        "defaultLanguage": "en",
        "localized": {
          "title": "Your body language may shape who you are | Amy Cuddy",
          "description": "Body language affects how others see us, but it may also change how we see ourselves"
        },
        "defaultAudioLanguage": "en"
      },
      "contentDetails": {
        "duration": "P0D",
        "dimension": "2d",
        "definition": "sd",
        "caption": "false",
        "licensedContent": false,
        "contentRating": {},
        "projection": "rectangular"
      },
      "statistics": {
        "viewCount": "23939769",
        "likeCount": "405624",
        "favoriteCount": "0",
        "commentCount": "9597"
      }
    }
    '''

    video = YoutubeVideo.from_dict(json.loads(video_json))
    item = video.to_item(item_id=UUID("321cbb52-1398-406e-b278-0a81e85d3274"),
                         sub_id=UUID("f1edd7fe-a588-485b-b85c-3c087b9f174f"),
                         current_date=datetime(2022, 11, 1, tzinfo=timezone.utc))

    assert item.uuid == UUID("321cbb52-1398-406e-b278-0a81e85d3274")
    assert item.deleted_at is None

    item = video.to_item(item_id=UUID("321cbb52-1398-406e-b278-0a81e85d3274"),
                         sub_id=UUID("f1edd7fe-a588-485b-b85c-3c087b9f174f"),
                         current_date=datetime(2023, 11, 1, tzinfo=timezone.utc))

    assert item.uuid == UUID("321cbb52-1398-406e-b278-0a81e85d3274")
    assert item.deleted_at == datetime(2023, 11, 1, tzinfo=timezone.utc)


def test_youtube_channel_parsing() -> None:
    channel_json = '''
   {
      "kind": "youtube#channel",
      "etag": "MYuyUsm3ivvUB4a8Jiqnv2REvww",
      "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
      "snippet": {
        "title": "Google for Developers",
        "description": "Subscribe to join a community of creative developers and learn the latest in Google technology — from AI and cloud, to mobile and web.Explore more at developers.google.com",
        "customUrl": "@googledevelopers",
        "publishedAt": "2007-08-23T00:34:43Z",
        "thumbnails": {
          "default": {
            "url": "https://yt3.ggpht.com/vY3uYs71A_JwVcigyd2tVRHwuj05_cYktQSuzRCxta-9VFxHFtKjGrwG9WFi8ijXITBL3CwPQQ=s88-c-k-c0x00ffffff-no-rj",
            "width": 88,
            "height": 88
          },
          "medium": {
            "url": "https://yt3.ggpht.com/vY3uYs71A_JwVcigyd2tVRHwuj05_cYktQSuzRCxta-9VFxHFtKjGrwG9WFi8ijXITBL3CwPQQ=s240-c-k-c0x00ffffff-no-rj",
            "width": 240,
            "height": 240
          },
          "high": {
            "url": "https://yt3.ggpht.com/vY3uYs71A_JwVcigyd2tVRHwuj05_cYktQSuzRCxta-9VFxHFtKjGrwG9WFi8ijXITBL3CwPQQ=s800-c-k-c0x00ffffff-no-rj",
            "width": 800,
            "height": 800
          }
        },
        "localized": {
          "title": "Google for Developers",
          "description": "Subscribe to join a community of creative developers and learn the latest in Google technology — from AI and cloud, to mobile and web.Explore more at developers.google.com"
        },
        "country": "US"
      },
      "contentDetails": {
        "relatedPlaylists": {
          "likes": "",
          "uploads": "UU_x5XG1OV2P6uZZ5FSM9Ttw"
        }
      },
      "statistics": {
        "viewCount": "236498490",
        "subscriberCount": "2320000",
        "hiddenSubscriberCount": false,
        "videoCount": "5909"
      }
    }
    '''

    channel = YoutubeChannel.from_dict(json.loads(channel_json))
    sub = channel.to_subscription(sub_id=UUID("1b2e723e-3d6c-4398-96dd-0da41a64007b"))

    assert sub.uuid == UUID("1b2e723e-3d6c-4398-96dd-0da41a64007b")
    assert sub.name == "Google for Developers"
    assert sub.provider == SubscriptionProvider.YOUTUBE
    assert sub.url == parse_url("https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw")
    assert sub.thumbnail == parse_url("https://yt3.ggpht.com/vY3uYs71A_JwVcigyd2tVRHwuj05_cYktQSuzRCxta-"
                                      "9VFxHFtKjGrwG9WFi8ijXITBL3CwPQQ=s240-c-k-c0x00ffffff-no-rj")
    assert sub.external_data == {"channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw", "playlist_id": "UU_x5XG1OV2P6uZZ5FSM9Ttw"}
