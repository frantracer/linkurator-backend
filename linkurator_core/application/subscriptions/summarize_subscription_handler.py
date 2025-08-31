import logging
from uuid import UUID

from linkurator_core.domain.agents.summarize_agent_service import SummarizeAgentService
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository


class SummarizeSubscriptionHandler:
    """Handler for summarizing a single subscription description using AI."""

    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        summarizer_service: SummarizeAgentService,
    ) -> None:
        self.subscription_repository = subscription_repository
        self.summarizer_service = summarizer_service

    async def handle(self, subscription_id: UUID) -> None:
        """Summarize a subscription by its UUID."""
        logging.info(f"Handling subscription summarization for subscription ID: {subscription_id}")

        try:
            subscription = await self.subscription_repository.get(subscription_id)
            if subscription is None:
                logging.warning(f"Subscription not found: {subscription_id}")
                return

            logging.debug(f"Summarizing subscription: {subscription.name} ({subscription.uuid})")

            result = await self.summarizer_service.summarize(subscription)

            # Update the subscription with the new summary
            subscription.update_summary(result.summary)
            await self.subscription_repository.update(subscription)
            logging.info(f"Successfully summarized subscription: {subscription.name}")

        except Exception as e:
            logging.exception(f"Error summarizing subscription {subscription_id}: {e}")
