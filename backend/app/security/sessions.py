import hashlib
import secrets
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Session:
    user_id: str
    expires_at: float


class SessionStore:
    """Server-side sessions: the cookie holds an opaque random token, we store only its hash.

    Server-side (not a signed JWT) so logout truly revokes the session. In-memory is fine for a
    single Cloud Run instance; swap for Redis/Firestore when scaling out.
    """

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._purge_expired()
            self._sessions[self._key(token)] = Session(user_id, time.monotonic() + self._ttl)
        return token

    def resolve(self, token: str) -> str | None:
        with self._lock:
            session = self._sessions.get(self._key(token))
            if session is None:
                return None
            if session.expires_at <= time.monotonic():
                del self._sessions[self._key(token)]
                return None
            return session.user_id

    def revoke(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(self._key(token), None)

    def _purge_expired(self) -> None:
        now = time.monotonic()
        for key in [k for k, s in self._sessions.items() if s.expires_at <= now]:
            del self._sessions[key]
