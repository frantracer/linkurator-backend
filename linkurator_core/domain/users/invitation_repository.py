from abc import ABC, abstractmethod
from uuid import UUID

from linkurator_core.domain.users.invitation import Invitation


class InvitationRepository(ABC):
    @abstractmethod
    async def create_invitation(self, invitation: Invitation) -> None:
        pass

    @abstractmethod
    async def get_invitation_by_email(self, email: str) -> Invitation | None:
        pass

    @abstractmethod
    async def get_all_invitations(self) -> list[Invitation]:
        pass

    @abstractmethod
    async def delete_invitation(self, invitation_id: UUID) -> None:
        pass
