import http
from typing import Any, Optional
from urllib.parse import urljoin

from fastapi import Request
from fastapi.param_functions import Cookie
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.routing import APIRouter

from linkurator_core.application.users.validate_token_handler import ValidateTokenHandler
from linkurator_core.infrastructure.google.account_service import GoogleAccountService

COOKIE_EXPIRATION_IN_SECONDS = 3600 * 24 * 30


def get_router(validate_token_handler: ValidateTokenHandler, google_client: GoogleAccountService) -> APIRouter:
    router = APIRouter()

    @router.get("/login")
    async def login(request: Request) -> Any:
        """
        Login endpoint
        """
        redirect_uri = request.cookies.get("redirect_uri")
        if redirect_uri is None:
            redirect_uri = request.query_params.get("redirect_uri")

        token = request.cookies.get("token")
        if token is not None:
            session = await validate_token_handler.handle(access_token=token, refresh_token=None)
            if session is not None:
                if redirect_uri is None:
                    return JSONResponse(content={"token": session.token})
                response = RedirectResponse(url=redirect_uri)
                response.delete_cookie("redirect_uri")
                return response

        scopes = ['profile', 'email', 'openid', "https://www.googleapis.com/auth/youtube.readonly"]
        response = RedirectResponse(
            url=google_client.authorization_url(
                scopes=scopes,
                redirect_uri=urljoin(str(request.base_url), "/auth")),
            status_code=http.HTTPStatus.FOUND)
        response.delete_cookie(key="token")
        if redirect_uri is not None:
            response.set_cookie("redirect_uri", redirect_uri)
        return response

    @router.get("/auth")
    async def auth(request: Request) -> Any:
        """
        Auth endpoint
        """
        code = request.query_params.get("code", "")
        tokens = google_client.validate_code(code=code, redirect_uri=urljoin(str(request.base_url), "/auth"))
        if tokens is not None:
            token = tokens.access_token

            session = await validate_token_handler.handle(access_token=token, refresh_token=tokens.refresh_token)

            if session is None:
                return JSONResponse(content={"message": "Invalid token"}, status_code=http.HTTPStatus.UNAUTHORIZED)

            response = RedirectResponse(url=urljoin(str(request.base_url), "/login"))
            response.set_cookie(key="token", value=token, expires=COOKIE_EXPIRATION_IN_SECONDS)
            return response
        return JSONResponse(content={"error": "Authentication failed"}, status_code=http.HTTPStatus.UNAUTHORIZED)

    @router.get("/logout")
    async def logout(request: Request) -> Any:
        """
        Logout endpoint
        """
        redirect_uri = request.query_params.get("redirect_uri")
        if redirect_uri is not None:
            redirect_res = RedirectResponse(url=redirect_uri)
            redirect_res.delete_cookie(key="token")
            return redirect_res

        response = JSONResponse(content={"message": "Logged out successfully"})
        response.delete_cookie(key="token")
        return response

    @router.get("/revoke")
    async def revoke(token: Optional[str] = Cookie(None)) -> Any:
        if token is None:
            return JSONResponse(content={"message": "No token provided"}, status_code=http.HTTPStatus.BAD_REQUEST)

        google_client.revoke_credentials(token)
        response = JSONResponse(content={"message": "Token revoked"})
        response.delete_cookie(key="token")
        return response

    return router
