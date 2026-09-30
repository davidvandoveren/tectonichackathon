from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.config import Settings, get_settings
from app.domain.bank import Bank
from app.domain.models import User
from app.security.rate_limit import FailureLimiter
from app.security.sessions import SessionStore


def session_cookie_name(settings: Settings) -> str:
    # The __Host- prefix makes browsers enforce Secure, Path=/ and no Domain attribute.
    return "__Host-session" if settings.cookie_secure else "session"


def get_bank(request: Request) -> Bank:
    bank: Bank = request.app.state.bank
    return bank


def get_sessions(request: Request) -> SessionStore:
    sessions: SessionStore = request.app.state.sessions
    return sessions


def get_login_limiter(request: Request) -> FailureLimiter:
    limiter: FailureLimiter = request.app.state.login_limiter
    return limiter


def get_today() -> date:
    return date.today()


SettingsDep = Annotated[Settings, Depends(get_settings)]
BankDep = Annotated[Bank, Depends(get_bank)]
SessionsDep = Annotated[SessionStore, Depends(get_sessions)]
LimiterDep = Annotated[FailureLimiter, Depends(get_login_limiter)]
TodayDep = Annotated[date, Depends(get_today)]


def get_current_user(
    request: Request, settings: SettingsDep, bank: BankDep, sessions: SessionsDep
) -> User:
    token = request.cookies.get(session_cookie_name(settings))
    user_id = sessions.resolve(token) if token else None
    user = bank.get_user(user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
