import uuid

from linkurator_core.application.account_service import AccountService
from linkurator_core.domain.user import User
from linkurator_core.domain.user_repository import UserRepository


class RegisterUserHandler:
    def __init__(self, user_repository: UserRepository, account_service: AccountService):
        self.user_repository = user_repository
        self.account_service = account_service

    def handle(self, refresh_token: str):
        access_token = self.account_service.generate_access_token_from_refresh_token(refresh_token)

        if access_token is not None:
            user_info = self.account_service.get_user_info(access_token)
            if user_info is not None:
                user = self.user_repository.get_by_email(user_info.email)
                if user is None and refresh_token is not None:
                    user = User.new(uuid.uuid4(), user_info.given_name, user_info.email, refresh_token)
                    self.user_repository.add(user)
