from fastapi import APIRouter, HTTPException, Request, Response, status

from app.dependencies import (
    BankDep,
    CurrentUser,
    LimiterDep,
    SessionsDep,
    SettingsDep,
    session_cookie_name,
)
from app.schemas import DemoUserOut, LoginIn, MeOut
from app.security.passwords import hash_password, verify_password

router = APIRouter(tags=["auth"])

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
    client_ip = request.client.host if request.client else "unknown"
    keys = (f"ip:{client_ip}", f"user:{body.username.lower()}")
    if limiter.is_blocked(*keys):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts, try later")

    user = bank.find_user_by_username(body.username)
    if user is None:
        verify_password(body.password, _DUMMY_HASH, _DUMMY_SALT)
    if user is None or not verify_password(body.password, user.password_hash, user.password_salt):
        limiter.record_failure(*keys)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    limiter.reset(f"user:{body.username.lower()}")
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
