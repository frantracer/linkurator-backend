#!/usr/bin/env python3
"""
Manual test script for RSS feed functionality.

This script tests the RSS feed client and service with real RSS feeds.

Usage:
    python scripts/find_rss_feeds.py
"""
import asyncio
import logging

from linkurator_core.infrastructure.asyncio_impl.http_client import AsyncHttpClient
from linkurator_core.infrastructure.rss.rss_feed_client import RssFeedClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)


async def find_rss_feeds(client: RssFeedClient, feed_urls: list[str]) -> None:
    """Test RSS feed client with a real RSS feed."""
    logging.info("=" * 60)
    logging.info("Testing RSS Feed Client")
    logging.info("=" * 60)

    for feed_url in feed_urls:
        logging.info("")
        logging.info("Testing feed: %s", feed_url)
        logging.info("-" * 60)

        try:
            # Get feed info
            feed_info = await client.get_feed_info(feed_url)
            logging.info("✓ Feed Title: %s", feed_info.title)
            logging.info("✓ Feed Link: %s", feed_info.link)
            logging.info("✓ Description: %s...", feed_info.description[:100])
            logging.info("✓ Thumbnail: %s", feed_info.thumbnail)
            logging.info("✓ Language: %s", feed_info.language or "Not specified")

            # Get feed items
            items = await client.get_feed_items(feed_url)
            items = await client.get_feed_items_with_thumbnails(items)

            logging.info("")
            logging.info("✓ Found %d items", len(items))

            if items:
                logging.info("")
                logging.info("First 3 items:")
                for i, item in enumerate(items[:3], 1):
                    logging.info("")
                    logging.info("  %d. %s", i, item.title)
                    logging.info("     Link: %s", item.link)
                    logging.info("     Published: %s", item.published)
                    logging.info("     Description: %s...", item.description[:80])
                    logging.info("     Thumbnail: %s", item.thumbnail)

        except Exception as e:
            logging.exception("✗ Error: %s", e)


async def main() -> None:
    """Run all tests."""
    logging.info("")
    logging.info("=" * 60)
    logging.info("RSS FEED IMPLEMENTATION - MANUAL TEST")
    logging.info("=" * 60)

    test_feeds = [
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "https://vandal.elespanol.com/xml.cgi",
        "https://www.vidaextra.com/feedburner.xml",
    ]

    http_client = AsyncHttpClient(contact_email="test@email.com")
    rss_client = RssFeedClient(http_client=http_client)

    await find_rss_feeds(rss_client, test_feeds)

    logging.info("")
    logging.info("=" * 60)
    logging.info("All tests completed!")
    logging.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
