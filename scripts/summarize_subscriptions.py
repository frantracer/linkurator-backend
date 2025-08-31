import asyncio
import logging
from uuid import uuid4

from pydantic import AnyUrl

from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.infrastructure.ai_agents.subscription_summarizer import SubscriptionSummarizerService
from linkurator_core.infrastructure.config.settings import ApplicationSettings
from linkurator_core.infrastructure.logger import configure_logging


async def main() -> None:
    """Test the subscription summarizer agent with mock data."""
    settings = ApplicationSettings.from_file()

    configure_logging(settings.log)

    # Get API key from environment or use a placeholder
    api_key = settings.google_ai.api_key

    # Create test subscriptions
    test_subscriptions = [
        Subscription.new(
            uuid=uuid4(),
            name="TechCrunch",
            provider=SubscriptionProvider.YOUTUBE,
            url=AnyUrl("https://youtube.com/techcrunch"),
            thumbnail=AnyUrl("https://example.com/thumb.jpg"),
            description="""
TechCrunch is a leading technology media property, dedicated to obsessively profiling startups,
reviewing new Internet products, and breaking tech news. We cover the technology industry including
startups, venture capital, gadgets, apps, social media, and mobile.
            """,
        ),
        Subscription.new(
            uuid=uuid4(),
            name="The Joe Rogan Experience",
            provider=SubscriptionProvider.SPOTIFY,
            url=AnyUrl("https://spotify.com/jre"),
            thumbnail=AnyUrl("https://example.com/thumb2.jpg"),
            description="""
The Joe Rogan Experience podcast features long-form conversations with guests from various
fields including comedians, actors, musicians, MMA fighters, scientists, and political figures"
            """,
        ),
        Subscription.new(
            uuid=uuid4(),
            name="Empty Description Channel",
            provider=SubscriptionProvider.YOUTUBE,
            url=AnyUrl("https://youtube.com/empty"),
            thumbnail=AnyUrl("https://example.com/thumb3.jpg"),
            description="""
            """,
        ),
    ]

    # Initialize summarizer service
    summarizer_service = SubscriptionSummarizerService(google_api_key=api_key)

    logging.info("Testing subscription summarizer with mock data...\n")

    for i, subscription in enumerate(test_subscriptions, 1):
        logging.info(f"--- Test Subscription {i} ---")
        logging.info(f"Description: {subscription.description or 'Empty'}")

        try:
            result = await summarizer_service.summarize(subscription)
            logging.info(f"✅ Generated Summary: {result.summary}")

        except Exception as e:
            logging.info(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
