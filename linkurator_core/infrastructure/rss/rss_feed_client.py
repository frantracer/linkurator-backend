from __future__ import annotations

import copy
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

from linkurator_core.domain.common.exceptions import InvalidRssFeedError
from linkurator_core.infrastructure.asyncio_impl.http_client import AsyncHttpClient

DEFAULT_FEED_ICON = "https://upload.wikimedia.org/wikipedia/en/4/43/Feed-icon.svg"


@dataclass
class RssFeedItem:
    title: str
    link: str
    description: str
    published: datetime
    thumbnail: str
    raw_data: str


@dataclass
class RssFeedInfo:
    title: str
    link: str
    description: str
    thumbnail: str
    language: str


class RssFeedClient:
    def __init__(self, http_client: AsyncHttpClient = AsyncHttpClient()) -> None:
        self.http_client = http_client

    async def get_feed_info(self, feed_url: str) -> RssFeedInfo:
        """Get feed information from an RSS/Atom feed URL."""
        response = await self.http_client.get(feed_url)
        if response.status == 404:
            msg = f"Feed not found: {feed_url}"
            raise InvalidRssFeedError(msg)
        if response.status != 200:
            msg = f"Invalid response status: {response.status}"
            raise InvalidRssFeedError(msg)

        feed_info = self.parse_feed_info(response.text)

        if feed_info.thumbnail == DEFAULT_FEED_ICON:
            # Try to use the feed URL's domain favicon as a better thumbnail
            favicon_url = urljoin(feed_info.link, "/favicon.ico")
            if await self.http_client.check(favicon_url) == 200:
                feed_info.thumbnail = favicon_url

        return feed_info

    def parse_feed_info(self, xml_string: str) -> RssFeedInfo:
        """
        Parse feed information from an RSS/Atom XML string.

        Args:
        ----
            xml_string: The XML content as a string

        Returns:
        -------
            RssFeedInfo with feed metadata

        Raises:
        ------
            InvalidRssFeedError: If XML parsing fails or format is unknown

        """
        # Pre-process XML to wrap description content in CDATA
        xml_string = self._wrap_descriptions_in_cdata(xml_string)

        # Register any namespaces found in the XML to preserve them during serialization
        self._register_namespaces_from_xml(xml_string)

        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            msg = f"Failed to parse XML: {e}"
            raise InvalidRssFeedError(msg) from e

        # Detect feed type
        if root.tag == "rss":
            return self._parse_rss_feed_info(root)
        if root.tag == "{http://www.w3.org/2005/Atom}feed":
            return self._parse_atom_feed_info(root)

        msg = f"Unknown feed format: {root.tag}"
        raise InvalidRssFeedError(msg)

    async def get_feed_items(self, feed_url: str) -> list[RssFeedItem]:
        """Get items from an RSS/Atom feed URL."""
        response = await self.http_client.get(feed_url)
        if response.status == 404:
            return []
        if response.status != 200:
            msg = f"Invalid response status: {response.status}"
            raise InvalidRssFeedError(msg)

        return self.parse_feed_items(response.text)

    def parse_feed_items(self, xml_string: str) -> list[RssFeedItem]:
        """
        Parse items from an RSS/Atom XML string.

        Args:
        ----
            xml_string: The XML content as a string

        Returns:
        -------
            List of RssFeedItem objects

        Raises:
        ------
            InvalidRssFeedError: If XML parsing fails or format is unknown

        """
        # Pre-process XML to wrap description content in CDATA
        xml_string = self._wrap_descriptions_in_cdata(xml_string)

        # Register any namespaces found in the XML to preserve them during serialization
        self._register_namespaces_from_xml(xml_string)

        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            msg = f"Failed to parse XML: {e}"
            raise InvalidRssFeedError(msg) from e

        # Detect feed type
        if root.tag == "rss":
            return self._parse_rss_items(root)
        if root.tag == "{http://www.w3.org/2005/Atom}feed":
            return self._parse_atom_items(root)

        msg = f"Unknown feed format: {root.tag}"
        raise InvalidRssFeedError(msg)

    def _parse_rss_feed_info(self, root: ET.Element) -> RssFeedInfo:
        """Parse RSS 2.0 feed information."""
        channel = root.find("channel")
        if channel is None:
            msg = "No channel element found in RSS feed"
            raise InvalidRssFeedError(msg)

        title = channel.findtext("title", "").strip()
        link = channel.findtext("link", "").strip()
        description = channel.findtext("description", "").strip()
        language = channel.findtext("language", "").strip()

        # Try to find thumbnail/image
        thumbnail = ""
        image_elem = channel.find("image")
        if image_elem is not None:
            thumbnail = image_elem.findtext("url", "").strip()

        # Try iTunes image as fallback
        if not thumbnail:
            itunes_image = channel.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}image")
            if itunes_image is not None:
                thumbnail = itunes_image.get("href", "")

        # Fallback to a generic RSS icon if no thumbnail found
        if not thumbnail:
            thumbnail = DEFAULT_FEED_ICON

        return RssFeedInfo(
            title=title or "Untitled Feed",
            link=link,
            description=description,
            thumbnail=thumbnail,
            language=language,
        )

    def _parse_atom_feed_info(self, root: ET.Element) -> RssFeedInfo:
        """Parse Atom feed information."""
        namespaces = {"atom": "http://www.w3.org/2005/Atom"}

        title = root.findtext("atom:title", "", namespaces).strip()
        description = root.findtext("atom:subtitle", "", namespaces).strip()

        # Find link
        link = ""
        link_elem = root.find("atom:link[@rel='alternate']", namespaces)
        if link_elem is not None:
            link = link_elem.get("href", "")

        # Try to find logo or icon
        thumbnail = root.findtext("atom:logo", "", namespaces).strip()
        if not thumbnail:
            thumbnail = root.findtext("atom:icon", "", namespaces).strip()
        if not thumbnail:
            thumbnail = DEFAULT_FEED_ICON

        return RssFeedInfo(
            title=title or "Untitled Feed",
            link=link,
            description=description,
            thumbnail=thumbnail,
            language="",
        )

    def _parse_rss_items(self, root: ET.Element) -> list[RssFeedItem]:
        """Parse RSS 2.0 items."""
        items: list[RssFeedItem] = []
        channel = root.find("channel")
        if channel is None:
            return items

        for item_elem in channel.findall("item"):
            title = item_elem.findtext("title", "").strip()
            link = item_elem.findtext("link", "").strip()
            description = item_elem.findtext("description", "").strip()

            # Parse publication date
            pub_date_str = item_elem.findtext("pubDate", "")
            published = self._parse_rfc822_date(pub_date_str)

            # Try to find thumbnail
            thumbnail = ""

            # Try media:thumbnail (common in feeds)
            media_thumbnail = item_elem.find("{http://search.yahoo.com/mrss/}thumbnail")
            if media_thumbnail is not None:
                thumbnail = media_thumbnail.get("url", "")

            # Try enclosure with image type
            if not thumbnail:
                enclosure = item_elem.find("enclosure")
                if enclosure is not None:
                    enclosure_type = enclosure.get("type", "")
                    if enclosure_type.startswith("image/"):
                        thumbnail = enclosure.get("url", "")

            # Try iTunes image
            if not thumbnail:
                itunes_image = item_elem.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}image")
                if itunes_image is not None:
                    thumbnail = itunes_image.get("href", "")

            # Try media:content with image type or nested thumbnail
            if not thumbnail:
                media_content = item_elem.find("{http://search.yahoo.com/mrss/}content")
                if media_content is not None:
                    # First check for nested media:thumbnail
                    nested_thumbnail = media_content.find("{http://search.yahoo.com/mrss/}thumbnail")
                    if nested_thumbnail is not None:
                        thumbnail = nested_thumbnail.get("url", "")
                    # If no nested thumbnail, try using content URL if it's an image
                    elif not thumbnail:
                        media_type = media_content.get("type", "")
                        if media_type.startswith("image/"):
                            thumbnail = media_content.get("url", "")

            # Fallback to generic icon
            if not thumbnail:
                thumbnail = DEFAULT_FEED_ICON

            if title and link:
                # Create minimal RSS structure with root and channel tags
                rss_elem = ET.Element("rss")
                # Copy root attributes
                for key, value in root.attrib.items():
                    rss_elem.set(key, value)
                channel_elem = ET.SubElement(rss_elem, "channel")
                # Copy the item element to avoid modifying the original tree
                item_copy = copy.deepcopy(item_elem)
                channel_elem.append(item_copy)
                raw_data = ET.tostring(rss_elem, encoding="unicode")

                items.append(RssFeedItem(
                    title=title,
                    link=link,
                    description=description,
                    published=published,
                    thumbnail=thumbnail,
                    raw_data=raw_data,
                ))

        return items

    def _parse_atom_items(self, root: ET.Element) -> list[RssFeedItem]:
        """Parse Atom feed items."""
        namespaces = {"atom": "http://www.w3.org/2005/Atom"}
        items: list[RssFeedItem] = []

        for entry in root.findall("atom:entry", namespaces):
            title = entry.findtext("atom:title", "", namespaces).strip()

            # Find link
            link = ""
            link_elem = entry.find("atom:link[@rel='alternate']", namespaces)
            if link_elem is None:
                link_elem = entry.find("atom:link", namespaces)
            if link_elem is not None:
                link = link_elem.get("href", "")

            # Get description/summary/content
            description = entry.findtext("atom:summary", "", namespaces).strip()
            if not description:
                content_elem = entry.find("atom:content", namespaces)
                if content_elem is not None:
                    description = content_elem.text or ""
                    description = description.strip()

            # Parse publication date
            published_str = entry.findtext("atom:published", "", namespaces)
            if not published_str:
                published_str = entry.findtext("atom:updated", "", namespaces)
            published = self._parse_iso8601_date(published_str)

            # Try to find thumbnail
            thumbnail = ""

            # Try media:thumbnail
            media_thumbnail = entry.find("{http://search.yahoo.com/mrss/}thumbnail", namespaces)
            if media_thumbnail is not None:
                thumbnail = media_thumbnail.get("url", "")

            # Try link with type="image/*"
            if not thumbnail:
                img_link = entry.find("atom:link[@type^='image/']", namespaces)
                if img_link is not None:
                    thumbnail = img_link.get("href", "")

            # Fallback to generic icon
            if not thumbnail:
                thumbnail = DEFAULT_FEED_ICON

            if title and link:
                # Create minimal Atom feed structure with root tag
                feed_elem = ET.Element("{http://www.w3.org/2005/Atom}feed")
                # Copy root attributes
                for key, value in root.attrib.items():
                    feed_elem.set(key, value)
                # Copy the entry element to avoid modifying the original tree
                entry_copy = copy.deepcopy(entry)
                feed_elem.append(entry_copy)
                raw_data = ET.tostring(feed_elem, encoding="unicode")

                items.append(RssFeedItem(
                    title=title,
                    link=link,
                    description=description,
                    published=published,
                    thumbnail=thumbnail,
                    raw_data=raw_data,
                ))

        return items

    def _parse_rfc822_date(self, date_str: str) -> datetime:
        """Parse RFC 822 date format (used in RSS 2.0)."""
        if not date_str:
            return datetime.fromtimestamp(0, tz=timezone.utc)

        try:
            # Use email.utils.parsedate_to_datetime which handles RFC 822
            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError) as e:
            logging.exception("Error parsing RFC 822 date: %s", e)
            return datetime.fromtimestamp(0, tz=timezone.utc)

    def _parse_iso8601_date(self, date_str: str) -> datetime:
        """Parse ISO 8601 date format (used in Atom)."""
        if not date_str:
            return datetime.fromtimestamp(0, tz=timezone.utc)

        try:
            # Handle different ISO 8601 formats
            # Example: 2019-06-16T19:58:45+00:00 or 2019-06-16T19:58:45Z
            date_str = date_str.strip()
            if date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"

            return datetime.fromisoformat(date_str)
        except ValueError as e:
            logging.exception("Error parsing ISO 8601 date: %s", e)
            return datetime.fromtimestamp(0, tz=timezone.utc)

    def _register_namespaces_from_xml(self, xml_string: str) -> None:
        """Extract and register all namespace declarations from XML string."""
        # Find all xmlns declarations: xmlns:prefix="uri"
        # This ensures namespace prefixes are preserved when serializing
        pattern = r'xmlns:([a-zA-Z0-9_-]+)="([^"]+)"'
        matches = re.findall(pattern, xml_string)

        for prefix, uri in matches:
            try:
                ET.register_namespace(prefix, uri)
            except Exception as e:
                # Skip if registration fails (e.g., invalid prefix)
                logging.debug("Failed to register namespace %s=%s: %s", prefix, uri, e)

    def _wrap_descriptions_in_cdata(self, xml_string: str) -> str:
        """
        Wrap description tag content in CDATA sections if it contains HTML.

        This allows RSS feeds with HTML content in descriptions to be parsed correctly.
        """
        # Pattern to match description tags
        pattern = r"<description>(.*?)</description>"

        def wrap_if_has_html(match: re.Match[str]) -> str:
            content = match.group(1)

            # Don't wrap if content already has CDATA
            if "<![CDATA[" in content:
                return match.group(0)

            # Check if content contains HTML tags (excluding HTML comments which are OK in XML)
            if "<" in content and ">" in content:
                # Check if it's not just HTML comments
                content_without_comments = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
                if "<" in content_without_comments and ">" in content_without_comments:
                    return f"<description><![CDATA[{content}]]></description>"
            return match.group(0)

        return re.sub(pattern, wrap_if_has_html, xml_string, flags=re.DOTALL)
