import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.config import Settings
from app.dependencies import (
    BankDep,
    CurrentUser,
    LimiterDep,
    SessionsDep,
    SettingsDep,
    session_cookie_name,
)
from app.domain.models import User
from app.schemas import AuthConfigOut, DemoLoginIn, DemoUserOut, LoginIn, MeOut
from app.security.client_ip import client_ip
from app.security.passwords import hash_password, verify_password
from app.security.sessions import SessionStore

router = APIRouter(tags=["auth"])

# Security events (failed logins, lockouts) for monitoring. Never passwords or tokens; user input
# is logged with %r so a crafted username cannot forge extra log lines (CWE-117).
security_log = logging.getLogger("kbc_poc.security")

# Verified against when the username is unknown, so response timing does not reveal which
# usernames exist.
_DUMMY_HASH, _DUMMY_SALT = hash_password("timing-equaliser-not-a-password")


@router.get("/auth/demo-users", response_model=list[DemoUserOut])
def demo_users(bank: BankDep) -> list[DemoUserOut]:
    return [
        DemoUserOut(
            username=u.username, display_name=f"{u.first_name} {u.last_name}", persona=u.persona
        )
        for u in bank.list_users()
    ]


@router.get("/auth/config", response_model=AuthConfigOut)
def auth_config(settings: SettingsDep) -> AuthConfigOut:
    return AuthConfigOut(passwordless_login=settings.passwordless_login)


@router.post("/auth/login", response_model=MeOut)
def login(
    body: LoginIn,
    request: Request,
    response: Response,
    settings: SettingsDep,
    bank: BankDep,
    sessions: SessionsDep,
    limiter: LimiterDep,
) -> MeOut:
    ip = client_ip(request, settings.trusted_proxy_hops)
    keys = (f"ip:{ip}", f"user:{body.username.lower()}")
    if limiter.is_blocked(*keys):
        security_log.warning("login blocked (rate limit) username=%r ip=%r", body.username, ip)
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try later")

    user = bank.find_user_by_username(body.username)
    if user is None:
        verify_password(body.password, _DUMMY_HASH, _DUMMY_SALT)
    if user is None or not verify_password(body.password, user.password_hash, user.password_salt):
        limiter.record_failure(*keys)
        security_log.warning("login failed username=%r ip=%r", body.username, ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    limiter.reset(f"user:{body.username.lower()}")
    return _start_session(request, response, settings, sessions, user)


@router.post("/auth/demo-login", response_model=MeOut)
def demo_login(
    body: DemoLoginIn,
    request: Request,
    response: Response,
    settings: SettingsDep,
    bank: BankDep,
    sessions: SessionsDep,
) -> MeOut:
    """One-click login as a synthetic persona. Only exists when PASSWORDLESS_LOGIN is on."""
    if not settings.passwordless_login:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    user = bank.find_user_by_username(body.username)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return _start_session(request, response, settings, sessions, user)


def _start_session(
    request: Request, response: Response, settings: Settings, sessions: SessionStore, user: User
) -> MeOut:
    old_token = request.cookies.get(session_cookie_name(settings))
    if old_token:
        sessions.revoke(old_token)  # no session fixation: always issue a fresh token
    response.set_cookie(
        key=session_cookie_name(settings),
        value=sessions.create(user.id),
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    return MeOut.model_validate(user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, settings: SettingsDep, sessions: SessionsDep) -> Response:
    token = request.cookies.get(session_cookie_name(settings))
    if token:
        sessions.revoke(token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        session_cookie_name(settings),
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    return response


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser) -> MeOut:
    return MeOut.model_validate(user)
