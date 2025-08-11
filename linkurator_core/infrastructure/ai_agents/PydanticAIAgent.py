from dataclasses import dataclass
from uuid import UUID, uuid4

import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.domain.items.item import Item, ItemProvider
from linkurator_core.domain.items.item_repository import AnyItemInteraction, ItemFilterCriteria, ItemRepository
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class SupportDependencies:
    user_uuid: UUID
    user_repository: UserRepository
    subscription_repository: SubscriptionRepository
    item_repository: ItemRepository
    topic_repository: TopicRepository


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


class ItemForAI(BaseModel):
    uuid: UUID = Field(
        description="Unique identifier for the item",
    )
    name: str = Field(
        description="Name of the item",
    )
    description: str | None = Field(
        default=None,
        description="Description of the item, if available",
    )
    provider: ItemProvider = Field(
        description="Provider of the item (e.g., 'youtube', 'spotify')",
    )

    @classmethod
    def from_item(cls, item: Item) -> "ItemForAI":
        """
        Converts an Item domain object to an ItemForAI model.

        Args:
        ----
            item: The Item domain object to convert.

        Returns:
        -------
            An ItemForAI instance with the same data as the provided item.

        """
        return cls(
            uuid=item.uuid,
            name=item.name,
            description=item.description,
            provider=item.provider,
        )


class SupportOutput(BaseModel):
    recommendation: str = Field(
        description="Content recommendation for the user based on their query",
    )
    topics: list[UUID] = Field(
        description="List of topics UUIDs created for the user to organize their subscriptions. "
                    "Can be empty if no topics match.",
    )
    subscriptions: list[UUID] = Field(
        description="List of subscriptions UUIDs that are relevant to the query. "
                    "Can be empty if no subscriptions match.",
    )
    content_items: list[UUID] = Field(
        description="List of content items UUIDs related to the user's query. "
                    "Can be empty if no items match.",
    )


