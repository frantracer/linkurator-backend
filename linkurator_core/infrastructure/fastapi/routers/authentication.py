import hashlib
import http
from typing import Any, Optional, Annotated
from urllib.parse import urljoin
from uuid import UUID

from fastapi import Request, status, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.routing import APIRouter
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, EmailStr, AnyUrl

from linkurator_core.application.auth.change_password_from_request import ChangePasswordFromRequest
from linkurator_core.application.auth.register_new_user_with_email import RegisterNewUserWithEmail
from linkurator_core.application.auth.register_new_user_with_google import RegisterUserHandler
from linkurator_core.application.auth.request_password_change import RequestPasswordChange
from linkurator_core.application.auth.validate_new_user_request import ValidateNewUserRequest
from linkurator_core.application.auth.validate_session_token import ValidateTokenHandler
from linkurator_core.application.auth.validate_user_password import ValidateUserPassword
from linkurator_core.domain.common.exceptions import InvalidRegistrationRequestError
from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.user import Username
from linkurator_core.infrastructure.fastapi.models import default_responses
from linkurator_core.infrastructure.fastapi.models.authentication import PasswordWith64HexCharacters
from linkurator_core.infrastructure.google.account_service import GoogleAccountService

COOKIE_EXPIRATION_IN_SECONDS = 3600 * 24 * 30
REDIRECT_URI_NAME = "redirect_uri"
TOKEN_COOKIE_NAME = "token"

YOUTUBE_CHANNEL_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


class NewUserSchema(BaseModel):
    email: EmailStr
    password: PasswordWith64HexCharacters
    first_name: str
    last_name: str
    username: str
    validation_base_url: AnyUrl


class LoginUserSchema(BaseModel):
    email: EmailStr
    password: PasswordWith64HexCharacters


class RequestPasswordChangeSchema(BaseModel):
    email: EmailStr
    validate_url: AnyUrl


class ChangePasswordSchema(BaseModel):
    new_password: PasswordWith64HexCharacters


def check_basic_auth(credentials: Annotated[HTTPBasicCredentials, Depends(HTTPBasic())]) -> None:
    hasher = hashlib.sha256()
    hasher.update(f"{credentials.username}:{credentials.password}".encode("utf-8"))
    digest = hasher.hexdigest()
    if digest != "f9faf149ff01da006b1d90c28047b2e8a0aab2eccfe4c0f9f1c2ab6f8e25e9e3":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect user or password",
            headers={"WWW-Authenticate": "Basic"},
        )


def unauthorized_error(error: str, redirect_uri: Optional[str]) -> RedirectResponse | JSONResponse:
    if redirect_uri is not None:
        encoded_error = error.replace(" ", "%20")
        uri = f"{redirect_uri}?error={encoded_error}"
        redirect_response = RedirectResponse(url=uri)
        redirect_response.delete_cookie(REDIRECT_URI_NAME)
        redirect_response.delete_cookie(TOKEN_COOKIE_NAME)
        return redirect_response

    error_response = JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": error})
    error_response.delete_cookie(TOKEN_COOKIE_NAME)
    error_response.delete_cookie(REDIRECT_URI_NAME)
    return error_response


def valid_auth_response(token: str, redirect_uri: Optional[str]) -> RedirectResponse | JSONResponse:
    if redirect_uri is not None:
        response = RedirectResponse(url=redirect_uri)
        response.set_cookie(key=TOKEN_COOKIE_NAME, value=token, expires=COOKIE_EXPIRATION_IN_SECONDS)
        return response

    response = RedirectResponse(url="/login")
    response.set_cookie(key=TOKEN_COOKIE_NAME, value=token, expires=COOKIE_EXPIRATION_IN_SECONDS)
    return response


def google_redirect_response(oauth_uri: str, redirect_uri: Optional[str]) -> RedirectResponse:
    print(oauth_uri)
    response = RedirectResponse(
        url=oauth_uri,
        status_code=http.HTTPStatus.FOUND)
    if redirect_uri is not None:
        response.set_cookie(key=REDIRECT_URI_NAME, value=redirect_uri)
    response.delete_cookie(TOKEN_COOKIE_NAME)
    return response


