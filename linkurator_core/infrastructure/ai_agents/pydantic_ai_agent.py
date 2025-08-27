import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.usage import RunUsage

from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.domain.agents.query_agent_service import AgentQueryResult, QueryAgentService
from linkurator_core.domain.chats.chat import Chat, ChatRole
from linkurator_core.domain.chats.chat_repository import ChatRepository
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import (
    AnyItemInteraction,
    ItemFilterCriteria,
    ItemRepository,
)
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import (
    SubscriptionRepository,
)
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository

ITEMS_PER_PAGE = 20


@dataclass
class AgentDependencies:
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
        """
        Converts a Topic domain object to a TopicForAI model.

        Args:
        ----
            topic: The Topic domain object to convert.

        Returns:
        -------
            A TopicForAI instance with the same data as the provided topic.

        """
        return cls(
            uuid=topic.uuid,
            name=topic.name,
            subscription_ids=topic.subscriptions_ids,
        )

    def __str__(self) -> str:
        return f"{self.name} - {self.uuid}"


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
        """
        Converts a Subscription domain object to a SubscriptionForAI model.

        Args:
        ----
            subscription: The Subscription domain object to convert.

        Returns:
        -------
            A SubscriptionForAI instance with the same data as the provided subscription.

        """
        return cls(
            uuid=subscription.uuid,
            name=subscription.name,
            description=subscription.description,
            provider=subscription.provider,
        )

    def __str__(self) -> str:
        return f"- {self.name} ({self.provider}) - {self.uuid} - {self.description or 'No description'}"


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
        """
        Converts an Item domain object to an ItemForAI model.

        Args:
        ----
            item: The Item domain object to convert.
            sub_name: The name of the subscription this item belongs to.

        Returns:
        -------
            An ItemForAI instance with the same data as the provided item.

        """
        return cls(
            uuid=item.uuid,
            name=item.name,
            subscription_name=sub_name,
            description=item.description,
            provider=item.provider,
            published_at=item.published_at,
        )


class UserSubscriptionsAndTopics(BaseModel):
    subscriptions: list[SubscriptionForAI] = Field(
        description="List of user's subscriptions",
    )
    topics: list[TopicForAI] = Field(
        description="List of user's topics",
    )


class AgentOutput(BaseModel):
    response: str = Field(
        default="",
        description="Response for the user based on their query",
    )
    items_uuids: list[str] = Field(
        default_factory=list,
        description="List of content items UUIDs (32 hex) related to the user's query. "
                    "Can be empty if no items match.",
    )
    topics_were_created: bool = Field(
        default=False,
        description="Indicates whether any topics were created during the query processing.",
    )


class PydanticQueryAgentService(QueryAgentService):
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
        self.agent = create_agent(google_api_key)

    async def query(self, user_id: UUID, query: str, chat_id: UUID) -> AgentQueryResult:
        deps = AgentDependencies(
            user_uuid=user_id,
            user_repository=self.user_repository,
            subscription_repository=self.subscription_repository,
            item_repository=self.item_repository,
            topic_repository=self.topic_repository,
            previous_chat=await self.chat_repository.get(chat_id),
        )

        context = ""
        previously_chat = await self.chat_repository.get(chat_id)
        if previously_chat is not None and len(previously_chat.messages) > 0:
            context = "Previous chat messages:\n"
            for message in previously_chat.messages:
                if message.role == "user":
                    context += f"User: {message.content}\n"
                elif message.role == "assistant":
                    context += f"Assistant: {message.content}\n"
            context += "End of previous chat messages.\n"

        result = await self.agent.run(
            user_prompt=context + query,
            deps=deps,
            usage=RunUsage(requests=10),
        )

        output: AgentOutput = result.output

        items = []
        item_uuids = set(parse_ids_to_uuids(output.items_uuids))
        if len(output.items_uuids) > 0:
            items = await self.item_repository.find_items(
                criteria=ItemFilterCriteria(item_uuids),
                page_number=0,
                limit=len(output.items_uuids),
            )

        subscriptions_uuids = list({item.subscription_uuid for item in items})
        subscriptions = []
        if len(subscriptions_uuids) > 0:
            subscriptions = await self.subscription_repository.get_list(subscriptions_uuids)

        final_message = re.sub(
            r"https://linkurator\.com/(items|subscriptions)/([0-9a-fA-F-]{36})",
            lambda match: f"{self.base_url}/{match.group(1)}/{match.group(2)}/url",
            output.response,
        )

        return AgentQueryResult(
            message=final_message,
            items=items,
            subscriptions=subscriptions,
            topics_were_created=output.topics_were_created,
        )


