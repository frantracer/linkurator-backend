from __future__ import annotations

import http
from typing import Any, Callable, Coroutine

from fastapi import APIRouter, Depends, Request, status

from linkurator_core.application.users.add_external_credentials import AddExternalCredentialsHandler
from linkurator_core.application.users.delete_external_credential import DeleteExternalCredentialHandler
from linkurator_core.application.users.get_user_external_credentials import GetUserExternalCredentialsHandler
from linkurator_core.domain.common.exceptions import CredentialsAlreadyExistsError, InvalidCredentialsError
from linkurator_core.domain.users.external_service_credential import ExternalServiceType
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.credentials import ExternalCredentialSchema
from linkurator_core.infrastructure.fastapi.models.default_responses import EmptyResponse


def get_router(
        get_session: Callable[[Request], Coroutine[Any, Any, Session | None]],
        get_user_external_credentials_handler: GetUserExternalCredentialsHandler,
        add_external_credential_handler: AddExternalCredentialsHandler,
        delete_external_credential_handler: DeleteExternalCredentialHandler,
) -> APIRouter:
    router = APIRouter()

    @router.get("/",
                responses={
                    status.HTTP_401_UNAUTHORIZED: {"model": None},
                })
    async def get_user_external_credentials(
            session: Session | None = Depends(get_session),
    ) -> list[ExternalCredentialSchema]:
        if session is None:
            raise default_responses.not_authenticated()

        credentials = await get_user_external_credentials_handler.handle(session.user_id)
        return [ExternalCredentialSchema.from_domain_credential(credential) for credential in credentials]

    @router.post("/", responses={400: {"model": None}}, status_code=http.HTTPStatus.NO_CONTENT)
    async def add_external_credential(
            credential_type: ExternalServiceType,
            credential_value: str,
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        if session is None:
            raise default_responses.not_authenticated()

        try:
            await add_external_credential_handler.handle(
                user_uuid=session.user_id,
                credential_value=credential_value,
                credential_type=credential_type)
        except InvalidCredentialsError as error:
            msg = "Invalid credentials"
            raise default_responses.bad_request(msg) from error
        except CredentialsAlreadyExistsError as error:
            msg = "Credentials already exists"
            raise default_responses.bad_request(msg) from error

        return EmptyResponse()

    @router.delete("/{credential_id}",
                   responses={
                       status.HTTP_401_UNAUTHORIZED: {"model": None},
                   },
                   status_code=status.HTTP_204_NO_CONTENT)
    async def delete_external_credential(
            credential_value: str,
            credential_type: ExternalServiceType,
            session: Session | None = Depends(get_session),
    ) -> EmptyResponse:
        if session is None:
            raise default_responses.not_authenticated()

        await delete_external_credential_handler.handle(
            user_uuid=session.user_id,
            credential_value=credential_value,
            credential_type=credential_type)

        return EmptyResponse()

    return router
