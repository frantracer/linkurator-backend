import http
import json
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import fastapi
import requests
from fastapi.applications import Request
from fastapi.param_functions import Cookie
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from requests.auth import HTTPBasicAuth


def get_router() -> APIRouter:
    router = APIRouter()

    with open("client_secret.json", "r", encoding='UTF-8') as secrets_file:
        secrets = json.loads(secrets_file.read())
        client_id = secrets["web"]["client_id"]
        client_secret = secrets["web"]["client_secret"]
    scopes = ['email', 'openid']

    @router.route("/login", methods=["GET", "POST"])
    async def login(request: Request) -> Any:
        """
        Login endpoint
        """
        token = request.cookies.get("token")
        if token is not None:
            return JSONResponse(content={"token_login": token})

        google_oauth_url = "https://accounts.google.com/o/oauth2/auth"
        query_params: Dict[str, str] = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "http://localhost:9000/auth",
            "scope": " ".join(scopes),
            "state": "ETL04Oop9e1yFQQFRM2KpHvbWwtMRV",
            "access_type": "offline",
            "include_granted_scopes": "true"
        }
        authorization_url = f"{google_oauth_url}?{urlencode(query_params)}"
        return fastapi.responses.RedirectResponse(
            authorization_url,
            status_code=http.HTTPStatus.FOUND)

    @router.get("/auth")
    async def auth(code: str = "") -> Any:
        """
        Auth endpoint
        """
        google_oauth_url = "https://oauth2.googleapis.com/token"
        query_params: Dict[str, str] = {
            'grant_type': "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:9000/auth"
        }
        token_response = requests.post(google_oauth_url, auth=HTTPBasicAuth(client_id, client_secret),
                                       data=query_params)
        token = token_response.json().get("access_token")

        if token is not None:
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
        revoke_response = requests.post('https://oauth2.googleapis.com/revoke',
                                        params={'token': token},
                                        headers={'content-type': 'application/x-www-form-urlencoded'})

        if revoke_response.status_code == http.HTTPStatus.OK:
            response = JSONResponse(content={"message": "Token revoked"})
            response.delete_cookie(key="token")
            return response
        return JSONResponse(content={"error": "Failed to revoke token"},
                            status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR)

    return router
