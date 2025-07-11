from datetime import datetime, timezone
from uuid import UUID

from linkurator_core.domain.common.exceptions import CredentialsAlreadyExistsError, InvalidCredentialsError
from linkurator_core.domain.users.external_credentials_checker_service import ExternalCredentialsCheckerService
from linkurator_core.domain.users.external_service_credential import ExternalServiceCredential, ExternalServiceType
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository


class AddExternalCredentialsHandler:
    def __init__(
            self,
            credentials_repository: ExternalCredentialRepository,
            credential_checker: ExternalCredentialsCheckerService) -> None:
        self.credentials_repository = credentials_repository
        self.credential_checker = credential_checker

    async def handle(self, user_uuid: UUID, credential_type: ExternalServiceType, credential_value: str) -> None:
        new_credential = ExternalServiceCredential(
            user_id=user_uuid,
            credential_type=credential_type,
            credential_value=credential_value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        credential = await self.credentials_repository.get_by_value_and_type(credential_type, credential_value)
        if credential is not None:
            msg = f"Credential for service {credential_type} already exists"
            raise CredentialsAlreadyExistsError(msg)

        if not await self.credential_checker.check(new_credential):
            msg = f"Invalid credential for service {credential_type}"
            raise InvalidCredentialsError(msg)

        await self.credentials_repository.add(new_credential)
