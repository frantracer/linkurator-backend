import abc
from dataclasses import dataclass
from typing import Optional

from pydantic import AnyUrl


@dataclass
class UserInfo:
    given_name: str
    family_name: str
    email: str
    picture: AnyUrl
    locale: str


class AccountService(abc.ABC):
    @abc.abstractmethod
    def get_user_info(self, access_token: str) -> Optional[UserInfo]:
        raise NotImplementedError()
