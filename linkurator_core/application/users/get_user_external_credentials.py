from typing import List
from uuid import UUID

from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository


class GetUserExternalCredentialsHandler:
    def __init__(self, credentials_repository: ExternalCredentialRepository) -> None:
        self.credentials_repository = credentials_repository

    async def handle(self, user_uuid: UUID) -> List[ExternalServiceCredential]:
        return await self.credentials_repository.get(user_uuid)
