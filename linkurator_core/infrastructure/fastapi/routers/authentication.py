import http
from typing import Any, Optional
from urllib.parse import urljoin

from fastapi import Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.routing import APIRouter

from linkurator_core.application.users.register_user_handler import RegisterUserHandler
from linkurator_core.application.users.validate_token_handler import ValidateTokenHandler
from linkurator_core.domain.users.session import Session
from linkurator_core.infrastructure.google.account_service import GoogleAccountService

COOKIE_EXPIRATION_IN_SECONDS = 3600 * 24 * 30
REDIRECT_URI_NAME = "redirect_uri"
TOKEN_COOKIE_NAME = "token"

YOUTUBE_CHANNEL_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"


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
        validate_token_handler: ValidateTokenHandler,
        register_user_handler: RegisterUserHandler,
        google_client: GoogleAccountService
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
            valid_session = await validate_token_handler.handle(access_token=token)

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

        session = await validate_token_handler.handle(access_token=tokens.access_token)
        if session is None:
            return unauthorized_error("Invalid access token", redirect_uri)

        return valid_auth_response(token=session.token, redirect_uri="/login")

    @router.get("/register")
    async def register(request: Request, redirect_uri: str | None = None) -> Any:
        """
        Login endpoint
        """
        scopes = ['profile', 'email', 'openid', YOUTUBE_CHANNEL_SCOPE]
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

            elif not google_client.token_has_scope_access(tokens.access_token, YOUTUBE_CHANNEL_SCOPE):
                auth_error = "Invalid scope access"

            else:
                register_error = await register_user_handler.handle(
                    access_token=tokens.access_token,
                    refresh_token=tokens.refresh_token)

                if register_error is None:
                    return valid_auth_response(token=tokens.access_token, redirect_uri="/login")

                auth_error = f"Registration error {register_error}"

        return unauthorized_error(auth_error, redirect_uri)

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

    return router
