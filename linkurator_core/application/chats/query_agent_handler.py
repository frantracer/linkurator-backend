from uuid import UUID

from linkurator_core.domain.agents.query_agent_service import AgentQueryResult, QueryAgentService
from linkurator_core.domain.chats.chat import Chat
from linkurator_core.domain.chats.chat_repository import ChatRepository
from linkurator_core.domain.common.exceptions import InvalidChatError


class QueryAgentHandler:
    def __init__(self, query_agent_service: QueryAgentService, chat_repository: ChatRepository) -> None:
        self.query_agent_service = query_agent_service
        self.chat_repository = chat_repository

    async def handle(self, user_id: UUID, query: str, chat_id: UUID) -> AgentQueryResult:
        chat = await self.chat_repository.get(chat_id)
        if chat is None:
            title = query[:47] + "..." if len(query) > 50 else query
            chat = Chat.new(uuid=chat_id, user_id=user_id, title=title)
            await self.chat_repository.add(chat)

        if chat.user_id != user_id:
            raise InvalidChatError()

        # Get the AI response
        result = await self.query_agent_service.query(user_id, query, chat_id)

        # Add messages to chat
        chat = await self.chat_repository.get(chat_id)
        if chat is not None:
            chat.add_user_message(query)
            chat.add_assistant_message(
                result.message,
                item_uuids=[item.uuid for item in result.items],
                subscription_uuids=[sub.uuid for sub in result.subscriptions],
                topic_uuids=[topic.uuid for topic in result.topics],
            )
            await self.chat_repository.update(chat)

        return result
