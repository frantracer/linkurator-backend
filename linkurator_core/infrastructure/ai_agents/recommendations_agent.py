import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Union
from uuid import UUID

import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.usage import RunUsage

from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.domain.chats.chat import Chat, ChatRole
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import (
    AnyItemInteraction,
    ItemFilterCriteria,
    ItemRepository,
)
from linkurator_core.domain.subscriptions.subscription import Subscription
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository
from linkurator_core.infrastructure.ai_agents.keyword_generator_agent import KeywordGeneratorAgent

ITEMS_PER_PAGE = 20
SHORT_ID_LENGTH = 8


def short_id(uuid: UUID) -> str:
    return str(uuid)[:SHORT_ID_LENGTH]


def resolve_short_ids(ids: list[str] | None, mapping: dict[str, UUID]) -> list[UUID]:
    if not ids:
        return []
    resolved: list[UUID] = []
    for raw in ids:
        sid = raw.lower()
        full = mapping.get(sid)
        if full is not None:
            resolved.append(full)
            continue
        try:
            resolved.append(UUID(raw))
        except ValueError:
            logging.warning("Could not resolve short id %r", raw)
    return resolved


@dataclass
class RecommendationsDependencies:
    user_uuid: UUID | None
    user_repository: UserRepository
    subscription_repository: SubscriptionRepository
    item_repository: ItemRepository
    topic_repository: TopicRepository
    keyword_generator_agent: KeywordGeneratorAgent
    previous_chat: Chat | None
    item_id_map: dict[str, UUID] = field(default_factory=dict)
    subscription_id_map: dict[str, UUID] = field(default_factory=dict)
    topic_id_map: dict[str, UUID] = field(default_factory=dict)
    find_items_by_keywords_calls: int = 0
    find_subscriptions_items_calls: int = 0

    def register_item_id(self, item_uuid: UUID) -> None:
        self.item_id_map[short_id(item_uuid)] = item_uuid

    def register_subscription_id(self, sub_uuid: UUID) -> None:
        self.subscription_id_map[short_id(sub_uuid)] = sub_uuid

    def register_topic(self, topic: Topic) -> None:
        self.topic_id_map[short_id(topic.uuid)] = topic.uuid
        for sub_uuid in topic.subscriptions_ids:
            self.register_subscription_id(sub_uuid)


class TopicForAI(BaseModel):
    id: str = Field(
        description="Short identifier for the topic (8 hex chars)",
    )
    name: str = Field(
        description="Name of the topic",
    )
    subscription_ids: list[str] = Field(
        description="List of subscription short IDs (8 hex chars) associated with this topic",
    )

    @classmethod
    def from_topic(cls, topic: Topic) -> "TopicForAI":
        return cls(
            id=short_id(topic.uuid),
            name=topic.name,
            subscription_ids=[short_id(sub_uuid) for sub_uuid in topic.subscriptions_ids],
        )

    def as_context(self) -> str:
        subs = ", ".join(self.subscription_ids) if self.subscription_ids else "none"
        return f"Name: {self.name} | ID: {self.id} | Subscriptions: {subs}"


class SubscriptionForAI(BaseModel):
    id: str = Field(
        description="Short identifier for the subscription (8 hex chars)",
    )
    name: str = Field(
        description="Name of the subscription",
    )
    description: str | None = Field(
        default=None,
        description="Description of the subscription, if available",
    )
    provider: ItemProvider = Field(
        description="Provider of the subscription (e.g., 'youtube', 'spotify')",
    )

    @classmethod
    def from_subscription(cls, subscription: Subscription) -> "SubscriptionForAI":
        return cls(
            id=short_id(subscription.uuid),
            name=subscription.name,
            description=subscription.summary,
            provider=subscription.provider,
        )

    def as_context(self) -> str:
        return (f"Name: {self.name} | ID: {self.id} | Provider: {self.provider} | "
                f"Description: {self.description or 'No description'}")


class ItemForAI(BaseModel):
    id: str = Field(
        description="Short identifier for the item (8 hex chars)",
    )
    name: str = Field(
        description="Name of the item",
    )
    subscription_name: str = Field(
        description="Name of the subscription this item belongs to",
    )
    description: str = Field(
        description="Description of the item",
    )
    provider: ItemProvider = Field(
        description="Provider of the item (e.g., 'youtube', 'spotify')",
    )
    published_at: datetime = Field(
        description="Publication date of the item, if available",
    )

    @classmethod
    def from_item(cls, item: Item, sub_name: str) -> "ItemForAI":
        return cls(
            id=short_id(item.uuid),
            name=item.name,
            subscription_name=sub_name,
            description=item.description,
            provider=item.provider,
            published_at=item.published_at,
        )


