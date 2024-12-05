from datetime import datetime, timezone

from linkurator_core.domain.users.session import Session, SESSION_DURATION_IN_SECONDS
from linkurator_core.domain.users.session_repository import SessionRepository
from linkurator_core.domain.users.user_repository import UserRepository


class ValidateUserPassword:
    def __init__(self, user_repository: UserRepository, session_repository: SessionRepository):
        self.user_repository = user_repository
        self.session_repository = session_repository

    async def handle(self, email: str, password: str) -> Session | None:
        user = await self.user_repository.get_by_email(email)
        if user is None:
            return None

        password_is_valid = user.validate_password(password)
        if not password_is_valid:
            return None

        session = Session.new(user_id=user.uuid, seconds_to_expire=SESSION_DURATION_IN_SECONDS)
        self.session_repository.add(session)

        user.last_login_at = datetime.now(timezone.utc)
        await self.user_repository.update(user)

        return session
