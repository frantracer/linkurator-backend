import logging

from linkurator_core.domain.common.event import SubscriptionNeedsSummarizationEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.subscriptions.subscription_repository import (
    SubscriptionFilterCriteria,
    SubscriptionRepository,
)


class FindSubscriptionsForSummarizationHandler:
    """Handler that finds subscriptions needing summarization and publishes events for them."""

    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        event_bus: EventBusService,
    ) -> None:
        self.subscription_repository = subscription_repository
        self.event_bus = event_bus

    async def handle(self) -> None:
        """Find subscriptions that need summarization and publish events for them."""
        logging.info("Starting search for subscriptions needing summarization")

        # Get subscriptions that don't have summaries yet
        filter_criteria = SubscriptionFilterCriteria(has_summary=False)
        subscriptions_to_summarize = await self.subscription_repository.find(filter_criteria)

        if len(subscriptions_to_summarize) == 0:
            logging.info("No subscriptions need summarization")
            return

        logging.info(f"Found {len(subscriptions_to_summarize)} subscriptions needing summarization")

        events_published = 0
        for subscription in subscriptions_to_summarize:
            try:
                logging.debug(f"Publishing summarization event for subscription: {subscription.name} ({subscription.uuid})")

                event = SubscriptionNeedsSummarizationEvent.new(subscription.uuid)
                await self.event_bus.publish(event)
                events_published += 1

            except Exception as e:
                logging.exception(f"Error publishing event for subscription {subscription.name} ({subscription.uuid}): {e}")

        logging.info(f"Published {events_published} summarization events")
