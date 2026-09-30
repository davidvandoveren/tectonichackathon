from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.population.dashboard import summarise
from app.population.generator import MIX, generate
from tests.conftest import DEMO_PASSWORD, login

DASHBOARD = "/api/v1/admin/dashboard"


def _client(admin_usernames: str) -> TestClient:
    settings = Settings(
        app_env="test",
        demo_password=DEMO_PASSWORD,  # type: ignore[arg-type]
        cookie_secure=False,
        admin_usernames=admin_usernames,
    )
    return TestClient(create_app(settings))


@pytest.fixture
def admin() -> Iterator[TestClient]:
    with _client("jan") as client:
        login(client, "jan")
        yield client


def test_dashboard_is_invisible_to_customers() -> None:
    with _client("jan") as client:
        assert client.get(DASHBOARD).status_code == 401
        login(client, "emma")
        assert client.get(DASHBOARD).status_code == 404  # not even revealed to exist


def test_dashboard_is_off_without_admins() -> None:
    with _client("") as client:
        login(client, "jan")
        assert client.get(DASHBOARD).status_code == 404


def test_dashboard_counts_everyone_once(admin: TestClient) -> None:
    body = admin.get(DASHBOARD, params={"size": 300}).json()
    population = body["population"]
    assert population["size"] == 300
    assert population["with_message"] + population["silent"] == 300
    assert population["silent"] == population["nothing_at_all"] + population["held_back"]
    assert population["interrupted"] <= population["with_message"]
    assert sum(row["customers"] for row in population["archetypes"]) == 300
    assert list(population["by_channel"])[:4] == ["feed", "push", "sms", "call"]
    assert population["silent"] > 0  # deliberate silence is part of the answer
    assert population["full_bank_cpu_minutes"] > 0


def test_dashboard_traces_demo_personas(admin: TestClient) -> None:
    personas = {
        p["username"]: p for p in admin.get(DASHBOARD, params={"size": 100}).json()["personas"]
    }
    assert {"emma", "jan", "marie"} <= set(personas)
    jan = personas["jan"]
    assert jan["signals"] and all(s["evidence"] for s in jan["signals"])
    for action in jan["actions"]:
        assert action["reason"] and action["channel"] in {"feed", "push", "sms", "call"}


def test_dashboard_size_is_bounded(admin: TestClient) -> None:
    assert admin.get(DASHBOARD, params={"size": 10}).status_code == 422
    assert admin.get(DASHBOARD, params={"size": 1_000_000}).status_code == 422


def test_population_is_reproducible_and_synthetic() -> None:
    today = date(2026, 9, 30)
    first = [
        (c.archetype, len(c.bank.all_transactions_for(c.user.id))) for c in generate(50, today)
    ]
    again = [
        (c.archetype, len(c.bank.all_transactions_for(c.user.id))) for c in generate(50, today)
    ]
    assert first == again
    assert all(c.user.first_name == "Klant" for c in generate(20, today))


def test_real_engine_finds_the_archetypes_moments() -> None:
    summary = summarise(1500, date(2026, 9, 30))
    assert abs(sum(weight for _, weight, _ in MIX) - 1) < 1e-9
    for moment in (
        "income_missing",
        "first_salary",
        "moving_house",
        "idle_savings",
        "savings_habit_automatable",
        "cashflow_risk",
    ):
        assert summary.by_moment[moment] > 0, moment
    assert summary.silence_reasons  # and it explains why it stayed quiet
