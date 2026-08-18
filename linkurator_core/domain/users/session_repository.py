import abc
from typing import Optional

from linkurator_core.domain.users.session import Session


class SessionRepository(abc.ABC):
    @abc.abstractmethod
    async def get(self, token: str) -> Optional[Session]:
        pass

    @abc.abstractmethod
    async def add(self, session: Session) -> None:
        pass

    @abc.abstractmethod
    async def delete(self, token: str) -> None:
        pass
