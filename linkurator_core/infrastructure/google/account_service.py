import http
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests
from requests.auth import HTTPBasicAuth

from linkurator_core.domain.users.account_service import AccountService, UserInfo, CodeValidationResponse


class GoogleAccountService(AccountService):
    """
    GoogleAccountService allows to authenticate users with Google.

    More documentation: https://developers.google.com/identity/protocols/oauth2/openid-connect
    """

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    def authorization_url(self, scopes: List[str], redirect_uri: str) -> str:
        google_oauth_url = "https://accounts.google.com/o/oauth2/auth"
        query_params: Dict[str, str] = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": "ETL04Oop9e1yFQQFRM2KpHvbWwtMRV",
            "access_type": "offline",
            "include_granted_scopes": "true"
        }
        return f"{google_oauth_url}?{urlencode(query_params)}"

    def validate_code(self, code: str, redirect_uri: str) -> Optional[CodeValidationResponse]:
        google_oauth_url = "https://oauth2.googleapis.com/token"
        query_params: Dict[str, str] = {
            'grant_type': "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        }
        token_response = requests.post(google_oauth_url, auth=HTTPBasicAuth(self.client_id, self.client_secret),
                                       data=query_params)

        return CodeValidationResponse(
            access_token=token_response.json()['access_token'],
            refresh_token=token_response.json().get('refresh_token')
        )

    def revoke_credentials(self, access_token: str) -> None:
        revoke_response = requests.post('https://oauth2.googleapis.com/revoke',
                                        params={'token': access_token},
                                        headers={'content-type': 'application/x-www-form-urlencoded'})

        if revoke_response.status_code != http.HTTPStatus.OK:
            raise Exception(f'Failed to revoke token: {str(revoke_response.content)}')

    def generate_access_token_from_refresh_token(self, refresh_token: str) -> Optional[str]:
        google_oauth_url = "https://oauth2.googleapis.com/token"
        query_params: Dict[str, str] = {
            'grant_type': "refresh_token",
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        token_response = requests.post(google_oauth_url, auth=HTTPBasicAuth(self.client_id, self.client_secret),
                                       data=query_params)
        return token_response.json().get('access_token', None)

    def get_user_info(self, access_token: str) -> Optional[UserInfo]:
        user_info_url = "https://openidconnect.googleapis.com/v1/userinfo"
        user_info_response = requests.get(user_info_url, headers={"Authorization": f"Bearer {access_token}"})

        if user_info_response.status_code != http.HTTPStatus.OK:
            return None

        user_info = dict(user_info_response.json())
        return UserInfo(
            given_name=user_info['given_name'],
            family_name=user_info['family_name'],
            email=user_info['email'],
            picture=user_info['picture'],
            locale=user_info['locale']
        )
