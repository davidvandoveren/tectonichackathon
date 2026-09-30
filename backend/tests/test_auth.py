from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import DEMO_PASSWORD, login


def test_protected_endpoints_require_login(client: TestClient) -> None:
    for path in ["/api/v1/me", "/api/v1/accounts", "/api/v1/insights"]:
        assert client.get(path).status_code == 401


def test_login_sets_httponly_strict_cookie(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"username": "emma", "password": DEMO_PASSWORD}
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert response.json()["username"] == "emma"
    assert "password" not in response.text


def test_wrong_password_and_unknown_user_look_the_same(client: TestClient) -> None:
    wrong = client.post("/api/v1/auth/login", json={"username": "emma", "password": "nope-nope"})
    unknown = client.post("/api/v1/auth/login", json={"username": "ghost", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_login_is_rate_limited(client: TestClient) -> None:
    for _ in range(3):
        client.post("/api/v1/auth/login", json={"username": "jan", "password": "wrong-pass"})
    blocked = client.post("/api/v1/auth/login", json={"username": "jan", "password": DEMO_PASSWORD})
    assert blocked.status_code == 429


def test_logout_revokes_session_server_side(client: TestClient) -> None:
    login(client, "emma")
    token = next(iter(client.cookies.values()))
    assert client.post("/api/v1/auth/logout", json={}).status_code == 204
    client.cookies.set("session", token)  # replaying the old cookie must not work
    assert client.get("/api/v1/me").status_code == 401


def test_forged_session_cookie_is_rejected(client: TestClient) -> None:
    client.cookies.set("session", "u_emma")
    assert client.get("/api/v1/me").status_code == 401


def test_validation_errors_do_not_echo_input(client: TestClient) -> None:
    secret = "x" * 300
    response = client.post("/api/v1/auth/login", json={"username": "emma", "password": secret})
    assert response.status_code == 422
    assert secret not in response.text


def test_demo_login_is_disabled_by_default(client: TestClient) -> None:
    assert client.get("/api/v1/auth/config").json() == {"passwordless_login": False}
    response = client.post("/api/v1/auth/demo-login", json={"username": "emma"})
    assert response.status_code == 404
    assert client.get("/api/v1/me").status_code == 401


def test_demo_login_when_enabled(settings: Settings) -> None:
    settings.passwordless_login = True
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/auth/config").json() == {"passwordless_login": True}
        assert client.post("/api/v1/auth/demo-login", json={"username": "ghost"}).status_code == 401
        response = client.post("/api/v1/auth/demo-login", json={"username": "marie"})
        assert response.status_code == 200
        assert "httponly" in response.headers["set-cookie"].lower()
        assert client.get("/api/v1/me").json()["username"] == "marie"
        # Still owner-scoped: one-click login does not widen access.
        assert client.get("/api/v1/accounts/a_emma_1").status_code == 404
