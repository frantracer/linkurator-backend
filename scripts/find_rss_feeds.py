#!/usr/bin/env python3
"""
Manual test script for RSS feed functionality.

This script tests the RSS feed client and service with real RSS feeds.

Usage:
    python scripts/find_rss_feeds.py
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from linkurator_core.domain.common.utils import parse_url
from linkurator_core.infrastructure.asyncio_impl.http_client import AsyncHttpClient
from linkurator_core.infrastructure.in_memory.item_repository import InMemoryItemRepository
from linkurator_core.infrastructure.in_memory.rss_data_repository import InMemoryRssDataRepository
from linkurator_core.infrastructure.in_memory.subscription_repository import InMemorySubscriptionRepository
from linkurator_core.infrastructure.rss.rss_feed_client import RssFeedClient
from linkurator_core.infrastructure.rss.rss_service import RssSubscriptionService

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


async def find_rss_details(client: RssFeedClient, feed_urls: list[str]) -> None:
    """Test RSS subscription service with a real feed."""
    logging.info("")
    logging.info("=" * 60)
    logging.info("Testing RSS Subscription Service")
    logging.info("=" * 60)

    sub_repo = InMemorySubscriptionRepository()
    item_repo = InMemoryItemRepository()
    rss_data_repo = InMemoryRssDataRepository()
    service = RssSubscriptionService(
        subscription_repository=sub_repo,
        item_repository=item_repo,
        rss_feed_client=client,
        rss_data_repository=rss_data_repo,
    )

    # Test getting subscription from URL
    for feed_url in feed_urls:
        logging.info("")
        logging.info("Creating subscription from URL: %s", feed_url)
        logging.info("-" * 60)

        try:
            subscription = await service.get_subscription_from_url(parse_url(feed_url))

            if subscription:
                logging.info("✓ Subscription created: %s", subscription.name)
                logging.info("✓ Provider: %s", subscription.provider)
                logging.info("✓ URL: %s", subscription.url)
                logging.info("✓ Description: %s...", subscription.description[:100])
                logging.info("✓ Feed URL: %s", subscription.external_data.get("feed_url"))

                # Save subscription
                await sub_repo.add(subscription)
                logging.info("✓ Subscription saved with ID: %s", subscription.uuid)

                # Test getting items
                from_date = datetime.now(tz=timezone.utc) - timedelta(days=30)
                logging.info("")
                logging.info("Getting items published after %s", from_date.date())
                logging.info("-" * 60)

                items = await service.get_subscription_items(subscription.uuid, from_date)
                logging.info("✓ Found %d items", len(items))

                if items:
                    logging.info("")
                    logging.info("First 3 items:")
                    for i, item in enumerate(items[:3], 1):
                        logging.info("")
                        logging.info("  %d. %s", i, item.name)
                        logging.info("     URL: %s", item.url)
                        logging.info("     Provider: %s", item.provider)
                        logging.info("     Published: %s", item.published_at)

            else:
                logging.error("✗ Failed to create subscription")

        except Exception:
            logging.exception("✗ Error:")


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
    ]

    http_client = AsyncHttpClient(contact_email="test@email.com")
    rss_client = RssFeedClient(http_client=http_client)

    await find_rss_feeds(rss_client, test_feeds)
    await find_rss_details(rss_client, test_feeds)

    logging.info("")
    logging.info("=" * 60)
    logging.info("All tests completed!")
    logging.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
