from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets


@dataclass
class Session:
    user_id: int
    expires_at: datetime


class SessionService:
    PUBLIC_ERROR = "Операция не выполнена"

    def __init__(self, ttl_seconds=24 * 60 * 60):
        self.ttl_seconds = ttl_seconds
        self.sessions = {}

    def create_session(self, user_id):
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            raise ValueError(self.PUBLIC_ERROR)

        token = secrets.token_urlsafe(32)
        self.sessions[token] = Session(
            user_id=user_id,
            expires_at=self._now() + timedelta(seconds=self.ttl_seconds),
        )
        return token

    def get_current_user_id(self, token):
        self.clear_expired_sessions()
        session = self.sessions.get(token)
        if session is None:
            raise ValueError(self.PUBLIC_ERROR)
        return session.user_id

    def delete_session(self, token):
        if token is not None:
            self.sessions.pop(token, None)

    def clear_expired_sessions(self):
        now = self._now()
        expired_tokens = [
            token
            for token, session in self.sessions.items()
            if session.expires_at <= now
        ]
        for token in expired_tokens:
            del self.sessions[token]

    def _now(self):
        return datetime.now(timezone.utc)
