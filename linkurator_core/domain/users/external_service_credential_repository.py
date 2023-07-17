from abc import abstractmethod, ABC
from typing import List
from uuid import UUID

from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential, ExternalServiceType


class ExternalCredentialRepository(ABC):
    @abstractmethod
    async def get(self, user_id: UUID) -> List[ExternalServiceCredential]:
        pass

    @abstractmethod
    async def add(self, credentials: ExternalServiceCredential) -> None:
        pass

    @abstractmethod
    async def update(self, credentials: ExternalServiceCredential) -> None:
        pass

    @abstractmethod
    async def delete(
            self,
            user_id: UUID,
            credential_type: ExternalServiceType,
            credential_value: str
    ) -> None:
        pass

    @abstractmethod
    async def find_by_users_and_type(
            self,
            user_ids: List[UUID],
            credential_type: ExternalServiceType
    ) -> List[ExternalServiceCredential]:
        pass
