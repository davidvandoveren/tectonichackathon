"""Feed cards (Moments Engine) -> confirmable Kate Skills proposals."""

from fastapi.testclient import TestClient

from tests.conftest import login


def feed_ids(client: TestClient) -> set[str]:
    return {item["id"] for item in client.get("/api/v1/kate/feed").json()["items"]}


def test_feed_actions_need_login(client: TestClient) -> None:
    assert client.get("/api/v1/skills/feed-actions").status_code == 401
    response = client.post("/api/v1/proposals/from-moment", json={"moment": "first_salary"})
    assert response.status_code == 401


def test_every_feed_action_belongs_to_a_card_in_the_feed(emma: TestClient) -> None:
    actions = emma.get("/api/v1/skills/feed-actions").json()
    assert actions, "Emma's feed should offer at least one action"
    assert {a["moment"] for a in actions} <= feed_ids(emma)
    salary = next(a for a in actions if a["moment"] == "first_salary")
    assert salary["action"] == "savings.create_goal"
    assert salary["level"] == "prepare"
    assert salary["can_confirm"] is True
    assert salary["summary"].startswith("Spaardoel 'Buffer' van €")


def test_each_card_gets_at_most_one_action(client: TestClient) -> None:
    for username in ("emma", "jan", "marie"):
        login(client, username)
        moments = [a["moment"] for a in client.get("/api/v1/skills/feed-actions").json()]
        assert len(moments) == len(set(moments))
        assert set(moments) <= feed_ids(client)
        client.post("/api/v1/auth/logout", json={})


def test_consent_off_or_suggest_means_no_confirm_button(emma: TestClient) -> None:
    emma.put("/api/v1/skills/consent/savings.create_goal", json={"level": "suggest"})
    salary = next(
        a for a in emma.get("/api/v1/skills/feed-actions").json() if a["moment"] == "first_salary"
    )
    assert salary["can_confirm"] is False
    emma.put("/api/v1/skills/consent/savings.create_goal", json={"level": "off"})
    moments = {a["moment"] for a in emma.get("/api/v1/skills/feed-actions").json()}
    assert "first_salary" not in moments


def test_confirming_a_card_uses_the_servers_own_numbers(emma: TestClient) -> None:
    expected = next(
        a for a in emma.get("/api/v1/skills/feed-actions").json() if a["moment"] == "first_salary"
    )
    created = emma.post("/api/v1/proposals/from-moment", json={"moment": "first_salary"})
    assert created.status_code == 201, created.text
    proposal = created.json()
    assert proposal["source"] == "moment"
    assert proposal["action"] == "savings.create_goal"
    assert proposal["summary"] == expected["summary"]
    assert "Proximus" in proposal["reason"]  # the engine's own evidence, not client text

    done = emma.post(f"/api/v1/proposals/{proposal['id']}/approve", json={}).json()
    assert done["status"] == "executed"
    assert "Buffer" in done["outcome"]["message"]


def test_client_cannot_invent_a_moment_or_smuggle_params(emma: TestClient) -> None:
    assert (
        emma.post("/api/v1/proposals/from-moment", json={"moment": "idle_savings"}).status_code
        == 404
    )  # real moment type, but not in Emma's feed
    assert emma.post("/api/v1/proposals/from-moment", json={"moment": "casino"}).status_code == 404
    smuggled = emma.post(
        "/api/v1/proposals/from-moment",
        json={"moment": "first_salary", "params": {"target": "1.00"}},
    )
    assert smuggled.status_code == 422


def test_regulated_card_becomes_an_advisor_handoff(client: TestClient) -> None:
    login(client, "jan")
    proposal = client.post("/api/v1/proposals/from-moment", json={"moment": "moving_house"}).json()
    done = client.post(f"/api/v1/proposals/{proposal['id']}/approve", json={}).json()
    assert done["outcome"]["kind"] == "advisor_handoff"


def test_consent_off_blocks_confirming(emma: TestClient) -> None:
    emma.put("/api/v1/skills/consent/savings.create_goal", json={"level": "off"})
    response = emma.post("/api/v1/proposals/from-moment", json={"moment": "first_salary"})
    assert response.status_code == 403
