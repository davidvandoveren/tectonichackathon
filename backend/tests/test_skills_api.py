from fastapi.testclient import TestClient

from tests.conftest import login

WHY = "Je zet al maanden met de hand geld opzij."


def propose(client: TestClient, action: str, params: dict[str, object]) -> dict[str, object]:
    response = client.post(
        "/api/v1/proposals",
        json={"action": action, "params": params, "source": "moment", "reason": WHY},
    )
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def test_skills_need_login(client: TestClient) -> None:
    assert client.get("/api/v1/skills").status_code == 401
    assert client.get("/api/v1/proposals").status_code == 401
    assert client.get("/api/v1/activity").status_code == 401


def test_catalogue_lists_kbc_domains_with_consent(emma: TestClient) -> None:
    skills = emma.get("/api/v1/skills").json()
    ids = {s["id"] for s in skills}
    assert {"payments", "savings", "cards", "deals", "loans", "investing"} <= ids
    transfer = next(a for s in skills for a in s["actions"] if a["id"] == "payments.transfer")
    assert transfer["risk"] == "external_money"
    assert transfer["level"] == "prepare"
    assert transfer["max_level"] == "prepare"


def test_propose_approve_flow_with_money_as_strings(emma: TestClient) -> None:
    proposal = propose(emma, "savings.move_to_savings", {"amount": "25"})
    assert proposal["status"] == "pending"
    assert proposal["params"] == {"amount": "25.00"}
    done = emma.post(f"/api/v1/proposals/{proposal['id']}/approve", json={}).json()
    assert done["status"] == "executed"
    assert done["outcome"]["kind"] == "done"
    assert emma.post(f"/api/v1/proposals/{proposal['id']}/approve", json={}).status_code == 409
    events = [e["event"] for e in emma.get("/api/v1/activity").json()]
    assert events[:2] == ["executed", "proposed"]


def test_other_customers_proposal_is_404(client: TestClient) -> None:
    login(client, "emma")
    proposal = propose(client, "savings.move_to_savings", {"amount": "25.00"})
    client.post("/api/v1/auth/logout")
    login(client, "jan")
    assert client.post(f"/api/v1/proposals/{proposal['id']}/approve", json={}).status_code == 404
    assert client.post(f"/api/v1/proposals/{proposal['id']}/decline", json={}).status_code == 404
    assert client.get("/api/v1/proposals").json() == []


def test_consent_off_blocks_proposals(emma: TestClient) -> None:
    response = emma.put("/api/v1/skills/consent/cards.add_package", json={"level": "off"})
    assert response.status_code == 200
    assert response.json()["level"] == "off"
    refused = emma.post(
        "/api/v1/proposals",
        json={
            "action": "cards.add_package",
            "params": {"package": "reis"},
            "source": "chat",
            "reason": WHY,
        },
    )
    assert refused.status_code == 403


def test_consent_cannot_exceed_ceiling_or_mandate_limits(emma: TestClient) -> None:
    too_high = emma.put("/api/v1/skills/consent/payments.transfer", json={"level": "auto"})
    assert too_high.status_code == 422
    no_mandate = emma.put("/api/v1/skills/consent/savings.move_to_savings", json={"level": "auto"})
    assert no_mandate.status_code == 422
    huge = emma.put(
        "/api/v1/skills/consent/savings.move_to_savings",
        json={
            "level": "auto",
            "mandate": {"max_per_execution": "900.00", "max_per_month": "900.00"},
        },
    )
    assert huge.status_code == 422
    unknown = emma.put("/api/v1/skills/consent/casino.bet", json={"level": "off"})
    assert unknown.status_code == 404


def test_auto_with_mandate_executes_and_reports(emma: TestClient) -> None:
    ok = emma.put(
        "/api/v1/skills/consent/savings.move_to_savings",
        json={
            "level": "auto",
            "mandate": {"max_per_execution": "50.00", "max_per_month": "100.00"},
        },
    )
    assert ok.status_code == 200
    assert ok.json()["mandate"] == {"max_per_execution": "50.00", "max_per_month": "100.00"}
    assert propose(emma, "savings.move_to_savings", {"amount": "40.00"})["status"] == "executed"
    assert propose(emma, "savings.move_to_savings", {"amount": "80.00"})["status"] == "pending"


def test_bad_input(emma: TestClient) -> None:
    def post(body: dict[str, object]) -> int:
        return emma.post("/api/v1/proposals", json=body).status_code

    assert post({"action": "casino.bet", "params": {}, "source": "chat", "reason": WHY}) == 404
    base = {"action": "savings.move_to_savings", "source": "chat", "reason": WHY}
    assert post({**base, "params": {"amount": "-1"}}) == 422
    assert post({**base, "params": {"amount": "5.00", "extra": "x"}}) == 422
    assert post({**base, "params": {"amount": "999999.00"}}) == 422
    assert post({**base, "params": {"amount": "5.00"}, "source": "hacker"}) == 422
    assert post({**base, "params": {"amount": "5.00"}, "reason": ""}) == 422
    assert post({**base, "params": {"amount": "5.00"}, "reason": "   "}) == 422
    assert post({**base, "params": {"amount": "9999.00"}}) == 409  # more than Emma has


def test_decline_and_filter(emma: TestClient) -> None:
    proposal = propose(emma, "deals.activate", {"category": "fuel"})
    assert (
        emma.post(f"/api/v1/proposals/{proposal['id']}/decline", json={}).json()["status"]
        == "declined"
    )
    assert emma.get("/api/v1/proposals?status=pending").json() == []
    assert len(emma.get("/api/v1/proposals?status=declined").json()) == 1
