from linkurator_core.domain.users.session import Session
from linkurator_core.domain.users.session_repository import SessionRepository
from linkurator_core.domain.users.user_repository import UserRepository

EXPIRATION_TIME_IN_SECONDS = 60 * 60 * 24 * 30  # 30 days


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

        session = Session.new(user_id=user.uuid, seconds_to_expire=EXPIRATION_TIME_IN_SECONDS)
        self.session_repository.add(session)
        return session
