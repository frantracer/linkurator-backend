from uuid import UUID

from linkurator_core.domain.chats.chat_repository import ChatRepository


class DeleteChatHandler:
    def __init__(self, chat_repository: ChatRepository) -> None:
        self.chat_repository = chat_repository

    async def handle(self, chat_id: UUID, user_id: UUID) -> bool:
        """
        Delete a chat conversation.

        Args:
        ----
            chat_id (UUID): The ID of the chat to delete.
            user_id (UUID): The ID of the user requesting the deletion.

        """
        chat = await self.chat_repository.get(chat_id)
        if chat is None or chat.user_id != user_id:
            return False

        await self.chat_repository.delete(chat_id)
        return True
