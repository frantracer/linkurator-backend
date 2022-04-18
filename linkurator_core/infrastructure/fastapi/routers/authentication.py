import http
import json
from typing import Any, Optional

import fastapi
from fastapi.applications import Request
from fastapi.param_functions import Cookie
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

from linkurator_core.infrastructure.google.account_service import GoogleAccountService


def get_router() -> APIRouter:
    router = APIRouter()

    with open("client_secret.json", "r", encoding='UTF-8') as secrets_file:
        secrets = json.loads(secrets_file.read())
        client_id = secrets["web"]["client_id"]
        client_secret = secrets["web"]["client_secret"]

    google_client = GoogleAccountService(client_id=client_id, client_secret=client_secret)

    @router.route("/login", methods=["GET", "POST"])
    async def login(request: Request) -> Any:
        """
        Login endpoint
        """
        token = request.cookies.get("token")
        if token is not None:
            return JSONResponse(content={"token_login": token})

        return fastapi.responses.RedirectResponse(
            google_client.authorization_url(scopes=['profile', 'email', 'openid'],
                                            redirect_uri="http://localhost:9000/auth"),
            status_code=http.HTTPStatus.FOUND)

    @router.get("/auth")
    async def auth(code: str = "") -> Any:
        """
        Auth endpoint
        """
        tokens = google_client.validate_code(code=code, redirect_uri="http://localhost:9000/auth")
        if tokens is not None:
            token = tokens.access_token
            print(tokens.refresh_token)
            response = JSONResponse(content={"token_auth": token})
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
