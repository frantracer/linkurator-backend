import abc
from typing import Optional

from linkurator_core.domain.users.session import Session


class SessionRepository(abc.ABC):
    @abc.abstractmethod
    def get(self, token: str) -> Optional[Session]:
        pass

    @abc.abstractmethod
    def add(self, session: Session) -> None:
        pass

    @abc.abstractmethod
    def delete(self, token: str) -> None:
        pass
