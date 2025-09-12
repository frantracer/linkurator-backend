import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Union
from uuid import UUID, uuid4

import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.tools import ToolDefinition

from linkurator_core.application.subscriptions.get_user_subscriptions_handler import GetUserSubscriptionsHandler
from linkurator_core.domain.chats.chat import Chat
from linkurator_core.domain.subscriptions.subscription import Subscription, SubscriptionProvider
from linkurator_core.domain.subscriptions.subscription_repository import SubscriptionRepository
from linkurator_core.domain.topics.topic import Topic
from linkurator_core.domain.topics.topic_repository import TopicRepository
from linkurator_core.domain.users.user_repository import UserRepository


@dataclass
class TopicManagerDependencies:
    user_uuid: UUID
    user_repository: UserRepository
    subscription_repository: SubscriptionRepository
    topic_repository: TopicRepository
    previous_chat: Chat | None


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


class TopicManagerOutput(BaseModel):
    response: str = Field(
        default="",
        description="Response for the user based on their query",
    )
    topics_were_created: bool = Field(
        default=False,
        description="Indicates whether any topics were created during the query processing.",
    )


class TopicManagerAgent:
    def __init__(self, google_api_key: str) -> None:
        self.agent = self._create_agent(google_api_key)

    def _create_agent(self, api_key: str) -> Agent[TopicManagerDependencies, TopicManagerOutput]:
        provider = GoogleProvider(api_key=api_key)

        gemini_flash_model = GoogleModel(
            provider=provider,
            model_name="gemini-2.5-flash",
            settings=GoogleModelSettings(
                temperature=0.2,
                google_thinking_config={"thinking_budget": 0},
            ),
        )

        ai_agent = Agent[TopicManagerDependencies, TopicManagerOutput](
            gemini_flash_model,
            deps_type=TopicManagerDependencies,
            output_type=TopicManagerOutput,
            system_prompt=(
                "You are a topic management system that helps users organize their subscriptions into topics. "
                "Answer in the same language the user is using. "
                "Always use the customer's name in your responses. "
                "When creating topics, do not create similar topics if they already exist. "
                "Before creating topics, tell the user which exact subscriptions you are going to add to each topic. "
                "Help the user by proposing topics when the user requires it. "
                "Only create topics if you have explicitly been asked to do so. "
                "Use markdown formatting, make titles bold and bullet points for lists. "
                "Answer the user's query using topics and subscriptions that are relevant to the query. "
                "Do not ask the user to provide more information, use the information you have. "
                "If a subscription is referenced in the response, use a markdown link to the url https://linkurator.com/subscriptions/{subscription.uuid} "
                "The response must have 1000 words maximum. "
            ),
        )

        @ai_agent.system_prompt
        async def add_user_name(ctx: RunContext[TopicManagerDependencies]) -> str:
            user = await ctx.deps.user_repository.get(ctx.deps.user_uuid)
            if user is None:
                logfire.warning(
                    "User not found for customer UUID",
                    customer_uuid=ctx.deps.user_uuid,
                )
                return "The customer's name is unknown"
            return f"The customer's name is {user.first_name!r}"

        @ai_agent.system_prompt
        async def add_today_date(_ctx: RunContext[TopicManagerDependencies]) -> str:
            now = datetime.now(tz=timezone.utc)
            return f"Today is {now.strftime('%A %Y-%m-%d')}"

        @ai_agent.system_prompt
        async def user_subscriptions_and_topics(
            ctx: RunContext[TopicManagerDependencies],
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

        @ai_agent.tool
        async def create_topic(
            ctx: RunContext[TopicManagerDependencies],
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

    async def handle_query(self, deps: TopicManagerDependencies, query: str) -> TopicManagerOutput:
        result = await self.agent.run(user_prompt=query, deps=deps)
        return result.output


async def filter_tools(
    ctx: RunContext[TopicManagerDependencies], tool_defs: list[ToolDefinition],
) -> Union[list[ToolDefinition], None]:
    return tool_defs


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
