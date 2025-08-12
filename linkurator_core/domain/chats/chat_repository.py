import abc
from typing import List, Optional
from uuid import UUID

from linkurator_core.domain.chats.chat import Chat


class ChatRepository(abc.ABC):
    @abc.abstractmethod
    async def add(self, chat: Chat) -> None: ...

    @abc.abstractmethod
    async def get(self, chat_id: UUID) -> Optional[Chat]: ...

    @abc.abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> List[Chat]: ...

    @abc.abstractmethod
    async def update(self, chat: Chat) -> None: ...

    @abc.abstractmethod
    async def delete(self, chat_id: UUID) -> None: ...

    @abc.abstractmethod
    async def delete_all(self) -> None: ...
