import abc
from dataclasses import dataclass
from typing import Optional, List

from pydantic import AnyUrl


@dataclass
class CodeValidationResponse:
    access_token: str
    refresh_token: Optional[str]


@dataclass
class UserInfo:
    given_name: str
    family_name: str
    email: str
    picture: AnyUrl
    locale: str


class AccountService(abc.ABC):
    @abc.abstractmethod
    def authorization_url(self, scopes: List[str], redirect_uri: str) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_user_info(self, access_token: str) -> Optional[UserInfo]:
        raise NotImplementedError()

    @abc.abstractmethod
    def generate_access_token_from_refresh_token(self, refresh_token: str) -> Optional[str]:
        raise NotImplementedError()

    @abc.abstractmethod
    def validate_code(self, code: str, redirect_uri: str) -> Optional[CodeValidationResponse]:
        raise NotImplementedError()

    @abc.abstractmethod
    def revoke_credentials(self, access_token: str) -> None:
        raise NotImplementedError()