def create_agent(api_key: str) -> Agent[SupportDependencies, SupportOutput]:
    """
    Creates a support agent that can be used to handle user queries.
    The agent will provide recommendations based on the user's subscriptions and interactions.
    """
    logfire.instrument_pydantic_ai()

    provider = OpenAIProvider(
        api_key=api_key,
    )
    llm_model = OpenAIModel(
        provider=provider,
        model_name="gpt-4.1",
    )
    support_agent = Agent[SupportDependencies, SupportOutput](
        llm_model,
        deps_type=SupportDependencies,
        output_type=SupportOutput,
        system_prompt=(
            "You are a system to recommend videos, podcasts or articles to the user based on their query. "
            "Always use the customer's name in your responses. "
        ),
    )

    @ support_agent.system_prompt
    async def add_user_name(ctx: RunContext[SupportDependencies]) -> str:
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

    @ support_agent.tool
    async def user_subscriptions(
            ctx: RunContext[SupportDependencies],
    ) -> list[SubscriptionForAI]:
        """Returns the user's subscriptions."""
        handler = GetUserSubscriptionsHandler(
            user_repository=ctx.deps.user_repository,
            subscription_repository=ctx.deps.subscription_repository,
        )
        subs = await handler.handle(
            user_id=ctx.deps.user_uuid,
        )
        return [SubscriptionForAI.from_subscription(sub) for sub in subs]

    @ support_agent.tool
    async def get_user_items(
            ctx: RunContext[SupportDependencies],
            page: int = 1,
            limit: int = 20,
            text_search: str | None = None,
            subscription_id: str | None = None,
            provider: str | None = None,
            interaction_type: str | None = None,
    ) -> list[ItemForAI]:
        """
        Gets items for the user with optional filtering.

        Args:
        ----
            page: Page number for pagination (default: 1)
            limit: Number of items per page (default: 20)
            text_search: Search in item names and descriptions
            subscription_id: Filter by subscription UUID
            provider: Filter by provider ('youtube' or 'spotify')
            interaction_type: Filter by user interaction ('recommended', 'discouraged', 'viewed', 'hidden')

        """
        # Get user's subscriptions using the handler
        handler = GetUserSubscriptionsHandler(
            user_repository=ctx.deps.user_repository,
            subscription_repository=ctx.deps.subscription_repository,
        )
        user_subscriptions = await handler.handle(user_id=ctx.deps.user_uuid)
        subscription_ids = [sub.uuid for sub in user_subscriptions]

        criteria = ItemFilterCriteria(
            subscription_ids=subscription_ids,
            text=text_search,
            interactions_from_user=ctx.deps.user_uuid,
        )

        # Apply additional filters
        if subscription_id:
            criteria.subscription_ids = [UUID(subscription_id)]

        if provider:
            from linkurator_core.domain.items.item import ItemProvider
            criteria.provider = ItemProvider(provider.lower())

        if interaction_type:
            interaction = AnyItemInteraction()
            if interaction_type == "recommended":
                interaction.recommended = True
            elif interaction_type == "discouraged":
                interaction.discouraged = True
            elif interaction_type == "viewed":
                interaction.viewed = True
            elif interaction_type == "hidden":
                interaction.hidden = True
            criteria.interactions = interaction

        items = await ctx.deps.item_repository.find_items(criteria, page - 1, limit)
        return [ItemForAI.from_item(item) for item in items]

    @ support_agent.tool
    async def search_items(
            ctx: RunContext[SupportDependencies],
            search_text: str,
            page: int = 1,
            limit: int = 20,
    ) -> list[ItemForAI]:
        """Searches across all items accessible to the user by text in name and description."""
        # Get user's subscriptions using the handler
        handler = GetUserSubscriptionsHandler(
            user_repository=ctx.deps.user_repository,
            subscription_repository=ctx.deps.subscription_repository,
        )
        user_subscriptions = await handler.handle(user_id=ctx.deps.user_uuid)
        subscription_ids = [sub.uuid for sub in user_subscriptions]

        criteria = ItemFilterCriteria(
            subscription_ids=subscription_ids,
            text=search_text,
        )

        items = await ctx.deps.item_repository.find_items(criteria, page - 1, limit)
        return [ItemForAI.from_item(item) for item in items]

    @ support_agent.tool
    async def get_user_recommendations(
            ctx: RunContext[SupportDependencies],
            limit: int = 10,
    ) -> list[ItemForAI]:
        """Gets items that the user has marked as recommended or that haven't been interacted with yet."""
        # Get user's subscriptions using the handler
        handler = GetUserSubscriptionsHandler(
            user_repository=ctx.deps.user_repository,
            subscription_repository=ctx.deps.subscription_repository,
        )
        user_subscriptions = await handler.handle(user_id=ctx.deps.user_uuid)
        subscription_ids = [sub.uuid for sub in user_subscriptions]

        # First try to get explicitly recommended items
        recommended_criteria = ItemFilterCriteria(
            subscription_ids=subscription_ids,
            interactions_from_user=ctx.deps.user_uuid,
            interactions=AnyItemInteraction(recommended=True),
        )
        recommended_items = await ctx.deps.item_repository.find_items(recommended_criteria, 0, limit)

        # If we need more items, get items without interactions (potentially new content)
        if len(recommended_items) < limit:
            remaining_limit = limit - len(recommended_items)
            uninteracted_criteria = ItemFilterCriteria(
                subscription_ids=subscription_ids,
                interactions_from_user=ctx.deps.user_uuid,
                interactions=AnyItemInteraction(without_interactions=True),
            )
            uninteracted_items = await ctx.deps.item_repository.find_items(
                uninteracted_criteria, 0, remaining_limit,
            )
            recommended_items.extend(uninteracted_items)

        return [ItemForAI.from_item(item) for item in recommended_items]

    @ support_agent.tool
    async def get_user_topics(
            ctx: RunContext[SupportDependencies],
    ) -> list[TopicForAI]:
        """Returns the user's topics."""
        topics = await ctx.deps.topic_repository.get_by_user_id(ctx.deps.user_uuid)
        return [TopicForAI.from_topic(topic) for topic in topics]

    @ support_agent.tool
    async def create_topic(
            ctx: RunContext[SupportDependencies],
            name: str,
            subscription_ids: list[str] | None = None,
    ) -> TopicForAI:
        """
        Creates a new topic for the user to organize their subscriptions.

        Args:
        ----
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

    return support_agent
