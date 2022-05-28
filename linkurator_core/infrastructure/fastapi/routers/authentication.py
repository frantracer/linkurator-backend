import http
from typing import Any, Optional
from urllib.parse import urljoin

import fastapi
from fastapi.applications import Request
from fastapi.param_functions import Cookie
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

from linkurator_core.application.validate_token_handler import ValidateTokenHandler
from linkurator_core.infrastructure.google.account_service import GoogleAccountService


def get_router(validate_token_handler: ValidateTokenHandler, google_client: GoogleAccountService) -> APIRouter:
    router = APIRouter()

    @router.route("/login", methods=["GET", "POST"])
    async def login(request: Request) -> Any:
        """
        Login endpoint
        """
        token = request.cookies.get("token")
        if token is not None:
            session = validate_token_handler.handle(access_token=token, refresh_token=None)
            if session is None:
                response = JSONResponse(content={"message": "Invalid token"}, status_code=http.HTTPStatus.UNAUTHORIZED)
                response.delete_cookie(key="token")
                return response
            return JSONResponse(content={"token": session.token})

        scopes = ['profile', 'email', 'openid', "https://www.googleapis.com/auth/youtube.readonly"]
        return fastapi.responses.RedirectResponse(
            google_client.authorization_url(scopes=scopes,
                                            redirect_uri=urljoin(str(request.base_url), "/auth")),
            status_code=http.HTTPStatus.FOUND)

    @router.get("/auth")
    async def auth(request: Request) -> Any:
        """
        Auth endpoint
        """
        code = request.query_params.get("code", "")
        tokens = google_client.validate_code(code=code, redirect_uri=urljoin(str(request.base_url), "/auth"))
        if tokens is not None:
            token = tokens.access_token

            session = validate_token_handler.handle(access_token=token, refresh_token=tokens.refresh_token)

            if session is None:
                return JSONResponse(content={"message": "Invalid token"}, status_code=http.HTTPStatus.UNAUTHORIZED)

            response = JSONResponse(content={"token": session.token})
            response.set_cookie(key="token", value=token)
            return response
        return JSONResponse(content={"error": "Authentication failed"}, status_code=http.HTTPStatus.UNAUTHORIZED)

    @router.get("/logout")
    async def logout() -> Any:
        """
        Logout endpoint
        """
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
