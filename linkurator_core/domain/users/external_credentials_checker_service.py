from abc import ABC, abstractmethod

from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential


class ExternalCredentialsCheckerService(ABC):
    @abstractmethod
    async def check(self, credential: ExternalServiceCredential) -> bool:
        pass
