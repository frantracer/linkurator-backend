import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Union
from uuid import UUID

import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.tools import ToolDefinition

from linkurator_core.domain.agents.query_agent_service import AgentQueryResult, QueryAgentService
from linkurator_core.domain.chats.chat import Chat
from linkurator_core.domain.chats.chat_repository import ChatRepository
from linkurator_core.domain.common.exceptions import QueryAgentError
from linkurator_core.domain.items.item_repository import (
    ItemFilterCriteria,
    ItemRepository,
)
from linkurator_core.domain.subscriptions.subscription_repository import (
    SubscriptionRepository,
)
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.ai_agents.recommendations_agent import (
    RecommendationsAgent,
    RecommendationsDependencies,
)
from linkurator_core.infrastructure.ai_agents.topic_manager_agent import (
    TopicManagerAgent,
    TopicManagerDependencies,
)


@dataclass
class CoreAgentDependencies:
    user_uuid: UUID
    user_repository: UserRepository
    subscription_repository: SubscriptionRepository
    item_repository: ItemRepository
    topic_repository: TopicRepository
    chat_repository: ChatRepository

    recommendations_agent: RecommendationsAgent
    recommendations_agent_calls: int
    topic_manager_agent: TopicManagerAgent
    topic_manager_agent_calls: int

    previous_chat: Chat | None
    topics_were_created: bool
    related_items_uuids: list[str]


class CoreAgentOutput(BaseModel):
    response: str = Field(
        description="Response for the user based on their query",
    )
    items_uuids: list[str] = Field(
        default_factory=list,
        description="List of content items UUIDs related to the user's query",
    )
    topics_were_created: bool = Field(
        default=False,
        description="Indicates whether any topics were created during the query processing",
    )


