from datetime import date, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.config import Settings, get_settings
from app.domain.bank import Bank
from app.domain.models import User
from app.moments.state import KateState
from app.security.rate_limit import FailureLimiter
from app.security.sessions import SessionStore

# The /duo demo page shows two phones side by side, each logged in as another persona. Each phone
# sends its slot in this header and gets its own session cookie. Only these values are accepted.
SESSION_SLOT_HEADER = "x-session-slot"
SESSION_SLOTS = frozenset({"a", "b"})


def session_cookie_name(settings: Settings, request: Request) -> str:
    # The __Host- prefix makes browsers enforce Secure, Path=/ and no Domain attribute.
    base = "__Host-session" if settings.cookie_secure else "session"
    slot = request.headers.get(SESSION_SLOT_HEADER, "")
    return f"{base}-{slot}" if slot in SESSION_SLOTS else base


def get_bank(request: Request) -> Bank:
    bank: Bank = request.app.state.bank
    return bank


def get_sessions(request: Request) -> SessionStore:
    sessions: SessionStore = request.app.state.sessions
    return sessions


def get_login_limiter(request: Request) -> FailureLimiter:
    limiter: FailureLimiter = request.app.state.login_limiter
    return limiter


def get_kate_state(request: Request) -> KateState:
    state: KateState = request.app.state.kate
    return state


def get_today(request: Request) -> date:
    """Today, as the app sees it.

    The demo time machine shifts this so the whole app — balances, insights and the Kate feed —
    moves together. Without a shift it is simply the real date.
    """
    state: KateState | None = getattr(request.app.state, "kate", None)
    offset = state.time_offset_days if state is not None else 0
    return date.today() + timedelta(days=offset)


SettingsDep = Annotated[Settings, Depends(get_settings)]
BankDep = Annotated[Bank, Depends(get_bank)]
SessionsDep = Annotated[SessionStore, Depends(get_sessions)]
LimiterDep = Annotated[FailureLimiter, Depends(get_login_limiter)]
TodayDep = Annotated[date, Depends(get_today)]
KateStateDep = Annotated[KateState, Depends(get_kate_state)]


def get_current_user(
    request: Request, settings: SettingsDep, bank: BankDep, sessions: SessionsDep
) -> User:
    token = request.cookies.get(session_cookie_name(settings, request))
    user_id = sessions.resolve(token) if token else None
    user = bank.get_user(user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_admin_user(user: CurrentUser, settings: SettingsDep) -> User:
    """Gate for the demo-only admin endpoints.

    Answers 404, never 403: a caller who may not use an endpoint does not get to learn that it
    exists. Same reasoning as `404` for another customer's account elsewhere in this API.
    """
    if user.username not in settings.admin_username_set:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return user


AdminUser = Annotated[User, Depends(get_admin_user)]
