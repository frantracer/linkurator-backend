from uuid import UUID

from linkurator_core.domain.chats.chat import Chat
from linkurator_core.domain.chats.chat_repository import ChatRepository


class GetUserChatsHandler:
    def __init__(self, chat_repository: ChatRepository) -> None:
        self.chat_repository = chat_repository

    async def handle(self, user_id: UUID) -> list[Chat]:
        return await self.chat_repository.get_by_user_id(user_id)
