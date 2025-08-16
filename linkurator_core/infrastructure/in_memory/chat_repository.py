from typing import Dict, List, Optional
from uuid import UUID

from linkurator_core.domain.chats.chat import Chat
from linkurator_core.domain.chats.chat_repository import ChatRepository


class InMemoryChatRepository(ChatRepository):
    def __init__(self) -> None:
        self._chats: Dict[UUID, Chat] = {}

    async def add(self, chat: Chat) -> None:
        self._chats[chat.uuid] = chat

    async def get(self, chat_id: UUID) -> Optional[Chat]:
        return self._chats.get(chat_id)

    async def get_by_user_id(self, user_id: UUID) -> List[Chat]:
        chats = [chat for chat in self._chats.values() if chat.user_id == user_id]
        return sorted(chats, key=lambda c: c.updated_at, reverse=True)

    async def update(self, chat: Chat) -> None:
        if chat.uuid in self._chats:
            self._chats[chat.uuid] = chat

    async def delete(self, chat_id: UUID) -> None:
        if chat_id in self._chats:
            del self._chats[chat_id]

    async def delete_all(self) -> None:
        self._chats.clear()
