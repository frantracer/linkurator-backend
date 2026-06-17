
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from linkurator_core.domain.agents.summarize_agent_service import SummarizeAgentResult, SummarizeAgentService
from linkurator_core.domain.subscriptions.subscription import Subscription


class SummaryOutput(BaseModel):
    summary: str = Field(
        description="A concise 2-3 sentence summary of the subscription's content and focus",
    )


class SubscriptionSummarizerService(SummarizeAgentService):
    """Service for generating AI summaries of subscription descriptions."""

    def __init__(self, model: Model) -> None:
        """Initialize the summarizer with the agent model."""
        self.agent = create_summarize_subscriptions_agent(model)

    async def summarize(self, subscription: Subscription) -> SummarizeAgentResult:
        """
        Generate a summary for a subscription based on its description.

        Args:
        ----
            subscription: The subscription to summarize

        Returns:
        -------
            A summary string, or None if summarization fails

        """
        if not subscription.description or subscription.description.strip() == "":
            return SummarizeAgentResult(summary="No description.")

        prompt = (
            f"Subscription Name: {subscription.name}\n"
            f"Provider: {subscription.provider}\n"
            f"Description: {subscription.description}\n\n"
            f"Create a concise summary of this {subscription.provider} "
            f"subscription's content and focus."
        )

        retries = 3
        summary = ""
        while retries > 0:
            retries -= 1
            result = await self.agent.run(prompt)
            summary = result.output.summary.strip()
            if len(summary) > 0 and summary[-1] == ".":
                break

        return SummarizeAgentResult(summary=summary)


def create_summarize_subscriptions_agent(model: Model) -> Agent[None, SummaryOutput]:
    """Create the PydanticAI agent for summarization."""
    return Agent[None, SummaryOutput](
        model,
        name="SubscriptionSummarizerAgent",
        output_type=SummaryOutput,
        model_settings=ModelSettings(
            temperature=0.1,
        ),
        system_prompt=(
            "You are a content summarization expert. Your task is to create concise, "
            "informative summaries of subscription descriptions. "
            "Focus on the main topics, content style, and target audience. "
            "Do not include email addresses, URLs, or any promotional language. "
            "Keep summaries to 2-3 sentences maximum. "
            "Be factual and avoid subjective language. "
            "Start the summary with the name of the subscription. "
            "End the summary with a period. "
        ),
    )
