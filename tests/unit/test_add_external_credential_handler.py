from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from linkurator_core.application.users.add_external_credentials import AddExternalCredentialsHandler
from linkurator_core.domain.common.exceptions import InvalidCredentialsError, CredentialsAlreadyExistsError
from linkurator_core.domain.users.external_credentials_checker_service import ExternalCredentialsCheckerService
from linkurator_core.domain.users.external_service_credential import ExternalServiceType, ExternalServiceCredential
from linkurator_core.domain.users.external_service_credential_repository import ExternalCredentialRepository


@pytest.mark.asyncio
async def test_add_external_credentials():
    credentials_checker = AsyncMock(spec=ExternalCredentialsCheckerService)
    credentials_checker.check.return_value = True
    credentials_repository = AsyncMock(spec=ExternalCredentialRepository)
    credentials_repository.get_by_value_and_type.return_value = None
    handler = AddExternalCredentialsHandler(
        credentials_repository=credentials_repository,
        credential_checker=credentials_checker
    )

    await handler.handle(
        credential_value="test-api-key",
        credential_type=ExternalServiceType.YOUTUBE_API_KEY,
        user_uuid=UUID("af437132-799b-4673-86e8-1af62540ca23"))

    assert credentials_checker.check.called
    assert credentials_repository.add.called
    assert credentials_repository.add.call_args[0][0].credential_value == "test-api-key"
    assert credentials_repository.add.call_args[0][0].credential_type == ExternalServiceType.YOUTUBE_API_KEY
    assert credentials_repository.add.call_args[0][0].user_id == UUID("af437132-799b-4673-86e8-1af62540ca23")


@pytest.mark.asyncio
async def test_add_invalid_external_credentials_raises_exception():
    credentials_checker = AsyncMock(spec=ExternalCredentialsCheckerService)
    credentials_checker.check.return_value = False
    credentials_repository = AsyncMock(spec=ExternalCredentialRepository)
    credentials_repository.get_by_value_and_type.return_value = None
    handler = AddExternalCredentialsHandler(
        credentials_repository=credentials_repository,
        credential_checker=credentials_checker
    )

    with pytest.raises(InvalidCredentialsError):
        await handler.handle(
            credential_value="test-api-key",
            credential_type=ExternalServiceType.YOUTUBE_API_KEY,
            user_uuid=UUID("af437132-799b-4673-86e8-1af62540ca23"))

    assert credentials_checker.check.called
    assert not credentials_repository.add.called


@pytest.mark.asyncio
async def test_add_existing_external_credentials_raises_exception():
    credentials_checker = AsyncMock(spec=ExternalCredentialsCheckerService)
    credentials_checker.check.return_value = True
    credentials_repository = AsyncMock(spec=ExternalCredentialRepository)
    existing_credential = ExternalServiceCredential(
        user_id=UUID("2261cc75-e64d-4c7f-b5dd-b42b70e3f583"),
        credential_type=ExternalServiceType.YOUTUBE_API_KEY,
        credential_value="test-api-key",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    credentials_repository.get_by_value_and_type.return_value = existing_credential

    handler = AddExternalCredentialsHandler(
        credentials_repository=credentials_repository,
        credential_checker=credentials_checker
    )

    with pytest.raises(CredentialsAlreadyExistsError):
        await handler.handle(
            credential_value=existing_credential.credential_value,
            credential_type=existing_credential.credential_type,
            user_uuid=UUID("af437132-799b-4673-86e8-1af62540ca23"))

    assert credentials_repository.get_by_value_and_type.called
    assert not credentials_repository.add.called
