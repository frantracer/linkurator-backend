import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

from linkurator_core.application.subscription_service import SubscriptionService
from linkurator_core.common import utils
from linkurator_core.domain.subscription import Subscription
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


class YoutubeService(SubscriptionService):
    def __init__(self, google_account_service: GoogleAccountService, user_repository: UserRepository):
        self.google_account_service = google_account_service
        self.user_repository = user_repository

    def get_subscriptions(self, user_id: uuid.UUID) -> List[Subscription]:
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

        if user is not None and user.google_refresh_token is not None:
            youtube_channels = [map_channel_to_subscription(c) for c in self.get_channels(user.google_refresh_token)]

        return youtube_channels

    def get_channels(self, refresh_token: str) -> List[YoutubeChannel]:
        access_token = self.google_account_service.generate_access_token_from_refresh_token(refresh_token)
        if access_token is None:
            return []

        next_page_token = None
        subscriptions: List[YoutubeChannel] = []

        while True:

            subs_response_json, subs_status_code = YoutubeService._get_youtube_subscriptions(
                access_token, next_page_token)
            if subs_status_code != 200:
                return []

            next_page_token = subs_response_json.get("nextPageToken", None)

            # Get channels associated to the subscriptions
            channel_ids = [d["snippet"]["resourceId"]["channelId"] for d in subs_response_json["items"]]

            channels_response_json, channels_status_code = YoutubeService._get_youtube_channels(
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
    def _get_youtube_subscriptions(access_token: str, next_page_token: Optional[str]) -> Tuple[Dict[str, Any], int]:
        youtube_api_url = "https://youtube.googleapis.com/youtube/v3/subscriptions"

        subs_query_params: Dict[str, Any] = {
            "part": "snippet",
            "mine": "true",
            "maxResults": 50
        }
        if next_page_token is not None:
            subs_query_params["pageToken"] = next_page_token

        url = f"{youtube_api_url}?{urlencode(subs_query_params)}"

        subs_response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})

        return subs_response.json(), subs_response.status_code

    @staticmethod
    def _get_youtube_channels(access_token: str, channel_ids: List[str]) -> Tuple[Dict[str, Any], int]:
        youtube_api_channels_url = "https://youtube.googleapis.com/youtube/v3/channels"

        channels_query_params: Dict[str, Any] = {
            "part": "snippet,contentDetails",
            "id": ",".join(channel_ids),
            "maxResults": 50
        }

        url = f"{youtube_api_channels_url}?{urlencode(channels_query_params)}"

        channels_response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})

        return channels_response.json(), channels_response.status_code
