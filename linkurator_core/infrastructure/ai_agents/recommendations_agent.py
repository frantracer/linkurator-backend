import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Union
from uuid import UUID

import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.tools import ToolDefinition

from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.domain.chats.chat import Chat, ChatRole
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import (
    AnyItemInteraction,
    ItemFilterCriteria,
    ItemRepository,
)
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository

ITEMS_PER_PAGE = 20


@dataclass
class RecommendationsDependencies:
    user_uuid: UUID
    user_repository: UserRepository
    subscription_repository: SubscriptionRepository
    item_repository: ItemRepository
    topic_repository: TopicRepository
    previous_chat: Chat | None
    find_items_by_keywords_calls: int = 0
    find_subscriptions_items_calls: int = 0


class TopicForAI(BaseModel):
    uuid: UUID = Field(
        description="Unique identifier for the topic",
    )
    name: str = Field(
        description="Name of the topic",
    )
    subscription_ids: list[UUID] = Field(
        description="List of subscription UUIDs associated with this topic",
    )

    @classmethod
    def from_topic(cls, topic: Topic) -> "TopicForAI":
        return cls(
            uuid=topic.uuid,
            name=topic.name,
            subscription_ids=topic.subscriptions_ids,
        )

    def as_context(self) -> str:
        return f"Name: {self.name} | UUID: {self.uuid}"


class SubscriptionForAI(BaseModel):
    uuid: UUID = Field(
        description="Unique identifier for the subscription",
    )
    name: str = Field(
        description="Name of the subscription",
    )
    description: str | None = Field(
        default=None,
        description="Description of the subscription, if available",
    )
    provider: SubscriptionProvider = Field(
        description="Provider of the subscription (e.g., 'youtube', 'spotify')",
    )

    @classmethod
    def from_subscription(cls, subscription: Subscription) -> "SubscriptionForAI":
        return cls(
            uuid=subscription.uuid,
            name=subscription.name,
            description=subscription.summary,
            provider=subscription.provider,
        )

    def as_context(self) -> str:
        return (f"Name: {self.name} | UUID: {self.uuid} | Provider: {self.provider.value} | "
                f"Description: {self.description or 'No description'}")


class ItemForAI(BaseModel):
    uuid: UUID = Field(
        description="Unique identifier for the item",
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
            uuid=item.uuid,
            name=item.name,
            subscription_name=sub_name,
            description=item.description,
            provider=item.provider,
            published_at=item.published_at,
        )

    def as_context(self) -> str:
        published_str = self.published_at.strftime("%Y-%m-%d")
        return (f"Title: {self.name}\nUUID: {self.uuid}\nSubscription: {self.subscription_name}\n"
                f"Provider: {self.provider.value}\nPublished at: {published_str}\nDescription: {self.description}")


class RecommendationsOutput(BaseModel):
    response: str = Field(
        default="",
        description="Response for the user based on their query",
    )
    items_uuids: list[str] = Field(
        default_factory=list,
        description="List of content items UUIDs (32 hex) related to the user's query. "
                    "Can be empty if no items match.",
    )


