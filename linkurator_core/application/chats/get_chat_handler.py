from typing import Optional
from uuid import UUID

from linkurator_core.domain.chats.chat import Chat
from linkurator_core.domain.chats.chat_repository import ChatRepository


class GetChatHandler:
    def __init__(self, chat_repository: ChatRepository) -> None:
        self.chat_repository = chat_repository

    async def handle(self, chat_id: UUID, user_id: UUID) -> Optional[Chat]:
        chat = await self.chat_repository.get(chat_id)
        if chat is None or chat.user_id != user_id:
            return None
        return chat
