"""Kate's chat proposes through Kate Skills (one proposal system)."""

from fastapi.testclient import TestClient

from tests.conftest import login

CHAT = "/api/v1/kate/chat"
PIZZA = {"message": "Stuur Lucas 25 euro voor de pizza"}


def test_chat_transfer_is_a_skills_proposal_in_the_activity_log(emma: TestClient) -> None:
    action = emma.post(CHAT, json=PIZZA).json()["action"]
    assert action["proposal_status"] == "pending"

    proposals = {p["id"]: p for p in emma.get("/api/v1/proposals").json()}
    proposal = proposals[action["proposal_id"]]
    assert proposal["action"] == "payments.transfer" and proposal["source"] == "chat"
    assert "Stuur Lucas 25 euro" in proposal["reason"]
    assert any(e["source"] == "chat" for e in emma.get("/api/v1/activity").json())


def test_confirm_only_prefills_the_transfer_screen(emma: TestClient) -> None:
    proposal_id = emma.post(CHAT, json=PIZZA).json()["action"]["proposal_id"]
    before = emma.get("/api/v1/accounts").json()
    outcome = emma.post(f"/api/v1/proposals/{proposal_id}/approve", json={}).json()["outcome"]
    assert outcome["kind"] == "navigate"
    assert outcome["navigate_to"].startswith("/transfer?")
    assert emma.get("/api/v1/accounts").json() == before  # Kate moved no money


def test_switched_off_action_gives_no_card(emma: TestClient) -> None:
    response = emma.put("/api/v1/skills/consent/payments.transfer", json={"level": "off"})
    assert response.status_code == 200, response.text
    body = emma.post(CHAT, json=PIZZA).json()
    assert body["action"]["type"] == "none"
    assert "niet voor je klaarzetten" in body["reply"]


def test_other_customer_cannot_confirm_my_chat_proposal(client: TestClient) -> None:
    login(client, "emma")
    proposal_id = client.post(CHAT, json=PIZZA).json()["action"]["proposal_id"]
    login(client, "jan")
    assert client.post(f"/api/v1/proposals/{proposal_id}/approve", json={}).status_code == 404


def test_advisor_handoff_is_a_skills_proposal(emma: TestClient) -> None:
    history = [
        {"role": "user", "text": "mijn moeder is overleden"},
        {
            "role": "kate",
            "text": "Als je wil, kan ik je helpen met wat er financieel geregeld "
            "moet worden. Zal ik dat rustig met je overlopen?",
        },
    ]
    action = emma.post(CHAT, json={"message": "ja graag", "history": history}).json()["action"]
    assert action["type"] == "advisor_handoff" and action["proposal_id"]
    proposal = next(
        p for p in emma.get("/api/v1/proposals").json() if p["id"] == action["proposal_id"]
    )
    assert proposal["action"] == "advisor.book_call"
