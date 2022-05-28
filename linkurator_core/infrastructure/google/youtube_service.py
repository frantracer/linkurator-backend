from dataclasses import dataclass
from typing import List, Dict, Any
from urllib.parse import urlencode

import requests

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


class YoutubeService:
    def __init__(self, google_account_service: GoogleAccountService, refresh_token: str):
        self.google_account_service = google_account_service
        self.refresh_token = refresh_token

    def get_subscriptions(self) -> List[YoutubeChannel]:

        access_token = self.google_account_service.generate_access_token_from_refresh_token(self.refresh_token)
        if access_token is None:
            return []

        youtube_api_url = "https://youtube.googleapis.com/youtube/v3/subscriptions"
        youtube_api_channels_url =  "https://youtube.googleapis.com/youtube/v3/channels"
        next_page_token = None
        subscriptions: List[YoutubeChannel] = []

        while True:
            # Get subscriptions
            subs_query_params: Dict[str, Any] = {
                "part": "snippet",
                "mine": "true",
                "maxResults": 50
            }
            if next_page_token is not None:
                subs_query_params["pageToken"] = next_page_token

            url = f"{youtube_api_url}?{urlencode(subs_query_params)}"

            subs_response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})

            if subs_response.status_code != 200:
                return []

            subs_response_json = subs_response.json()

            next_page_token = subs_response_json.get("nextPageToken", None)

            # Get channels associated to the subscriptions
            channels_query_params: Dict[str, Any] = {
                "part": "snippet,contentDetails",
                "id": ",".join([d["snippet"]["resourceId"]["channelId"] for d in subs_response_json["items"]]),
                "maxResults": 50
            }

            url = f"{youtube_api_channels_url}?{urlencode(channels_query_params)}"

            channels_response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})

            if subs_response.status_code != 200:
                return []

            channels_response_json = channels_response.json()

            # Join subscription and channel information
            youtube_subscriptions = list(subs_response_json["items"])
            youtube_subscriptions.sort(key=lambda i: i["snippet"]["resourceId"]["channelId"])
            youtube_channels = list(channels_response_json["items"])
            youtube_channels.sort(key=lambda i: i["id"])

            subscriptions = subscriptions + [YoutubeChannel.from_dict(c) for c in youtube_channels]

            # Stop if there are no more subscription to process
            if next_page_token is None:
                break

        return subscriptions