class AgentOutput(BaseModel):
    response: str = Field(
        description="Human-readable response for the user based on their query, written in the user's language. "
                    "This field is mandatory and must never be empty: it has to contain the summary and the "
                    "markdown list of the recommended items.",
    )
    items_ids: list[str] = Field(
        default_factory=list,
        description="List of content item short IDs (8 hex chars) related to the user's query. "
                    "Can be empty if no items match.",
    )


class RecommendationsOutput(BaseModel):
    response: str = Field(
        default="",
        description="Response for the user based on their query",
    )
    items_uuids: list[str] = Field(
        default_factory=list,
        description="List of content items UUIDs related to the user's query.",
    )


class RecommendationsAgent:
    def __init__(
            self,
            model: Model,
            base_url: str,
            user_repository: UserRepository,
            subscription_repository: SubscriptionRepository,
            item_repository: ItemRepository,
            topic_repository: TopicRepository,
    ) -> None:
        self.recommendations_agent = create_recommendations_agent(model)
        self.base_url = base_url
        self.user_repository = user_repository
        self.subscription_repository = subscription_repository
        self.item_repository = item_repository
        self.topic_repository = topic_repository
        self.keyword_generator_agent = KeywordGeneratorAgent(model=model)

    async def query(
            self,
            query: str,
            user_id: UUID | None,
            previous_chat: Chat | None,
            usage: RunUsage,
    ) -> RecommendationsOutput:
        deps = RecommendationsDependencies(
            user_uuid=user_id,
            user_repository=self.user_repository,
            subscription_repository=self.subscription_repository,
            item_repository=self.item_repository,
            topic_repository=self.topic_repository,
            keyword_generator_agent=self.keyword_generator_agent,
            previous_chat=previous_chat,
        )
        result = await self.recommendations_agent.run(query, deps=deps, usage=usage)

        final_message = _expand_short_id_links(result.output.response, deps, self.base_url)

        items_uuids: list[str] = []
        for sid in result.output.items_ids:
            full = deps.item_id_map.get(sid.lower())
            if full is not None:
                items_uuids.append(str(full))

        return RecommendationsOutput(
            response=final_message,
            items_uuids=items_uuids,
        )


def _expand_short_id_links(response: str, deps: RecommendationsDependencies, base_url: str) -> str:
    short_id_re = re.compile(rf"\]\(([0-9a-fA-F]{{{SHORT_ID_LENGTH}}})\)")
    full_url_re = re.compile(
        rf"https://linkurator\.com/(items|subscriptions)/([0-9a-fA-F]{{{SHORT_ID_LENGTH}}})",
    )

    def replace_markdown(match: re.Match[str]) -> str:
        sid = match.group(1).lower()
        if sid in deps.item_id_map:
            return f"]({base_url}/items/{deps.item_id_map[sid]}/url)"
        if sid in deps.subscription_id_map:
            return f"]({base_url}/subscriptions/{deps.subscription_id_map[sid]}/url)"
        return match.group(0)

    def replace_full_url(match: re.Match[str]) -> str:
        kind = match.group(1)
        sid = match.group(2).lower()
        mapping = deps.item_id_map if kind == "items" else deps.subscription_id_map
        full = mapping.get(sid)
        if full is None:
            return match.group(0)
        return f"{base_url}/{kind}/{full}/url"

    response = short_id_re.sub(replace_markdown, response)
    return full_url_re.sub(replace_full_url, response)