class CoreRouterAgent(QueryAgentService):
    def __init__(
        self,
        user_repository: UserRepository,
        subscription_repository: SubscriptionRepository,
        item_repository: ItemRepository,
        topic_repository: TopicRepository,
        chat_repository: ChatRepository,
        base_url: str,
        google_api_key: str,
    ) -> None:
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository
        self.topic_repository = topic_repository
        self.chat_repository = chat_repository
        self.base_url = base_url

        self.agent = self._create_agent(google_api_key)
        self.recommendations_agent = RecommendationsAgent(google_api_key)
        self.topic_manager_agent = TopicManagerAgent(google_api_key)

    def _create_agent(self, api_key: str) -> Agent[CoreAgentDependencies, CoreAgentOutput]:
        provider = GoogleProvider(api_key=api_key)

        gemini_flash_model = GoogleModel(
            provider=provider,
            model_name="gemini-2.5-flash",
            settings=GoogleModelSettings(
                temperature=0.1,
                google_thinking_config={"thinking_budget": 0},
            ),
        )

        ai_agent = Agent[CoreAgentDependencies, CoreAgentOutput](
            gemini_flash_model,
            deps_type=CoreAgentDependencies,
            output_type=CoreAgentOutput,
            system_prompt=(
                "You are a unified AI agent that helps users find content and manage topics. "
                "Answer in the same language the user is using. "
                "Always use the customer's name in your responses. "
                "Use tools to handle different types of queries:\n\n"
                "For content recommendations, searching for videos/podcasts, or finding items: use recommendation tools.\n"
                "For creating, managing, or organizing topics: use topic management tools.\n\n"
                "Use markdown formatting, make titles bold and bullet points for lists. "
                "If an item is referenced in the response, use a markdown link to https://linkurator.com/items/{item.uuid} "
                "If a subscription is referenced in the response, use a markdown link to https://linkurator.com/subscriptions/{subscription.uuid} "
                "The response must have 1000 words maximum."
            ),
            prepare_tools=filter_tools,
        )

        @ai_agent.system_prompt
        async def add_user_name(ctx: RunContext[CoreAgentDependencies]) -> str:
            user = await ctx.deps.user_repository.get(ctx.deps.user_uuid)
            if user is None:
                logfire.warning(
                    "User not found for customer UUID",
                    customer_uuid=ctx.deps.user_uuid,
                )
                return "The customer's name is unknown"
            return f"The customer's name is {user.first_name!r}"

        @ai_agent.system_prompt
        async def add_today_date(_ctx: RunContext[CoreAgentDependencies]) -> str:
            now = datetime.now(tz=timezone.utc)
            return f"Today is {now.strftime('%A %Y-%m-%d')}"

        @ai_agent.tool()
        async def handle_recommendations_query(
            ctx: RunContext[CoreAgentDependencies],
            query: str,
        ) -> str:
            """
            Handle content recommendation queries, searching for videos/podcasts, or finding items by keywords.

            Args:
            ----
                ctx: RunContext with dependencies
                query: The user's query about content recommendations

            """
            agent_deps = RecommendationsDependencies(
                user_uuid=ctx.deps.user_uuid,
                user_repository=ctx.deps.user_repository,
                subscription_repository=ctx.deps.subscription_repository,
                item_repository=ctx.deps.item_repository,
                topic_repository=ctx.deps.topic_repository,
                previous_chat=ctx.deps.previous_chat,
            )

            context = build_chat_context(ctx.deps.previous_chat)
            result = await ctx.deps.recommendations_agent.handle_query(agent_deps, context + query)

            # Store results for later retrieval
            ctx.deps.recommendations_agent_calls += 1
            ctx.deps.related_items_uuids.extend(result.items_uuids)

            return result.response

        @ai_agent.tool()
        async def handle_topic_management_query(
            ctx: RunContext[CoreAgentDependencies],
            query: str,
        ) -> str:
            """
            Handle topic management queries, creating, managing, or organizing topics.

            Args:
            ----
                ctx: RunContext with dependencies
                query: The user's query about topic management

            """
            agent_deps = TopicManagerDependencies(
                user_uuid=ctx.deps.user_uuid,
                user_repository=ctx.deps.user_repository,
                subscription_repository=ctx.deps.subscription_repository,
                topic_repository=ctx.deps.topic_repository,
                previous_chat=ctx.deps.previous_chat,
            )

            context = build_chat_context(ctx.deps.previous_chat)
            result = await ctx.deps.topic_manager_agent.handle_query(agent_deps, context + query)

            # Store results for later retrieval
            ctx.deps.topic_manager_agent_calls += 1
            ctx.deps.topics_were_created = result.topics_were_created

            return result.response

        return ai_agent

    async def query(self, user_id: UUID, query: str, chat_id: UUID) -> AgentQueryResult:
        retry = 0
        max_retries = 3
        while retry < max_retries:
            try:
                return await self._perform_query(user_id, query, chat_id)
            except UnexpectedModelBehavior as e:
                logging.exception(f"Error during AI agent query, retry {retry + 1}/{max_retries}: {e}")
                retry += 1
        msg = "AI agent failed to process the query after multiple attempts"
        logging.error(msg)
        raise QueryAgentError(msg)

    async def _perform_query(self, user_id: UUID, query: str, chat_id: UUID) -> AgentQueryResult:
        previous_chat = await self.chat_repository.get(chat_id)

        deps = CoreAgentDependencies(
            user_uuid=user_id,
            user_repository=self.user_repository,
            subscription_repository=self.subscription_repository,
            item_repository=self.item_repository,
            topic_repository=self.topic_repository,
            chat_repository=self.chat_repository,
            recommendations_agent=self.recommendations_agent,
            recommendations_agent_calls=0,
            topic_manager_agent=self.topic_manager_agent,
            topic_manager_agent_calls=0,
            topics_were_created=False,
            related_items_uuids=[],
            previous_chat=previous_chat,
        )

        result = await self.agent.run(user_prompt=query, deps=deps)

        return await self._build_agent_result(
            response=result.output.response,
            item_uuids_str=deps.related_items_uuids,
            topics_were_created=deps.topics_were_created,
        )

    async def _build_agent_result(self, response: str, item_uuids_str: list[str], topics_were_created: bool) -> AgentQueryResult:
        items = []
        item_uuids = set(parse_ids_to_uuids(item_uuids_str))
        if len(item_uuids_str) > 0:
            items = await self.item_repository.find_items(
                criteria=ItemFilterCriteria(item_ids=item_uuids),
                page_number=0,
                limit=len(item_uuids_str),
            )

        subscriptions_uuids = list({item.subscription_uuid for item in items})
        subscriptions = []
        if len(subscriptions_uuids) > 0:
            subscriptions = await self.subscription_repository.get_list(subscriptions_uuids)

        final_message = re.sub(
            r"https://linkurator\.com/(items|subscriptions)/([0-9a-fA-F-]{36})",
            lambda match: f"{self.base_url}/{match.group(1)}/{match.group(2)}/url",
            response,
        )

        return AgentQueryResult(
            message=final_message,
            items=items,
            subscriptions=subscriptions,
            topics_were_created=topics_were_created,
        )


def build_chat_context(previous_chat: Chat | None) -> str:
    context = ""
    if previous_chat is not None and len(previous_chat.messages) > 0:
        context = "Previous chat messages:\n"
        for message in previous_chat.messages:
            if message.role == "user":
                context += f"User: {message.content}\n"
            elif message.role == "assistant":
                context += f"Assistant: {message.content}\n"
        context += "End of previous chat messages.\n"
    return context


def parse_ids_to_uuids(ids: list[str] | None) -> list[UUID]:
    if ids is None:
        return []

    valid_uuids: list[UUID] = []
    for id_str in ids:
        try:
            valid_uuids.append(UUID(id_str))
        except ValueError as e:
            logging.exception(f"Failed to parse UUID {id_str}: {e}")

    return valid_uuids


async def filter_tools(
        ctx: RunContext[CoreAgentDependencies], tool_defs: list[ToolDefinition],
) -> Union[list[ToolDefinition], None]:
    filtered_tools = []
    for tool_def in tool_defs:
        if tool_def.name == "handle_recommendations_query":
            if ctx.deps.recommendations_agent_calls < 1 and ctx.deps.topic_manager_agent_calls < 1:
                filtered_tools.append(tool_def)
        elif tool_def.name == "handle_topic_management_query":
            if ctx.deps.topic_manager_agent_calls < 1 and ctx.deps.recommendations_agent_calls < 1:
                filtered_tools.append(tool_def)
        else:
            filtered_tools.append(tool_def)
    return filtered_tools
