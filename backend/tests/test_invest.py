from decimal import Decimal
from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import login

API = "/api/v1/invest"
NEUTRAL = {"goal": "grow", "horizon": "5to10", "knowledge": "basic", "drop_reaction": "wait"}
CORE_MIX = {"etf_world": 60, "etf_aggbond": 40}


def _answer(client: TestClient, answers: dict[str, str] = NEUTRAL) -> dict[str, Any]:
    response = client.post(f"{API}/answers", json=answers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _shift(client: TestClient, days: int) -> None:
    client.app.state.kate.time_offset_days += days  # type: ignore[attr-defined]


def _savings(client: TestClient, account_id: str) -> Decimal:
    return Decimal(client.get(f"/api/v1/accounts/{account_id}").json()["balance"])


def test_requires_login(client: TestClient) -> None:
    assert client.get(API).status_code == 401
    assert client.post(f"{API}/answers", json=NEUTRAL).status_code == 401


def test_health_check_is_honest_about_the_buffer(client: TestClient) -> None:
    login(client, "emma")  # € 250 savings: build a buffer first
    health = client.get(API).json()["health"]
    assert health["status"] == "build_buffer"
    assert Decimal(health["investable"]) == 0
    assert "buffer" in health["notes"][0].lower()

    login(client, "jan")
    health = client.get(API).json()["health"]
    assert health["status"] == "ready"
    assert Decimal(health["buffer"]) >= Decimal("2000")
    assert Decimal(health["investable"]) == Decimal(health["savings"]) - Decimal(health["buffer"])


def test_profile_points_a_direction_with_caps(client: TestClient) -> None:
    login(client, "jan")
    assert _answer(client)["direction"]["profile"] == "neutral"
    bold = _answer(client, {**NEUTRAL, "horizon": "gt10", "drop_reaction": "buy_more"})
    assert bold["direction"]["profile"] == "dynamic"
    assert bold["direction"]["shares_percent"] == 90
    # A purchase soon caps the direction, however brave the answers.
    soon = _answer(
        client, {**NEUTRAL, "goal": "purchase", "horizon": "lt3", "drop_reaction": "buy_more"}
    )
    assert soon["direction"]["profile"] == "defensive"
    assert soon["direction"]["suitable"] is False
    assert any("3 jaar" in w for w in soon["direction"]["warnings"])


def test_catalog_marks_fit_and_blocks_complex_without_knowledge(client: TestClient) -> None:
    login(client, "jan")
    body = _answer(client, {**NEUTRAL, "knowledge": "none"})
    by_id = {e["id"]: e for e in body["catalog"]}
    assert by_id["etf_world"]["fit"] == "fits"
    assert by_id["etf_em"]["fit"] == "addition"
    assert by_id["etf_clean"]["fit"] == "caution"
    assert by_id["etf_lev"]["allowed"] is False
    assert all(e["name"].startswith("Demo") for e in body["catalog"])  # never a real product
    assert body["simulated"] is True


def test_mix_check_warns_but_the_choice_stays_yours(client: TestClient) -> None:
    login(client, "jan")
    _answer(client)
    good = client.post(f"{API}/check", json={"weights": CORE_MIX}).json()
    assert good["warnings"] == [] and good["blocked"] == []
    assert good["shares_percent"] == 60

    risky = client.post(f"{API}/check", json={"weights": {"etf_clean": 100}}).json()
    assert risky["needs_acknowledgement"] is True
    assert any("sector" in w for w in risky["warnings"])
    assert any("basis" in w for w in risky["warnings"])

    # Without acknowledging, no plan; with it, the customer's own choice goes through.
    plan = {"weights": {"etf_clean": 100}, "total": "1200.00", "months": 12}
    assert client.post(f"{API}/plan", json=plan).status_code == 422
    accepted = client.post(f"{API}/plan", json={**plan, "accept_risks": True})
    assert accepted.status_code == 201


def test_bad_mixes_are_refused(client: TestClient) -> None:
    login(client, "jan")
    _answer(client, {**NEUTRAL, "knowledge": "none"})
    not_100 = client.post(f"{API}/check", json={"weights": {"etf_world": 50}}).json()
    assert not_100["blocked"]
    lev = client.post(f"{API}/check", json={"weights": {"etf_lev": 100}}).json()
    assert lev["blocked"]
    plan = {"weights": {"etf_lev": 100}, "total": "600.00", "months": 6, "accept_risks": True}
    assert client.post(f"{API}/plan", json=plan).status_code == 422
    bad_id = client.post(f"{API}/check", json={"weights": {"../etc": 100}})
    assert bad_id.status_code == 422


def test_plan_needs_answers_first(client: TestClient) -> None:
    login(client, "jan")
    plan = {"weights": CORE_MIX, "total": "1200.00", "months": 12}
    response = client.post(f"{API}/plan", json=plan)
    assert response.status_code == 422
    assert "vragen" in response.json()["detail"]


def test_buffer_can_never_be_invested(client: TestClient) -> None:
    login(client, "jan")
    _answer(client)
    health = client.get(API).json()["health"]
    too_much = Decimal(health["investable"]) + 1
    plan = {"weights": CORE_MIX, "total": f"{too_much:.2f}", "months": 6}
    response = client.post(f"{API}/plan", json=plan)
    assert response.status_code == 422
    assert "buffer" in response.json()["detail"]


def test_plan_runs_steps_by_itself_and_reports_them(client: TestClient) -> None:
    login(client, "jan")
    _answer(client)
    before = _savings(client, "a_jan_2")
    body = client.post(
        f"{API}/plan", json={"weights": CORE_MIX, "total": "3000.00", "months": 3}
    ).json()
    plan = body["plan"]
    assert plan["status"] == "active"
    assert len(plan["steps"]) == 1  # the first step right away
    assert plan["steps"][0]["amount"] == "1000.00"
    assert plan["steps"][0]["tax"] == "1.20"  # beurstaks 0,12%
    assert _savings(client, "a_jan_2") == before - 1000
    assert {h["etf_id"] for h in body["portfolio"]["holdings"]} == set(CORE_MIX)

    inbox = client.get("/api/v1/kate/notifications").json()
    assert any(n["title"] == "Stap 1 van 3 uitgevoerd" for n in inbox["items"])

    _shift(client, 62)  # two months later: Kate did steps 2 and 3 and finished
    body = client.get(API).json()
    assert body["plan"]["status"] == "completed"
    assert body["plan"]["invested"] == "3000.00"
    assert _savings(client, "a_jan_2") == before - 3000
    titles = [n["title"] for n in client.get("/api/v1/kate/notifications").json()["items"]]
    assert "Stap 3 van 3 uitgevoerd" in titles
    assert "Je beleggingsplan is afgerond" in titles
    assert titles.count("Stap 2 van 3 uitgevoerd") == 1  # reported exactly once


def test_pause_resume_and_stop(client: TestClient) -> None:
    login(client, "jan")
    _answer(client)
    client.post(f"{API}/plan", json={"weights": CORE_MIX, "total": "1200.00", "months": 12})
    assert client.post(f"{API}/plan/pause", json={}).json()["plan"]["status"] == "paused"
    _shift(client, 90)
    assert len(client.get(API).json()["plan"]["steps"]) == 1  # nothing while paused
    resumed = client.post(f"{API}/plan/resume", json={}).json()["plan"]
    assert len(resumed["steps"]) == 2  # carries on from today, no catch-up of missed months
    stopped = client.post(f"{API}/plan/stop", json={}).json()
    assert stopped["plan"]["status"] == "stopped"
    assert stopped["portfolio"]["holdings"]  # what was invested stays yours
    assert client.post(f"{API}/plan/resume", json={}).status_code == 409
    assert client.post(f"{API}/plan/explode", json={}).status_code == 422


def test_plan_pauses_instead_of_touching_the_buffer(client: TestClient) -> None:
    login(client, "jan")
    _answer(client)
    health = client.get(API).json()["health"]
    investable = Decimal(health["investable"])
    client.post(
        f"{API}/plan",
        json={"weights": CORE_MIX, "total": f"{investable:.2f}", "months": 2},
    )
    # Jan spends from savings in the meantime: the next step would dig into the buffer.
    client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": "a_jan_2",
            "to_iban": "BE68539007547034",
            "to_name": "Aannemer",
            "amount": "1000.00",
        },
    )
    _shift(client, 31)
    body = client.get(API).json()
    assert body["plan"]["status"] == "paused"
    assert "buffer" in body["plan"]["pause_reason"]
    assert Decimal(body["health"]["savings"]) >= Decimal(body["plan"]["buffer"])
    push = [
        n
        for n in client.get("/api/v1/kate/notifications").json()["items"]
        if n["channel"] == "push"
    ]
    assert any("pauze" in n["title"] for n in push)


def test_each_customer_only_sees_their_own(client: TestClient) -> None:
    login(client, "jan")
    _answer(client)
    client.post(f"{API}/plan", json={"weights": CORE_MIX, "total": "1200.00", "months": 12})
    login(client, "marie")
    body = client.get(API).json()
    assert body["plan"] is None and body["answers"] is None
    assert body["portfolio"]["holdings"] == []
    assert client.post(f"{API}/plan/stop", json={}).status_code == 409


def test_kate_chat_talks_about_investing_but_never_picks_a_product(client: TestClient) -> None:
    login(client, "jan")
    body = client.post(
        "/api/v1/kate/chat", json={"message": "Ik wil beginnen met beleggen in ETF's"}
    ).json()
    assert body["action"]["type"] == "invest_guide"
    assert "jij kiest" in body["reply"].lower()
    assert "buffer" in body["reply"].lower()
