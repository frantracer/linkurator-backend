from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Union
from uuid import UUID

import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.tools import ToolDefinition

from linkurator_core.domain.chats.chat import Chat
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class RouterDependencies:
    user_uuid: UUID
    user_repository: UserRepository
    subscription_repository: SubscriptionRepository
    topic_repository: TopicRepository
    previous_chat: Chat | None


class RouterOutput(BaseModel):
    agent_type: Literal["recommendations", "topic_manager"] = Field(
        description="The type of agent that should handle this query",
    )
    reasoning: str = Field(
        description="Explanation of why this agent type was chosen",
    )


class CoreRouterAgent:
    def __init__(self, google_api_key: str) -> None:
        self.agent = self._create_agent(google_api_key)

    def _create_agent(self, api_key: str) -> Agent[RouterDependencies, RouterOutput]:
        provider = GoogleProvider(api_key=api_key)

        gemini_flash_model = GoogleModel(
            provider=provider,
            model_name="gemini-2.5-flash",
            settings=GoogleModelSettings(
                temperature=0.1,
                google_thinking_config={"thinking_budget": 0},
            ),
        )

        ai_agent = Agent[RouterDependencies, RouterOutput](
            gemini_flash_model,
            deps_type=RouterDependencies,
            output_type=RouterOutput,
            system_prompt=(
                "You are a router agent that determines which specialized agent should handle a user query. "
                "Your job is to analyze the query and route it to the appropriate agent:\n\n"
                "- 'recommendations': For queries asking for content recommendations, searching for specific videos/podcasts, "
                "finding items by keywords, or general content discovery requests.\n"
                "- 'topic_manager': For queries about creating, managing, organizing topics, or managing subscriptions within topics.\n\n"
                "Always choose 'recommendations' as the default unless the query explicitly mentions topics management."
            ),
        )

        @ai_agent.system_prompt
        async def add_user_name(ctx: RunContext[RouterDependencies]) -> str:
            user = await ctx.deps.user_repository.get(ctx.deps.user_uuid)
            if user is None:
                logfire.warning(
                    "User not found for customer UUID",
                    customer_uuid=ctx.deps.user_uuid,
                )
                return "The customer's name is unknown"
            return f"The customer's name is {user.first_name!r}"

        @ai_agent.system_prompt
        async def add_today_date(_ctx: RunContext[RouterDependencies]) -> str:
            now = datetime.now(tz=timezone.utc)
            return f"Today is {now.strftime('%A %Y-%m-%d')}"

        return ai_agent

    async def route_query(self, deps: RouterDependencies, query: str) -> RouterOutput:
        result = await self.agent.run(user_prompt=query, deps=deps)
        return result.output


async def filter_tools(
    ctx: RunContext[RouterDependencies], tool_defs: list[ToolDefinition],
) -> Union[list[ToolDefinition], None]:
    return []
