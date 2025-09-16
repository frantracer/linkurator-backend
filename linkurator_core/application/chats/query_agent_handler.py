from uuid import UUID

from linkurator_core.domain.chats.chat import Chat, ChatRole
from linkurator_core.domain.chats.chat_repository import ChatRepository
from linkurator_core.domain.common.event import NewChatQueryEvent
from linkurator_core.domain.common.event_bus_service import EventBusService
from linkurator_core.domain.common.exceptions import InvalidChatError, MessageIsBeingProcessedError, QueryRateLimitError


class QueryAgentHandler:
    def __init__(self,
                 chat_repository: ChatRepository,
                 event_bus: EventBusService,
                 ) -> None:
        self.chat_repository = chat_repository
        self.event_bus = event_bus

    async def handle(self, user_id: UUID | None, query: str, chat_id: UUID) -> None:
        chat = await self.chat_repository.get(chat_id)
        if chat is None:
            title = query[:47] + "..." if len(query) > 50 else query
            chat = Chat.new(uuid=chat_id, user_id=user_id, title=title)
            await self.chat_repository.add(chat)

        if chat.user_id != user_id:
            raise InvalidChatError()

        user_message_count = sum(1 for message in chat.messages if message.role == ChatRole.USER)
        if user_message_count >= 5:
            raise QueryRateLimitError()

        if chat.is_waiting_for_response():
            raise MessageIsBeingProcessedError()

        chat.add_user_message(query)
        await self.chat_repository.update(chat)

        await self.event_bus.publish(
            NewChatQueryEvent.new(chat_id=chat_id, query=query),
        )