def create_agent(api_key: str) -> Agent[AgentDependencies, AgentOutput]:
    """
    Creates a support agent that can be used to handle user queries.
    The agent will provide recommendations based on the user's subscriptions and interactions.
    """
    provider = GoogleProvider(
        api_key=api_key,
    )

    gemini_flash_model = GoogleModel(
        provider=provider,
        model_name="gemini-2.5-flash",
        settings=GoogleModelSettings(
            temperature=0.2,
            max_tokens=4096,
            google_thinking_config={"thinking_budget": 0},
        ),
    )

    ai_agent = Agent[AgentDependencies, AgentOutput](
        gemini_flash_model,
        deps_type=AgentDependencies,
        output_type=AgentOutput,
        system_prompt=(
            "You are a system to recommend videos, podcasts or articles to the user based on their query. "
            "You are able to create topics for the user to organize their subscriptions. "
            "Answer in the same language the user is using. "
            "Always use the customer's name in your responses. "
            "If the user has no subscriptions, inform them that you cannot recommend content without subscriptions. "
            "When creating topics, do not create similar topics if they already exist. "
            "Before creating topics, tell the user which exact subscriptions you are going to add to each topic. "
            "Do not create any topic without explicitly user consent. "
            "Items that belongs to a subscription included in any of the user topics are considered more relevant. "
            "Try first to find items from subscriptions before using keyword search. "
            "When finding items, try to find by a single keyword. "
            "Find items by keywords can be called maximum once with maximum ten keywords. "
            "It is ok to return empty lists of items ids if there are no matching items to the query. "
            "When the user asks for specific dates, ensure you do not return any items that were published before the date. "
            "Use markdown formatting, make titles bold and bullet points for lists. "
            "Summarize the titles if they are similar and provide the subscription names as links to the item. "
            "If the same title from different providers is found, summarize them in a single item with links. "
            "Add the provider name (YouTube or Spotify) to the links if it is required to distinguish between items. "
            "You do not have access to the content, it is important not to offer details or summaries about the content. "
            "Answer the user's query using items, subscriptions and topics that are relevant to the query. "
            "Do not ask the user to provide more information, use the information you have. "
            "If an item is referenced in the response, use a markdown link to the url https://linkurator.com/items/{item.uuid} "
            "If a subscription is referenced in the response, use a markdown link to the url https://linkurator.com/subscriptions/{subscription.uuid} "
            "Link titles cannot be multiline in markdown. "
        ),
    )

    @ ai_agent.system_prompt
    async def add_user_name(ctx: RunContext[AgentDependencies]) -> str:
        user = await ctx.deps.user_repository.get(
            ctx.deps.user_uuid,
        )
        if user is None:
            logfire.warning(
                "User not found for customer UUID",
                customer_uuid=ctx.deps.user_uuid,
            )
            return "The customer's name is unknown"
        return f"The customer's name is {user.first_name!r}"

    @ ai_agent.system_prompt
    async def add_today_date(_ctx: RunContext[AgentDependencies]) -> str:
        """Returns today's date in Weekday YYYY-MM-DD format."""
        now = datetime.now(tz=timezone.utc)
        return f"Today is {now.strftime("%A %Y-%m-%d")}"

    @ ai_agent.system_prompt
    async def user_subscriptions_and_topics(
            ctx: RunContext[AgentDependencies],
    ) -> str:
        """
        Returns the user's subscriptions and topics.

        Args:
        ----
            ctx: RunContext with dependencies

        """
        handler = GetUserSubscriptionsHandler(
            user_repository=ctx.deps.user_repository,
            subscription_repository=ctx.deps.subscription_repository,
        )
        subs = await handler.handle(
            user_id=ctx.deps.user_uuid,
        )
        subs_for_ai = [SubscriptionForAI.from_subscription(sub) for sub in subs]

        topics = await ctx.deps.topic_repository.get_by_user_id(ctx.deps.user_uuid)
        topics_for_ai = [TopicForAI.from_topic(topic) for topic in topics]

        context = "User's subscriptions:\n"
        if len(subs_for_ai) == 0:
            context += "The user has no subscriptions.\n"
        else:
            context += "\n".join([str(sub) for sub in subs_for_ai]) + "\n"

        context += "\nUser's topics:\n"
        if len(topics_for_ai) == 0:
            context += "The user has no topics.\n"
        else:
            context += "\n".join([str(topic_ai) for topic_ai in topics_for_ai]) + "\n"

        context += "End of user's subscriptions and topics.\n"

        return context

    @ ai_agent.system_prompt
    async def previous_items_information(
            ctx: RunContext[AgentDependencies],
    ) -> str:
        """
        Returns information about previously recommended items to avoid repetition.

        Args:
        ----
            ctx: RunContext with dependencies

        """
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

        context = "Items recommended to the user in the chat:\n"
        context += "\n".join([
            ItemForAI.from_item(item, indexed_subs_names[item.subscription_uuid]).model_dump_json()
            for item in items
        ]) + "\n"
        context += "End of previously recommended items.\n"

        return context

    @ ai_agent.tool
    async def find_subscriptions_items(
            ctx: RunContext[AgentDependencies],
            topic_ids: list[str] | None = None,
            subscription_ids: list[str] | None = None,
    ) -> list[ItemForAI]:
        """
        Get items from subscriptions and topics. Maximum three calls per query.

        Args:
        ----
            ctx: RunContext with dependencies
            topic_ids: List of topic UUIDs (32 hex) to filter items by
            subscription_ids: List of subscription UUIDs (32 hex) to filter items by

        """
        ctx.deps.find_subscriptions_items_calls += 1
        if ctx.deps.find_subscriptions_items_calls > 3:
            return []

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

        return [ItemForAI.from_item(item, indexed_subs_names[item.subscription_uuid]) for item in items]

    @ ai_agent.tool
    async def find_items_by_keywords(
            ctx: RunContext[AgentDependencies],
            keywords: list[str],
    ) -> list[ItemForAI]:
        """
        Finds items based on a single keyword search. Maximum one call per query with up to ten keywords.

        Args:
        ----
            ctx: RunContext with dependencies
            keywords: Keywords to search for in item titles. Maximum of ten keywords.

        """
        ctx.deps.find_items_by_keywords_calls += 1
        if ctx.deps.find_items_by_keywords_calls > 1:
            return []

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

        return [ItemForAI.from_item(item, indexed_subs_names[item.subscription_uuid]) for item in items]

    @ ai_agent.tool
    async def create_topic(
            ctx: RunContext[AgentDependencies],
            name: str,
            subscription_ids: list[str] | None = None,
    ) -> TopicForAI:
        """
        Creates a new topic for the user to organize their subscriptions.

        Args:
        ----
            ctx: RunContext with dependencies
            name: Name of the new topic
            subscription_ids: Optional list of subscription UUIDs to add to this topic

        """
        topic_uuid = uuid4()
        subscription_uuids = [UUID(sid) for sid in subscription_ids] if subscription_ids else []

        # Verify user owns the subscriptions
        if subscription_uuids:
            # Get user's subscriptions using the handler
            handler = GetUserSubscriptionsHandler(
                user_repository=ctx.deps.user_repository,
                subscription_repository=ctx.deps.subscription_repository,
            )
            user_subscriptions = await handler.handle(user_id=ctx.deps.user_uuid)
            user_subscription_ids = {sub.uuid for sub in user_subscriptions}

            # Filter to only include subscriptions the user actually owns
            subscription_uuids = [sid for sid in subscription_uuids if sid in user_subscription_ids]

        topic = Topic.new(
            uuid=topic_uuid,
            name=name,
            user_id=ctx.deps.user_uuid,
            subscription_ids=subscription_uuids,
        )

        await ctx.deps.topic_repository.add(topic)
        return TopicForAI.from_topic(topic)

    return ai_agent


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
