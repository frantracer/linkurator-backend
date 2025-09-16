import logging
from uuid import UUID

import logfire
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.usage import RunUsage

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
)
from linkurator_core.infrastructure.ai_agents.router_agent import RouterAgent
from linkurator_core.infrastructure.ai_agents.topic_manager_agent import (
    TopicManagerAgent,
)
from linkurator_core.infrastructure.ai_agents.utils import build_chat_context, parse_ids_to_uuids


class MainQueryAgent(QueryAgentService):
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

        self.router_agent = RouterAgent(
            google_api_key=google_api_key,
        )
        self.recommendations_agent = RecommendationsAgent(
            google_api_key=google_api_key,
            base_url=base_url,
            user_repository=user_repository,
            subscription_repository=subscription_repository,
            item_repository=item_repository,
            topic_repository=topic_repository,
        )
        self.topic_manager_agent = TopicManagerAgent(
            google_api_key=google_api_key,
            user_repository=user_repository,
            subscription_repository=subscription_repository,
            topic_repository=topic_repository,
        )

    async def query(self, user_id: UUID | None, query: str, chat_id: UUID) -> AgentQueryResult:
        with logfire.span("MainAgent", user_id=str(user_id), chat_id=str(chat_id)):
            previous_chat = await self.chat_repository.get(chat_id)
            usage = RunUsage()

            retry = 0
            max_retries = 3
            while retry < max_retries:
                try:
                    return await self._perform_query(user_id, query, previous_chat, usage)
                except UnexpectedModelBehavior as e:
                    logging.exception(f"Error during AI agent query, retry {retry + 1}/{max_retries}: {e}")
                    retry += 1
            msg = "AI agent failed to process the query after multiple attempts"
            logging.error(msg)
            raise QueryAgentError(msg)

    async def _perform_query(self, user_id: UUID | None, query: str, chat: Chat | None, usage: RunUsage) -> AgentQueryResult:
        context = build_chat_context(chat)
        prompt = f"{context}\n{query}"

        # Step 1: Route the query to the appropriate agent
        routing_result = await self.router_agent.query(
            query=prompt,
            usage=usage,
        )

        # Step 2: Handle the query with the appropriate specialized agent
        if routing_result.agent_type == "recommendations":
            return await self._handle_recommendations_query(user_id, prompt, chat, usage)
        if routing_result.agent_type == "topic_manager" and user_id is not None:
            return await self._handle_topic_manager_query(user_id, prompt, chat, usage)
        # Default to recommendations if routing fails
        return await self._handle_recommendations_query(user_id, prompt, chat, usage)

    async def _handle_recommendations_query(
            self,
            user_id: UUID | None,
            query: str,
            chat: Chat | None,
            usage: RunUsage,
    ) -> AgentQueryResult:
        result = await self.recommendations_agent.query(
            query=query,
            previous_chat=chat,
            user_id=user_id,
            usage=usage,
        )

        return await self._build_agent_result(
            response=result.response,
            item_uuids_str=result.items_uuids,
            topics_were_created=False,
        )

    async def _handle_topic_manager_query(
            self,
            user_id: UUID,
            query: str,
            chat: Chat | None,
            usage: RunUsage,
    ) -> AgentQueryResult:
        result = await self.topic_manager_agent.query(
            query=query,
            user_id=user_id,
            previous_chat=chat,
            usage=usage)

        return await self._build_agent_result(
            response=result.response,
            item_uuids_str=[],
            topics_were_created=result.topics_were_created,
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

        return AgentQueryResult(
            message=response,
            items=items,
            subscriptions=subscriptions,
            topics_were_created=topics_were_created,
        )
