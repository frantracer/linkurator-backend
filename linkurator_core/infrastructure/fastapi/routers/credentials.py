import http
from typing import Any, Callable, Coroutine, Optional, List

from fastapi import APIRouter, Depends, Response
from fastapi.applications import Request

from linkurator_core.application.users.add_external_credentials import AddExternalCredentialsHandler
from linkurator_core.application.users.delete_external_credential import DeleteExternalCredentialHandler
from linkurator_core.application.users.get_user_external_credentials import GetUserExternalCredentialsHandler
from linkurator_core.domain.common.exceptions import InvalidCredentialsError, CredentialsAlreadyExistsError
from linkurator_core.domain.users.external_service_credential import ExternalServiceType
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.credentials import ExternalCredentialSchema


def get_router(
        get_session: Callable[[Request], Coroutine[Any, Any, Optional[Session]]],
        get_user_external_credentials_handler: GetUserExternalCredentialsHandler,
        add_external_credential_handler: AddExternalCredentialsHandler,
        delete_external_credential_handler: DeleteExternalCredentialHandler
) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_model=List[ExternalCredentialSchema])
    async def get_user_external_credentials(
            session: Optional[Session] = Depends(get_session)
    ) -> Any:
        if session is None:
            return default_responses.not_authenticated()

        credentials = await get_user_external_credentials_handler.handle(session.user_id)
        return [ExternalCredentialSchema.from_domain_credential(credential) for credential in credentials]

    @router.post("/", responses={400: {'model': None}}, status_code=http.HTTPStatus.NO_CONTENT)
    async def add_external_credential(
            credential_type: ExternalServiceType,
            credential_value: str,
            session: Optional[Session] = Depends(get_session),
    ) -> Any:
        if session is None:
            return default_responses.not_authenticated()

        try:
            await add_external_credential_handler.handle(
                user_uuid=session.user_id,
                credential_value=credential_value,
                credential_type=credential_type)
        except InvalidCredentialsError:
            return Response(status_code=http.HTTPStatus.BAD_REQUEST, content="Invalid credentials")
        except CredentialsAlreadyExistsError:
            return Response(status_code=http.HTTPStatus.BAD_REQUEST, content="Credentials already exists")

        return Response(status_code=http.HTTPStatus.NO_CONTENT)

    @router.delete("/{credential_id}", responses={400: {'model': None}}, status_code=http.HTTPStatus.NO_CONTENT)
    async def delete_external_credential(
            credential_value: str,
            credential_type: ExternalServiceType,
            session: Optional[Session] = Depends(get_session),
    ) -> Any:
        if session is None:
            return default_responses.not_authenticated()

        await delete_external_credential_handler.handle(
            user_uuid=session.user_id,
            credential_value=credential_value,
            credential_type=credential_type)

        return Response(status_code=http.HTTPStatus.NO_CONTENT)

    return router
