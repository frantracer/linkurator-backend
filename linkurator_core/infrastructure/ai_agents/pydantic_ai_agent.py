import logging
import re
from uuid import UUID

from pydantic_ai.exceptions import UnexpectedModelBehavior

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
from linkurator_core.infrastructure.ai_agents.core_router_agent import CoreRouterAgent, RouterDependencies
from linkurator_core.infrastructure.ai_agents.recommendations_agent import (
    RecommendationsAgent,
    RecommendationsDependencies,
)
from linkurator_core.infrastructure.ai_agents.topic_manager_agent import (
    TopicManagerAgent,
    TopicManagerDependencies,
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

        self.router_agent = CoreRouterAgent(google_api_key)
        self.recommendations_agent = RecommendationsAgent(google_api_key)
        self.topic_manager_agent = TopicManagerAgent(google_api_key)

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

        # Step 1: Route the query to the appropriate agent
        router_deps = RouterDependencies(
            user_uuid=user_id,
            user_repository=self.user_repository,
            subscription_repository=self.subscription_repository,
            topic_repository=self.topic_repository,
            previous_chat=previous_chat,
        )

        routing_result = await self.router_agent.route_query(router_deps, query)

        # Step 2: Handle the query with the appropriate specialized agent
        if routing_result.agent_type == "recommendations":
            return await self._handle_recommendations_query(user_id, query, previous_chat)
        if routing_result.agent_type == "topic_manager":
            return await self._handle_topic_manager_query(user_id, query, previous_chat)
        # Default to recommendations if routing fails
        return await self._handle_recommendations_query(user_id, query, previous_chat)

    async def _handle_recommendations_query(self, user_id: UUID, query: str, previous_chat: Chat | None) -> AgentQueryResult:
        deps = RecommendationsDependencies(
            user_uuid=user_id,
            user_repository=self.user_repository,
            subscription_repository=self.subscription_repository,
            item_repository=self.item_repository,
            topic_repository=self.topic_repository,
            previous_chat=previous_chat,
        )

        context = self._build_chat_context(previous_chat)
        result = await self.recommendations_agent.handle_query(deps, context + query)

        return await self._build_agent_result(
            response=result.response,
            item_uuids_str=result.items_uuids,
            topics_were_created=False,
        )

    async def _handle_topic_manager_query(self, user_id: UUID, query: str, previous_chat: Chat | None) -> AgentQueryResult:
        deps = TopicManagerDependencies(
            user_uuid=user_id,
            user_repository=self.user_repository,
            subscription_repository=self.subscription_repository,
            topic_repository=self.topic_repository,
            previous_chat=previous_chat,
        )

        context = self._build_chat_context(previous_chat)
        result = await self.topic_manager_agent.handle_query(deps, context + query)

        return await self._build_agent_result(
            response=result.response,
            item_uuids_str=[],
            topics_were_created=result.topics_were_created,
        )

    def _build_chat_context(self, previous_chat: Chat | None) -> str:
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