class RecommendationsAgent:
    def __init__(self, google_api_key: str) -> None:
        self.agent = self._create_agent(google_api_key)

    def _create_agent(self, api_key: str) -> Agent[RecommendationsDependencies, RecommendationsOutput]:
        provider = GoogleProvider(api_key=api_key)

        gemini_flash_model = GoogleModel(
            provider=provider,
            model_name="gemini-2.5-flash",
            settings=GoogleModelSettings(
                temperature=0.2,
                google_thinking_config={"thinking_budget": 0},
            ),
        )

        ai_agent = Agent[RecommendationsDependencies, RecommendationsOutput](
            gemini_flash_model,
            deps_type=RecommendationsDependencies,
            output_type=RecommendationsOutput,
            system_prompt=(
                "You are a content recommendation system that helps users find videos, podcasts or articles based on their query. "
                "Answer in the same language the user is using. "
                "Always use the customer's name in your responses. "
                "If the user has no subscriptions, inform them that you cannot recommend content without subscriptions. "
                "Items that belongs to a subscription included in any of the user topics are considered more relevant. "
                "Try first to find items from subscriptions before using keyword search. "
                "When finding items, try to find by a single keyword. "
                "It is ok to return empty lists of items ids if there are no matching items to the query. "
                "When the user asks for specific dates, ensure you do not return any items that were published before the date. "
                "Use markdown formatting, make titles bold and bullet points for lists. "
                "Summarize the titles if they are similar and provide the subscription names as links to the item. "
                "If the same title from different providers is found, summarize them in a single item with links. "
                "Add the provider name (YouTube or Spotify) to the links if it is required to distinguish between items. "
                "You do not have access to the content, only to a brief description and the title. "
                "Answer the user's query using items, subscriptions and topics that are relevant to the query. "
                "Do not ask the user to provide more information, use the information you have. "
                "If an item is referenced in the response, use a markdown link to the url https://linkurator.com/items/{item.uuid} "
                "If a subscription is referenced in the response, use a markdown link to the url https://linkurator.com/subscriptions/{subscription.uuid} "
                "Link titles cannot be multiline in markdown. "
                "The response must contains a list with the items you are recommending. "
                "The response must have 1000 words maximum. "
            ),
            prepare_tools=filter_tools,
        )

        @ai_agent.system_prompt
        async def add_user_name(ctx: RunContext[RecommendationsDependencies]) -> str:
            user = await ctx.deps.user_repository.get(ctx.deps.user_uuid)
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
            subs = await handler.handle(user_id=ctx.deps.user_uuid)
            subs_for_ai = [SubscriptionForAI.from_subscription(sub) for sub in subs]

            topics = await ctx.deps.topic_repository.get_by_user_id(ctx.deps.user_uuid)
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

            ai_items = [ItemForAI.from_item(item, indexed_subs_names[item.subscription_uuid]) for item in items]

            context = "Items recommended to the user in previous chats:\n"
            context += "\n---\n".join(ai_item.as_context() for ai_item in ai_items) + "\n"
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
                topic_ids: List of topic UUIDs (32 hex) to filter items by
                subscription_ids: List of subscription UUIDs (32 hex) to filter items by

            """
            ctx.deps.find_subscriptions_items_calls += 1

            topic_uuids: list[UUID] = parse_ids_to_uuids(topic_ids)
            subscription_uuids: list[UUID] = parse_ids_to_uuids(subscription_ids)

            topics = await ctx.deps.topic_repository.find_topics(topic_uuids)

            all_subs_ids = set()

            if subscription_uuids is not None:
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

            return [ItemForAI.from_item(item, indexed_subs_names[item.subscription_uuid]) for item in items]

        @ai_agent.tool()
        async def find_items_by_keywords(
            ctx: RunContext[RecommendationsDependencies],
            keywords: list[str],
        ) -> list[ItemForAI]:
            """
            Finds items based on a single keyword search.

            Maximum one call per query with up to ten keywords.
            Maximum two words per keyword.
            Maximum 100 items returned.

            Args:
            ----
                ctx: RunContext with dependencies
                keywords: Keywords to search for in item titles. Maximum of ten keywords.

            """
            ctx.deps.find_items_by_keywords_calls += 1

            keywords = keywords.copy()[:10]

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

            return [ItemForAI.from_item(item, indexed_subs_names[item.subscription_uuid]) for item in items]

        return ai_agent

    async def handle_query(self, deps: RecommendationsDependencies, query: str) -> RecommendationsOutput:
        result = await self.agent.run(user_prompt=query, deps=deps)

        final_message = re.sub(
            r"https://linkurator\.com/(items|subscriptions)/([0-9a-fA-F-]{36})",
            lambda match: f"{self.base_url}/{match.group(1)}/{match.group(2)}/url",
            result.output,
        )

        return RecommendationsOutput(
            response=final_message,
            items_uuids=result.output.items_uuids,
        )


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
