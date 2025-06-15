import logging

from linkurator_core.domain.common.exceptions import FailToRevokeCredentialsError
from linkurator_core.domain.users.account_service import AccountService
from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.session_repository import SessionRepository
from linkurator_core.domain.users.user_repository import UserRepository


class DeleteUserHandler:
    def __init__(self, user_repository: UserRepository, session_repository: SessionRepository,
                 account_service: AccountService) -> None:
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.account_service = account_service

    async def handle(self, user_session: Session) -> None:
        user_id = user_session.user_id
        user = await self.user_repository.get(user_id)
        if user is None:
            return

        try:
            self.account_service.revoke_credentials(user_session.token)
        except FailToRevokeCredentialsError:
            logging.warning("Failed to revoke credentials for user %s", user.username)

        self.session_repository.delete(user_session.token)

        await self.user_repository.delete(user_id)
