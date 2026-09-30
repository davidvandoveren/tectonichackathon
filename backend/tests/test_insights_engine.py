"""`GET /insights` ("Voor jou" on home) is fed by the moments engine.

The shape the frontend already uses must not change; the engine only adds optional fields and
makes the carousel obey the same ranking, consent and dismissals as `GET /kate/feed`.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import DEMO_PASSWORD, login

INSIGHTS = "/api/v1/insights"
FEED = "/api/v1/kate/feed"

LEGACY_FIELDS = {"id", "kind", "title", "body", "cta_label", "cta_target", "reason"}
ENGINE_FIELDS = {"moment", "urgency", "channel", "confidence"}


@pytest.fixture
def admin_client() -> Iterator[TestClient]:
    settings = Settings(
        app_env="test",
        demo_password=DEMO_PASSWORD,  # type: ignore[arg-type]
        cookie_secure=False,
        admin_usernames="jan",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def by_moment(insights: list[dict[str, object]]) -> dict[object, dict[str, object]]:
    return {insight["moment"]: insight for insight in insights}


def test_the_frontend_shape_is_kept_and_only_extended(client: TestClient) -> None:
    login(client, "emma")

    insights = client.get(INSIGHTS).json()

    assert insights
    for insight in insights:
        assert set(insight) == LEGACY_FIELDS | ENGINE_FIELDS
        assert insight["reason"]
        assert 0 <= insight["urgency"] <= 100
        assert insight["channel"] in {"feed", "push", "sms", "call", "none"}
        assert 0 <= insight["confidence"] <= 1


def test_the_old_insight_ids_still_exist(client: TestClient) -> None:
    expected = {
        "emma": "i_first_salary_u_emma",
        "jan": "i_moving_u_jan",
        "marie": "i_idle_savings_u_marie",
    }
    for username, insight_id in expected.items():
        login(client, username)
        assert insight_id in {i["id"] for i in client.get(INSIGHTS).json()}


def test_home_shows_what_kate_says_in_the_same_order(client: TestClient) -> None:
    for username in ("emma", "jan", "marie"):
        login(client, username)

        feed = [item["id"] for item in client.get(FEED).json()["items"]]
        insights = [insight["moment"] for insight in client.get(INSIGHTS).json()]

        assert insights == feed


def test_switching_off_a_domain_also_empties_it_on_home(client: TestClient) -> None:
    login(client, "emma")
    assert "first_salary" in by_moment(client.get(INSIGHTS).json())

    client.put("/api/v1/kate/consent", json={"domain": "income", "allowed": False})

    assert "first_salary" not in by_moment(client.get(INSIGHTS).json())


def test_a_dismissed_suggestion_leaves_home_too(client: TestClient) -> None:
    login(client, "marie")
    assert "idle_savings" in by_moment(client.get(INSIGHTS).json())

    assert client.post("/api/v1/kate/feed/idle_savings/dismiss", json={}).status_code == 204

    assert "idle_savings" not in by_moment(client.get(INSIGHTS).json())


def test_a_missing_salary_reaches_home_as_an_alert_on_top(admin_client: TestClient) -> None:
    login(admin_client, "jan")
    admin_client.post(
        "/api/v1/admin/time-machine",
        json={"days": 40, "scenario": "salary_missing", "username": "jan"},
    )

    insights = admin_client.get(INSIGHTS).json()

    top = insights[0]
    assert top["moment"] == "income_missing"
    assert top["kind"] == "alert"
    assert top["channel"] in {"push", "sms", "call"}


def test_insights_are_private(client: TestClient) -> None:
    assert client.get(INSIGHTS).status_code == 401