def create_recommendations_agent(model: Model) -> Agent[RecommendationsDependencies, AgentOutput]:
    ai_agent = Agent[RecommendationsDependencies, AgentOutput](
        model,
        name="RecommendationsAgent",
        deps_type=RecommendationsDependencies,
        output_type=AgentOutput,
        model_settings=ModelSettings(
            temperature=0.2,
        ),
        system_prompt=(
            "You are a content recommendation system that helps users find videos, podcasts or articles based on their query. "
            "Answer in the same language the user is using. "
            "Always use the customer's name in your responses. "
            "Items that belongs to a subscription included in any of the user topics are considered more relevant. "
            "It is ok to return empty lists of items ids if there are no matching items to the query. "
            "When the user asks for specific dates, ensure you do not return any items that were published before the date. "
            "Use markdown formatting, make titles bold and bullet points for lists. "
            "Summarize the titles if they are similar and provide the subscription names as links to the item. "
            "If the same title from different providers is found, summarize them in a single item with links. "
            "Add the provider name (YouTube or Spotify) to the links if it is required to distinguish between items. "
            "You do not have access to the content, only to a brief description and the title. "
            "Answer the user's query using items, subscriptions and topics that are relevant to the query. "
            "Avoid asking the user to provide more information, use the information you have. "
            "Items, subscriptions and topics are identified by short IDs of 8 hex characters in the context. "
            "When you reference an item or subscription in the response, use a markdown link with the short ID as the URL: [Title](id). "
            "Do not invent IDs and do not write full URLs; only use IDs that appear in the context provided to you. "
            "The items_ids field in your output must contain the same 8-hex-char short IDs (never full UUIDs). "
            "Link titles cannot be multiline in markdown. "
            "The response must contains a list with the items you are recommending. "
            "The response must have 1000 words maximum. "
            "The response must contains a summary of the recommendations. "
        ),
        prepare_tools=filter_tools,
    )

    @ai_agent.system_prompt
    async def add_user_name(ctx: RunContext[RecommendationsDependencies]) -> str:
        user_uuid = ctx.deps.user_uuid
        if user_uuid is None:
            return "The customer's name is unknown"

        user = await ctx.deps.user_repository.get(user_uuid)
        if user is None:
            logfire.warning(
                "User not found for customer UUID",
                customer_uuid=ctx.deps.user_uuid,
            )
            return "The customer's name is unknown"
        return f"The customer's name is {user.first_name!r}"

    @ai_agent.system_prompt
    async def add_today_date(_ctx: RunContext[RecommendationsDependencies]) -> str:
        now = datetime.now(tz=timezone.utc)
        return f"Today is {now.strftime('%A %Y-%m-%d')}"

    @ai_agent.system_prompt
    async def user_subscriptions_and_topics(
        ctx: RunContext[RecommendationsDependencies],
    ) -> str:
        handler = GetUserSubscriptionsHandler(
            user_repository=ctx.deps.user_repository,
            subscription_repository=ctx.deps.subscription_repository,
        )
        user_uuid = ctx.deps.user_uuid

        subs_for_ai: list[SubscriptionForAI] = []
        if user_uuid is not None:
            subs = await handler.handle(user_id=user_uuid)
            for sub in subs:
                ctx.deps.register_subscription_id(sub.uuid)
            subs_for_ai = [SubscriptionForAI.from_subscription(sub) for sub in subs]

        topics_for_ai: list[TopicForAI] = []
        if user_uuid is not None:
            topics = await ctx.deps.topic_repository.get_by_user_id(user_uuid)
            for topic in topics:
                ctx.deps.register_topic(topic)
            topics_for_ai = [TopicForAI.from_topic(topic) for topic in topics]

        context = "User's subscriptions:\n"
        if len(subs_for_ai) == 0:
            context += "The user has no subscriptions.\n"
        else:
            context += "\n\n".join([sub_ai.as_context() for sub_ai in subs_for_ai]) + "\n"

        context += "\nUser's topics:\n"
        if len(topics_for_ai) == 0:
            context += "The user has no topics.\n"
        else:
            context += "\n\n".join([topic_ai.as_context() for topic_ai in topics_for_ai]) + "\n"

        context += "End of user's subscriptions and topics.\n"

        return context

    @ai_agent.system_prompt
    async def previous_items_information(
        ctx: RunContext[RecommendationsDependencies],
    ) -> str:
        chat = ctx.deps.previous_chat
        if chat is None:
            return ""

        items_uuids: set[UUID] = set()
        for message in chat.messages:
            if message.role == ChatRole.ASSISTANT:
                items_uuids = items_uuids.union(set(message.item_uuids))

        if len(items_uuids) == 0:
            return ""

        items = await ctx.deps.item_repository.find_items(
            criteria=ItemFilterCriteria(
                item_ids=items_uuids,
            ),
            page_number=0,
            limit=100,
        )

        subscriptions = await ctx.deps.subscription_repository.get_list(
            [item.subscription_uuid for item in items],
        )
        indexed_subs_names = {sub.uuid: sub.name for sub in subscriptions}

        for item in items:
            ctx.deps.register_item_id(item.uuid)

        context = "Items recommended to the user in the chat:\n"
        context += "\n".join([
            ItemForAI.from_item(item, indexed_subs_names[item.subscription_uuid]).model_dump_json()
            for item in items
        ]) + "\n"
        context += "End of previously recommended items.\n"

        return context

    @ai_agent.tool()
    async def find_subscriptions_items(
        ctx: RunContext[RecommendationsDependencies],
        topic_ids: list[str] | None = None,
        subscription_ids: list[str] | None = None,
    ) -> list[ItemForAI]:
        """
        Get items from subscriptions and topics.

        Maximum one call per query. Maximum 100 items returned.

        Args:
        ----
            ctx: RunContext with dependencies
            topic_ids: List of topic short IDs (8 hex chars) from the context to filter items by
            subscription_ids: List of subscription short IDs (8 hex chars) from the context to filter items by

        """
        ctx.deps.find_subscriptions_items_calls += 1

        topic_uuids: list[UUID] = resolve_short_ids(topic_ids, ctx.deps.topic_id_map)
        subscription_uuids: list[UUID] = resolve_short_ids(
            subscription_ids, ctx.deps.subscription_id_map,
        )

        topics = await ctx.deps.topic_repository.find_topics(topic_uuids)

        all_subs_ids: set[UUID] = set()

        all_subs_ids.update(subscription_uuids)

        for topic in topics:
            all_subs_ids.update(topic.subscriptions_ids)

        criteria = ItemFilterCriteria(
            subscription_ids=None if len(all_subs_ids) == 0 else list(all_subs_ids),
            interactions_from_user=ctx.deps.user_uuid,
            interactions=AnyItemInteraction(without_interactions=True),
        )

        items = await ctx.deps.item_repository.find_items(
            criteria=criteria,
            page_number=0,
            limit=ITEMS_PER_PAGE,
        )

        subscriptions = await ctx.deps.subscription_repository.get_list(
            [item.subscription_uuid for item in items],
        )
        indexed_subs_names = {sub.uuid: sub.name for sub in subscriptions}

        items = sorted(items, key=lambda item: item.created_at, reverse=True)
        items = items[:100]

        for item in items:
            ctx.deps.register_item_id(item.uuid)

        return [
            ItemForAI.from_item(item, indexed_subs_names[item.subscription_uuid])
            for item in items
        ]

    @ai_agent.tool()
    async def find_items_by_keywords(
        ctx: RunContext[RecommendationsDependencies],
        user_query: str,
    ) -> list[ItemForAI]:
        """
        Finds items based on keyword search generated from user query.

        Maximum one call per query.
        Maximum 100 items returned.

        Args:
        ----
            ctx: RunContext with dependencies
            user_query: User query to generate keywords from and search for relevant items.

        """
        ctx.deps.find_items_by_keywords_calls += 1

        # Generate keywords from user query using the keyword generator agent
        usage = RunUsage()
        keywords = await ctx.deps.keyword_generator_agent.generate_keywords(user_query, usage)

        # Limit to 10 keywords for performance
        keywords = keywords[:10]

        tasks = []
        for keyword in keywords:
            criteria = ItemFilterCriteria(
                text=keyword,
            )

            task = ctx.deps.item_repository.find_items(
                criteria=criteria,
                page_number=0,
                limit=ITEMS_PER_PAGE,
            )

            tasks.append(task)

        results = await asyncio.gather(*tasks)
        items = [item for sublist in results for item in sublist]

        subscriptions = await ctx.deps.subscription_repository.get_list(
            [item.subscription_uuid for item in items],
        )
        indexed_subs_names = {sub.uuid: sub.name for sub in subscriptions}

        items = sorted(items, key=lambda item: item.created_at, reverse=True)
        unique_items = {}
        for item in items:
            if item.uuid not in unique_items:
                unique_items[item.uuid] = item
        items = list(unique_items.values())[:100]

        for item in items:
            ctx.deps.register_item_id(item.uuid)

        return [
            ItemForAI.from_item(item, indexed_subs_names[item.subscription_uuid])
            for item in items
        ]

    return ai_agent


async def filter_tools(
    ctx: RunContext[RecommendationsDependencies], tool_defs: list[ToolDefinition],
) -> Union[list[ToolDefinition], None]:
    filtered_tools = []
    for tool_def in tool_defs:
        if tool_def.name == "find_subscriptions_items":
            if ctx.deps.find_subscriptions_items_calls < 1:
                filtered_tools.append(tool_def)
        elif tool_def.name == "find_items_by_keywords":
            if ctx.deps.find_items_by_keywords_calls < 1:
                filtered_tools.append(tool_def)
        else:
            filtered_tools.append(tool_def)
    return filtered_tools
