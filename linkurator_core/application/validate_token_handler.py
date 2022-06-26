from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from linkurator_core.domain.user import User
from linkurator_core.application.account_service import AccountService
from linkurator_core.domain.session import Session
from linkurator_core.domain.session_repository import SessionRepository
from linkurator_core.domain.user_repository import UserRepository


class ValidateTokenHandler:
    def __init__(self, user_repository: UserRepository, session_repository: SessionRepository,
                 account_service: AccountService):
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.account_service = account_service

    def handle(self, access_token: str, refresh_token: Optional[str]) -> Optional[Session]:
        session: Optional[Session] = self.session_repository.get(access_token)
        if session is not None and not session.is_expired():
            return session

        user_info = self.account_service.get_user_info(access_token)
        if user_info is not None:
            user = self.user_repository.get_by_email(user_info.email)
            if user is None:
                user = User.new(
                    uuid=uuid4(),
                    email=user_info.email,
                    avatar_url=user_info.picture,
                    locale=user_info.locale,
                    first_name=user_info.given_name,
                    last_name=user_info.family_name,
                    google_refresh_token=refresh_token)
                self.user_repository.add(user)
            else:
                user.avatar_url = user_info.picture
                user.locale = user_info.locale
                user.first_name = user_info.given_name
                user.last_name = user_info.family_name
                if refresh_token is not None and user.google_refresh_token != refresh_token:
                    user.google_refresh_token = refresh_token
                now = datetime.now(timezone.utc)
                user.updated_at = now
                user.last_login_at = now
                self.user_repository.update(user)

            session = Session(user_id=user.uuid,
                              token=access_token,
                              expires_at=datetime.now(timezone.utc) + timedelta(days=1))
            self.session_repository.add(session)

            return session

        return None
