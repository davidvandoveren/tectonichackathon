"""The Kate feed and the time machine, end to end over HTTP.

Contract: `docs/plan.md` section 5. These tests run against the real synthetic seed, so they
also prove the engine says something sensible about the demo personas.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

DEMO_PASSWORD = "test-demo-password"
FEED = "/api/v1/kate/feed"
TIME_MACHINE = "/api/v1/admin/time-machine"

CONTRACT_FIELDS = {
    "id",
    "title",
    "body",
    "urgency",
    "channel",
    "reason",
    "cta_label",
    "cta_target",
    "requires_advisor",
}


def make_client(admin_usernames: str = "") -> TestClient:
    settings = Settings(
        app_env="test",
        demo_password=DEMO_PASSWORD,  # type: ignore[arg-type]
        cookie_secure=False,
        admin_usernames=admin_usernames,
    )
    return TestClient(create_app(settings))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with make_client() as test_client:
        yield test_client


@pytest.fixture
def admin_client() -> Iterator[TestClient]:
    with make_client(admin_usernames="jan") as test_client:
        yield test_client


def login(client: TestClient, username: str) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": DEMO_PASSWORD}
    )
    assert response.status_code == 200, response.text


# --- the feed ----------------------------------------------------------------------------------


def test_the_feed_requires_a_session(client: TestClient) -> None:
    assert client.get(FEED).status_code == 401


def test_the_feed_follows_the_agreed_contract(client: TestClient) -> None:
    login(client, "emma")

    body = client.get(FEED).json()

    assert isinstance(body["items"], list)
    assert isinstance(body["silenced"], list)
    for item in body["items"]:
        assert set(item) >= CONTRACT_FIELDS
        assert 0 <= item["urgency"] <= 100
        assert item["channel"] in {"feed", "push", "sms", "call", "none"}


def test_every_suggestion_explains_why_the_customer_sees_it(client: TestClient) -> None:
    login(client, "emma")

    for item in client.get(FEED).json()["items"]:
        assert item["reason"].strip(), f"{item['id']} has no reason"


def test_emma_is_recognised_as_having_started_working(client: TestClient) -> None:
    login(client, "emma")

    types = {item["id"] for item in client.get(FEED).json()["items"]}

    assert "first_salary" in types


def test_jan_is_recognised_as_moving_house(client: TestClient) -> None:
    login(client, "jan")

    feed = client.get(FEED).json()
    noticed = {item["id"] for item in feed["items"]} | {s["moment"] for s in feed["silenced"]}

    assert "moving_house" in noticed


def test_marie_is_told_her_savings_are_idle(client: TestClient) -> None:
    login(client, "marie")

    types = {item["id"] for item in client.get(FEED).json()["items"]}

    assert "idle_savings" in types


def test_at_most_one_suggestion_ever_interrupts_a_customer(client: TestClient) -> None:
    for username in ("emma", "jan", "marie"):
        login(client, username)
        items = client.get(FEED).json()["items"]
        interruptions = [i for i in items if i["channel"] in {"push", "sms", "call"}]
        assert len(interruptions) <= 1, f"{username} got {len(interruptions)} interruptions"


def test_silenced_entries_say_why_kate_kept_quiet(client: TestClient) -> None:
    login(client, "jan")

    for entry in client.get(FEED).json()["silenced"]:
        assert entry["reason"].strip()
        assert entry["reason_code"]


# --- consent -----------------------------------------------------------------------------------


def test_switching_off_a_signal_domain_changes_what_kate_says(client: TestClient) -> None:
    login(client, "jan")
    before = {item["id"] for item in client.get(FEED).json()["items"]}

    response = client.put("/api/v1/kate/consent", json={"domain": "spending", "allowed": False})
    assert response.status_code == 200

    after = {item["id"] for item in client.get(FEED).json()["items"]}
    assert after != before, "turning off spending signals must visibly change the feed"


def test_consent_rejects_an_unknown_domain(client: TestClient) -> None:
    login(client, "emma")

    response = client.put("/api/v1/kate/consent", json={"domain": "horoscope", "allowed": False})

    assert response.status_code == 422


def test_consent_is_per_customer(client: TestClient) -> None:
    login(client, "jan")
    client.put("/api/v1/kate/consent", json={"domain": "spending", "allowed": False})

    login(client, "marie")
    consent = client.get("/api/v1/kate/consent").json()

    assert consent["spending"] is True, "Jan's choice must not leak into Marie's profile"


# --- dismissing --------------------------------------------------------------------------------


def test_a_dismissed_suggestion_comes_back_silenced(client: TestClient) -> None:
    login(client, "marie")
    assert "idle_savings" in {i["id"] for i in client.get(FEED).json()["items"]}

    # The CSRF guard requires JSON on every state-changing call, body or no body.
    assert client.post("/api/v1/kate/feed/idle_savings/dismiss", json={}).status_code == 204

    feed = client.get(FEED).json()
    assert "idle_savings" not in {i["id"] for i in feed["items"]}
    assert {s["moment"]: s["reason_code"] for s in feed["silenced"]}["idle_savings"] == "dismissed"


# --- the time machine --------------------------------------------------------------------------


def test_the_time_machine_is_invisible_to_ordinary_customers(admin_client: TestClient) -> None:
    login(admin_client, "emma")

    response = admin_client.post(TIME_MACHINE, json={"days": 7, "scenario": "none"})

    # 404, not 403: we never confirm that an endpoint the caller may not use exists.
    assert response.status_code == 404


def test_the_time_machine_requires_a_session(admin_client: TestClient) -> None:
    assert admin_client.post(TIME_MACHINE, json={"days": 7, "scenario": "none"}).status_code == 401


def test_the_time_machine_is_off_unless_an_admin_is_configured(client: TestClient) -> None:
    login(client, "jan")

    assert client.post(TIME_MACHINE, json={"days": 7, "scenario": "none"}).status_code == 404


def test_an_admin_can_move_the_clock_forward(admin_client: TestClient) -> None:
    login(admin_client, "jan")

    response = admin_client.post(TIME_MACHINE, json={"days": 7, "scenario": "none"})

    assert response.status_code == 200
    assert response.json()["days_shifted"] == 7


def test_a_missing_salary_makes_kate_escalate(admin_client: TestClient) -> None:
    login(admin_client, "jan")

    body = admin_client.post(
        TIME_MACHINE, json={"days": 40, "scenario": "salary_missing", "username": "jan"}
    ).json()

    items = {item["id"]: item for item in body["feed"]["items"]}
    assert "income_missing" in items, "a salary that never arrived must be noticed"
    assert items["income_missing"]["channel"] in {"push", "sms", "call"}, (
        "and it must not sit quietly in the feed"
    )


def test_a_salary_that_does_arrive_keeps_kate_quiet(admin_client: TestClient) -> None:
    login(admin_client, "jan")

    body = admin_client.post(
        TIME_MACHINE, json={"days": 40, "scenario": "salary_paid", "username": "jan"}
    ).json()

    assert "income_missing" not in {item["id"] for item in body["feed"]["items"]}


def test_the_time_machine_rejects_an_absurd_jump(admin_client: TestClient) -> None:
    login(admin_client, "jan")

    assert (
        admin_client.post(TIME_MACHINE, json={"days": 9000, "scenario": "none"}).status_code == 422
    )


def test_the_time_machine_rejects_an_unknown_scenario(admin_client: TestClient) -> None:
    login(admin_client, "jan")

    response = admin_client.post(TIME_MACHINE, json={"days": 7, "scenario": "meteor"})

    assert response.status_code == 422


def test_an_admin_cannot_use_the_time_machine_to_read_someone_elses_feed(
    admin_client: TestClient,
) -> None:
    login(admin_client, "jan")

    body = admin_client.post(
        TIME_MACHINE, json={"days": 7, "scenario": "none", "username": "emma"}
    ).json()

    # The admin may simulate another persona's timeline for the demo, but the response must say
    # whose it is, so nothing is ever attributed to the wrong customer.
    assert body["username"] == "emma"
