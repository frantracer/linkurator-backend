from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode
import uuid

import aiohttp

from linkurator_core.application.subscription_service import SubscriptionService
from linkurator_core.common import utils
from linkurator_core.domain.item import Item
from linkurator_core.domain.subscription import Subscription
from linkurator_core.domain.subscription_repository import SubscriptionRepository
from linkurator_core.domain.user_repository import UserRepository
from linkurator_core.infrastructure.google.account_service import GoogleAccountService


@dataclass
class YoutubeChannel:
    title: str
    channel_id: str
    channel_title: str
    description: str
    published_at: str
    thumbnail_url: str
    url: str
    playlist_id: str
    country: str

    @staticmethod
    def from_dict(channel: dict):
        return YoutubeChannel(
            title=channel["snippet"]["title"],
            channel_id=channel["id"],
            channel_title=channel["snippet"]["title"],
            description=channel["snippet"]["description"],
            published_at=channel["snippet"]["publishedAt"],
            thumbnail_url=channel["snippet"]["thumbnails"]["default"]["url"],
            url=f'https://www.youtube.com/channel/{channel["id"]}',
            playlist_id=channel["contentDetails"]["relatedPlaylists"]["uploads"],
            country=channel['snippet'].get('country', '')
        )


@dataclass
class YoutubeVideo:
    title: str
    video_id: str
    published_at: datetime
    thumbnail_url: str
    url: str
    channel_id: str
    channel_url: str
    country: str

    @staticmethod
    def from_dict(video: dict):
        return YoutubeVideo(
            title=video["snippet"]["title"],
            video_id=video["id"],
            published_at=datetime.strptime(video["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"),
            thumbnail_url=video["snippet"]["thumbnails"]["default"]["url"],
            url=f'https://www.youtube.com/watch?v={video["id"]}',
            channel_id=video["snippet"]["channelId"],
            channel_url=f'https://www.youtube.com/channel/{video["snippet"]["channelId"]}',
            country=video['snippet'].get('country', '')
        )


class YoutubeService(SubscriptionService):
    def __init__(self, google_account_service: GoogleAccountService, user_repository: UserRepository,
                 subscription_repository: SubscriptionRepository, api_key: str):
        self.google_account_service = google_account_service
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.api_key = api_key

    async def get_subscriptions(self, user_id: uuid.UUID) -> List[Subscription]:
        user = self.user_repository.get(user_id)
        youtube_channels = []

        def map_channel_to_subscription(channel: YoutubeChannel) -> Subscription:
            return Subscription.new(
                uuid=uuid.uuid4(),
                name=channel.title,
                provider="youtube",
                external_data={
                    "channel_id": channel.channel_id,
                    "playlist_id": channel.playlist_id
                },
                url=utils.parse_url(channel.url),
                thumbnail=utils.parse_url(channel.thumbnail_url)
            )

        access_token = None
        if user is not None and user.google_refresh_token is not None:
            access_token = self.google_account_service.generate_access_token_from_refresh_token(
                user.google_refresh_token)

        if access_token is not None:
            youtube_channels = [map_channel_to_subscription(c)
                                for c in await YoutubeService.get_youtube_channels(access_token)]

        return youtube_channels

    async def get_items(self, sub_id: uuid.UUID, from_date: datetime) -> List[Item]:
        subscription = self.subscription_repository.get(sub_id)
        if subscription is None or subscription.provider != "youtube":
            return []

        def map_video_to_item(video: YoutubeVideo) -> Item:
            return Item.new(
                uuid=uuid.uuid4(),
                subscription_uuid=sub_id,
                name=video.title,
                url=utils.parse_url(video.url),
                thumbnail=utils.parse_url(video.thumbnail_url)
            )

        videos = await YoutubeService.get_youtube_videos(
            api_key=self.api_key,
            playlist_id=subscription.external_data["playlist_id"],
            from_date=from_date)

        return [map_video_to_item(v) for v in videos]

    @staticmethod
    async def get_youtube_channels(access_token: str) -> List[YoutubeChannel]:
        next_page_token = None
        subscriptions: List[YoutubeChannel] = []

        while True:
            subs_response_json, subs_status_code = await YoutubeService._request_youtube_subscriptions(
                access_token, next_page_token)
            if subs_status_code != 200:
                return []

            next_page_token = subs_response_json.get("nextPageToken", None)

            # Get channels associated to the subscriptions
            channel_ids = [d["snippet"]["resourceId"]["channelId"] for d in subs_response_json["items"]]

            channels_response_json, channels_status_code = await YoutubeService._request_youtube_channels(
                access_token, channel_ids)
            if channels_status_code != 200:
                return []

            youtube_channels = list(channels_response_json["items"])
            youtube_channels.sort(key=lambda i: i["id"])

            subscriptions = subscriptions + [YoutubeChannel.from_dict(c) for c in youtube_channels]

            # Stop if there are no more subscription to process
            if next_page_token is None:
                break

        return subscriptions

    @staticmethod
    async def get_youtube_videos(api_key: str, playlist_id: str, from_date: datetime) -> List[YoutubeVideo]:
        next_page_token = None
        videos: List[YoutubeVideo] = []

        while True:
            playlist_response_json, playlist_status_code = await YoutubeService._request_youtube_playlist_items(
                api_key, playlist_id, next_page_token)
            if playlist_status_code != 200:
                return []

            next_page_token = playlist_response_json.get("nextPageToken", None)

            # Get videos associated to the playlist
            playlist_items = playlist_response_json["items"]
            filtered_video_ids = [playlist_item["snippet"]["resourceId"]["videoId"]
                                  for playlist_item in playlist_items
                                  if playlist_item["snippet"]["publishedAt"] >= from_date.isoformat()]

            videos_response_json, videos_status_code = await YoutubeService._request_youtube_videos(
                api_key, filtered_video_ids)
            if videos_status_code != 200:
                return []

            youtube_videos = list(videos_response_json["items"])
            youtube_videos.sort(key=lambda i: i["id"])

            videos = videos + [YoutubeVideo.from_dict(v) for v in youtube_videos]

            # Stop if there are no more videos to process
            if next_page_token is None or len(filtered_video_ids) < len(playlist_items):
                break

        videos.sort(key=lambda i: i.published_at, reverse=True)
        return videos

    @staticmethod
    async def _request_youtube_subscriptions(
            access_token: str, next_page_token: Optional[str]
    ) -> Tuple[Dict[str, Any], int]:
        youtube_api_url = "https://youtube.googleapis.com/youtube/v3/subscriptions"

        subs_query_params: Dict[str, Any] = {
            "part": "snippet",
            "mine": "true",
            "maxResults": 50
        }
        if next_page_token is not None:
            subs_query_params["pageToken"] = next_page_token

        url = f"{youtube_api_url}?{urlencode(subs_query_params)}"

        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {access_token}"}) as session:
            async with session.get(url) as resp:
                resp_body = await resp.json()
                resp_status = resp.status

        return resp_body, resp_status

    @staticmethod
    async def _request_youtube_channels(access_token: str, channel_ids: List[str]) -> Tuple[Dict[str, Any], int]:
        youtube_api_channels_url = "https://youtube.googleapis.com/youtube/v3/channels"

        channels_query_params: Dict[str, Any] = {
            "part": "snippet,contentDetails",
            "id": ",".join(channel_ids),
            "maxResults": 50
        }

        url = f"{youtube_api_channels_url}?{urlencode(channels_query_params)}"

        async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {access_token}"}) as session:
            async with session.get(url) as resp:
                resp_body = await resp.json()
                resp_status = resp.status

        return resp_body, resp_status

    @staticmethod
    async def _request_youtube_playlist_items(
            api_key: str, playlist_id: str, next_page_token: Optional[str]
    ) -> Tuple[Dict[str, Any], int]:
        youtube_api_url = "https://youtube.googleapis.com/youtube/v3/playlistItems"

        playlist_items_query_params: Dict[str, Any] = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
            "key": api_key
        }
        if next_page_token is not None:
            playlist_items_query_params["pageToken"] = next_page_token

        url = f"{youtube_api_url}?{urlencode(playlist_items_query_params)}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp_body = await resp.json()
                resp_status = resp.status

        return resp_body, resp_status

    @staticmethod
    async def _request_youtube_videos(
            api_key: str, video_ids: List[str]
    ) -> Tuple[Dict[str, Any], int]:
        youtube_api_videos_url = "https://youtube.googleapis.com/youtube/v3/videos"

        videos_query_params: Dict[str, Any] = {
            "part": "snippet,contentDetails",
            "id": ",".join(video_ids),
            "maxResults": 50,
            "key": api_key
        }

        url = f"{youtube_api_videos_url}?{urlencode(videos_query_params)}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp_body = await resp.json()
                resp_status = resp.status

        return resp_body, resp_status
