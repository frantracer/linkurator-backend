from uuid import UUID

from linkurator_core.domain.agents.query_agent_service import QueryAgentService
from linkurator_core.domain.chats.chat_repository import ChatRepository


class ProcessUserQueryHandler:
    def __init__(
            self,
            chat_repository: ChatRepository,
            query_agent_service: QueryAgentService,
    ) -> None:
        self.chat_repository = chat_repository
        self.query_agent_service = query_agent_service

    async def handle(self, chat_id: UUID, user_query: str) -> None:
        chat = await self.chat_repository.get(chat_id)
        if not chat:
            return

        try:
            response = await self.query_agent_service.query(
                user_id=chat.user_id,
                chat_id=chat_id,
                query=user_query,
            )
            chat.add_assistant_message(
                content=response.message,
                item_uuids=[item.uuid for item in response.items],
                subscription_uuids=[sub.uuid for sub in response.subscriptions],
                topic_were_created=response.topics_were_created,
            )
        except Exception as e:
            chat.add_error_message(str(e))

        await self.chat_repository.update(chat)
