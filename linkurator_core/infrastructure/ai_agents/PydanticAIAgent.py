from dataclasses import dataclass
from uuid import UUID

import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class SupportDependencies:
    user_uuid: UUID
    user_repository: UserRepository
    subscription_repository: SubscriptionRepository


class SupportOutput(BaseModel):
    recommendation: str = Field(description='Content recommendation for the customer based on their query')
    content_items_uuids: bool = Field(description="List of content item UUIDs related to the customer's query")


def create_agent(api_key: str) -> Agent[SupportDependencies, SupportOutput]:
    """
    Creates a support agent that can be used to handle customer queries.
    The agent will provide advice based on the customer's query and
    judge the risk level of the query.
    """
    logfire.instrument_pydantic_ai()

    provider = OpenAIProvider(
        api_key=api_key,
    )
    llm_model = OpenAIModel(
        provider=provider,
        model_name='gpt-4.1',
    )
    support_agent = Agent[SupportDependencies, SupportOutput](
        llm_model,
        deps_type=SupportDependencies,
        output_type=SupportOutput,
        system_prompt=(
            'You are a system to recommend videos, podcasts or articles to the user based on their query. '
            'Always use the customer\'s name in your responses. '
        ),
    )

    @support_agent.system_prompt
    async def add_user_name(ctx: RunContext[SupportDependencies]) -> str:
        user = await ctx.deps.user_repository.get(
            ctx.deps.user_uuid
        )
        if user is None:
            logfire.warning(
                'User not found for customer UUID',
                customer_uuid=ctx.deps.user_uuid
            )
            return "The customer's name is unknown"
        return f"The customer's name is {user.first_name!r}"

    @support_agent.tool
    async def user_subscriptions(
            ctx: RunContext[SupportDependencies]
    ) -> list[Subscription]:
        """Returns the user's subscriptions."""
        handler = GetUserSubscriptionsHandler(
            user_repository=ctx.deps.user_repository,
            subscription_repository=ctx.deps.subscription_repository
        )
        return await handler.handle(
            user_id=ctx.deps.user_uuid
        )

    return support_agent
