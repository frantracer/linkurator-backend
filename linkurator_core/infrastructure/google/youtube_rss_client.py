import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone

from linkurator_core.domain.common.exceptions import InvalidYoutubeRssFeedError
from linkurator_core.infrastructure.asyncio_impl.http_client import AsyncHttpClient


@dataclass
class YoutubeRssItem:
    title: str
    link: str
    published: datetime


class YoutubeRssClient:
    def __init__(self, http_client: AsyncHttpClient = AsyncHttpClient()):
        self.http_client = http_client

    async def get_youtube_items(self, playlist_id: str) -> list[YoutubeRssItem]:
        items = []
        url = youtube_rss_url(playlist_id)

        response = await self.http_client.get(url)
        if response.status == 404:
            return []
        if response.status != 200:
            raise InvalidYoutubeRssFeedError(f"Invalid response status: {response.status}")

        root = ET.fromstring(response.text)

        namespaces = {
            "atom": "http://www.w3.org/2005/Atom"
        }

        item: ET.Element
        for item in root.findall("atom:entry", namespaces):
            title = item.findtext("atom:title", namespaces=namespaces)
            if title is None:
                title = ""

            link_element = item.find("atom:link", namespaces=namespaces)
            link_str = ""
            if link_element is not None:
                link_str = link_element.attrib.get("href", "")

            published_str = item.findtext("atom:published", namespaces=namespaces)
            published_date = datetime.fromtimestamp(0, tz=timezone.utc)
            if published_str is not None:
                try:
                    # format is 2019-06-16T19:58:45+00:00
                    published_date = datetime.strptime(published_str, "%Y-%m-%dT%H:%M:%S+00:00").replace(
                        tzinfo=timezone.utc)
                except ValueError as exception:
                    logging.error("Error parsing published date: %s", exception)

            items.append(YoutubeRssItem(title=title, link=link_str, published=published_date))

        return items


def youtube_rss_url(playlist_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