def valid_login_response(token: str, redirect_uri: Optional[str]) -> RedirectResponse | JSONResponse:
    if redirect_uri is not None:
        redirect_response = RedirectResponse(url=redirect_uri)
        redirect_response.delete_cookie(REDIRECT_URI_NAME)
        redirect_response.set_cookie(key=TOKEN_COOKIE_NAME, value=token, expires=COOKIE_EXPIRATION_IN_SECONDS)
        return redirect_response

    json_response = JSONResponse(content={TOKEN_COOKIE_NAME: token})
    json_response.delete_cookie(REDIRECT_URI_NAME)
    json_response.set_cookie(key=TOKEN_COOKIE_NAME, value=token, expires=COOKIE_EXPIRATION_IN_SECONDS)
    return json_response


def get_router(  # pylint: disable=too-many-statements
        google_client: GoogleAccountService,
        validate_token: ValidateTokenHandler,
        validate_user_password: ValidateUserPassword,
        register_user_with_google: RegisterUserHandler,
        register_user_with_email: RegisterNewUserWithEmail,
        validate_new_user_request: ValidateNewUserRequest,
        request_password_change: RequestPasswordChange,
        change_password_from_request: ChangePasswordFromRequest
) -> APIRouter:
    router = APIRouter()

    @router.get("/login",
                response_model=Session,
                responses={
                    status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
                    status.HTTP_307_TEMPORARY_REDIRECT: {"description": "Redirect to Google login page"},
                })
    async def login(request: Request, redirect_uri: str | None = None, error: str | None = None) -> Any:
        """
        Login endpoint
        """
        if redirect_uri is None:
            redirect_uri = request.cookies.get(REDIRECT_URI_NAME)

        if error is not None:
            return unauthorized_error(f"Login error {error}", redirect_uri)

        valid_session: Optional[Session] = None
        token = request.cookies.get(TOKEN_COOKIE_NAME)
        if token is not None:
            valid_session = await validate_token.handle(access_token=token)

        if valid_session is None:
            oauth_url = google_client.authorization_url(
                scopes=["email"],
                redirect_uri=urljoin(str(request.base_url), "/login_auth")
            )
            return google_redirect_response(oauth_url, redirect_uri)

        return valid_login_response(token=valid_session.token, redirect_uri=redirect_uri)

    @router.get("/login_auth")
    async def login_auth(request: Request, code: str | None = None, error: str | None = None) -> Any:
        redirect_uri = request.cookies.get(REDIRECT_URI_NAME)

        if error is not None:
            return unauthorized_error(f"Google error {error}", redirect_uri)

        if code is None:
            return unauthorized_error("No code returned", redirect_uri)

        tokens = google_client.validate_code(code=code, redirect_uri=urljoin(str(request.base_url), "/login_auth"))
        if tokens is None:
            return unauthorized_error("Invalid code", redirect_uri)

        session = await validate_token.handle(access_token=tokens.access_token)
        if session is None:
            return unauthorized_error("Invalid access token", redirect_uri)

        return valid_auth_response(token=session.token, redirect_uri="/login")

    @router.post("/login_email",
                 status_code=status.HTTP_200_OK,
                 responses={
                     status.HTTP_400_BAD_REQUEST: {"description": "Invalid request"},
                     status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
                 })
    async def login_email(credentials: LoginUserSchema) -> Any:
        """
        Login email endpoint
        """
        session = await validate_user_password.handle(email=credentials.email, password=str(credentials.password))
        if session is None:
            return unauthorized_error("Invalid credentials", None)

        return valid_login_response(token=session.token, redirect_uri=None)

    @router.get("/register")
    async def register(request: Request, redirect_uri: str | None = None) -> Any:
        """
        Login endpoint
        """
        scopes = ['profile', 'email', 'openid']
        oauth_url = google_client.authorization_url(
            scopes=scopes,
            redirect_uri=urljoin(str(request.base_url), "/register_auth")
        )
        return google_redirect_response(oauth_url, redirect_uri)

    @router.get("/register_auth")
    async def register_auth(request: Request, code: str | None = None, error: str | None = None) -> Any:
        """
        Auth endpoint
        """
        redirect_uri = request.cookies.get(REDIRECT_URI_NAME)

        auth_error: str

        if error is not None:
            auth_error = f"Google error {error}"

        elif code is None:
            auth_error = "No code returned"

        else:
            tokens = google_client.validate_code(
                code=code,
                redirect_uri=urljoin(str(request.base_url), "/register_auth"))
            if tokens is None:
                auth_error = "Invalid code"
            else:
                register_error = await register_user_with_google.handle(
                    access_token=tokens.access_token,
                    refresh_token=tokens.refresh_token)

                if register_error is None:
                    return valid_auth_response(token=tokens.access_token, redirect_uri="/login")

                auth_error = f"Registration error {register_error}"

        return unauthorized_error(auth_error, redirect_uri)

    @router.post("/register_email",
                 status_code=status.HTTP_201_CREATED,
                 responses={
                     status.HTTP_400_BAD_REQUEST: {"description": "Invalid request"},
                 })
    async def register_email(new_user: NewUserSchema) -> Any:
        """
        Register email endpoint
        """
        try:
            errors = await register_user_with_email.handle(
                email=new_user.email,
                password=str(new_user.password),
                first_name=new_user.first_name,
                last_name=new_user.last_name,
                username=Username(new_user.username),
                validation_base_url=new_user.validation_base_url
            )
            if errors:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"errors": ", ".join([str(e) for e in errors])})
            return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "Registration request sent"})
        except ValueError as exc:
            raise default_responses.bad_request(message=str(exc))

    @router.get("/validate_email/{request_uuid}",
                status_code=status.HTTP_200_OK,
                responses={
                    status.HTTP_400_BAD_REQUEST: {"description": "Invalid request"},
                })
    async def validate_email(request_uuid: UUID) -> Any:
        """
        Validate email endpoint
        """
        try:
            await validate_new_user_request.handle(request_uuid)
        except InvalidRegistrationRequestError:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Invalid request"})
        return JSONResponse(content={"message": "Email validated"})

    @router.get("/logout")
    async def logout(redirect_uri: Optional[str] = None) -> Any:
        """
        Logout endpoint
        """
        if redirect_uri is not None:
            redirect_res = RedirectResponse(url=redirect_uri)
            redirect_res.delete_cookie(key=TOKEN_COOKIE_NAME)
            return redirect_res

        response = JSONResponse(content={"message": "Logged out successfully"})
        response.delete_cookie(key=REDIRECT_URI_NAME)
        response.delete_cookie(key=TOKEN_COOKIE_NAME)
        return response

    @router.post("/revoke")
    async def revoke(request: Request) -> Any:
        token = request.cookies.get(TOKEN_COOKIE_NAME)
        if token is None:
            return unauthorized_error("No token provided", None)

        google_client.revoke_credentials(token)
        response = JSONResponse(content={"message": "Token revoked"})
        response.delete_cookie(key=TOKEN_COOKIE_NAME)
        return response

    @router.post("/change_password",
                 status_code=status.HTTP_204_NO_CONTENT
                 )
    async def request_change_password(password_change: RequestPasswordChangeSchema) -> None:
        """
        Request reset password endpoint
        """
        await request_password_change.handle(
            email=password_change.email,
            validate_base_url=password_change.validate_url)

    @router.post("/change_password/{request_id}",
                 status_code=status.HTTP_204_NO_CONTENT,
                 responses={
                     status.HTTP_400_BAD_REQUEST: {"description": "Invalid request"},
                     status.HTTP_404_NOT_FOUND: {"description": "Request not found"},
                 })
    async def change_password_from_previous_request(
            request_id: UUID,
            change_pass_request: ChangePasswordSchema
    ) -> None:
        """
        Change password from previous request
        """
        new_password = str(change_pass_request.new_password)
        result = await change_password_from_request.handle(request_id=request_id, new_password=new_password)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return router
