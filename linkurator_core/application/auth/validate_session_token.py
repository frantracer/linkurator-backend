from datetime import datetime, timedelta, timezone
from typing import Optional

from linkurator_core.domain.users.account_service import AccountService
from linkurator_core.domain.users.session import Session, SESSION_DURATION_IN_SECONDS
from linkurator_core.domain.users.session_repository import SessionRepository
from linkurator_core.domain.users.user_repository import UserRepository


class ValidateTokenHandler:
    def __init__(self, user_repository: UserRepository,
                 session_repository: SessionRepository,
                 account_service: AccountService):
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.account_service = account_service

    async def handle(self, access_token: str) -> Optional[Session]:
        session: Optional[Session] = self.session_repository.get(access_token)
        if session is not None and not session.is_expired():
            return session

        user_info = self.account_service.get_user_info(access_token)
        if user_info is None:
            return None

        user = await self.user_repository.get_by_email(user_info.email)
        if user is None:
            return None

        now = datetime.now(timezone.utc)

        session = Session(user_id=user.uuid,
                          token=access_token,
                          expires_at=now + timedelta(seconds=SESSION_DURATION_IN_SECONDS))
        self.session_repository.add(session)

        user.last_login_at = now
        await self.user_repository.update(user)

        return session
