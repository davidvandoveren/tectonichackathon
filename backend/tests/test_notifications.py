from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import login

API = "/api/v1/kate/notifications"


def _inbox(client: TestClient) -> dict[str, Any]:
    response = client.get(API)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_requires_login(client: TestClient) -> None:
    assert client.get(API).status_code == 401


def test_kate_sends_what_the_engine_decided_once(client: TestClient) -> None:
    login(client, "jan")
    first = _inbox(client)
    sources = {n["source"] for n in first["items"]}
    assert "moment" in sources  # the moments engine's decisions arrive by themselves
    assert "family" in sources  # "Noor wordt over 21 dagen 18"
    assert first["unread"] == len(first["items"])
    assert all(n["reason"] for n in first["items"])  # every message says why
    again = _inbox(client)
    assert len(again["items"]) == len(first["items"])  # no duplicates within the cool-down


def test_background_sweep_reaches_everyone(client: TestClient) -> None:
    sent = client.app.state.dispatcher.sweep()  # type: ignore[attr-defined]
    assert sent > 0
    login(client, "marie")
    assert _inbox(client)["items"]


def test_invest_nudge_only_for_healthy_finances_and_with_consent(client: TestClient) -> None:
    login(client, "marie")  # large savings above her buffer
    assert any(n["source"] == "invest" for n in _inbox(client)["items"])
    login(client, "emma")  # no buffer yet: no nudge to invest
    assert not any(n["source"] == "invest" for n in _inbox(client)["items"])
    login(client, "noor")  # a minor: never
    assert not any(n["source"] == "invest" for n in _inbox(client)["items"])


def test_no_invest_nudge_without_balances_consent(client: TestClient) -> None:
    login(client, "jan")
    client.put("/api/v1/kate/consent", json={"domain": "balances", "allowed": False})
    assert not any(n["source"] == "invest" for n in _inbox(client)["items"])


def test_interruptions_spend_the_engine_quota(client: TestClient) -> None:
    state = client.app.state.kate  # type: ignore[attr-defined]
    client.app.state.dispatcher.sweep()  # type: ignore[attr-defined]
    for user in client.app.state.bank.list_users():  # type: ignore[attr-defined]
        pushes = [
            n
            for n in client.app.state.notifications.for_user(user.id)  # type: ignore[attr-defined]
            if n.source == "moment" and n.channel in ("push", "sms", "call")
        ]
        if pushes:
            assert state.last_interruption_for(user.id) is not None


def test_mark_read_is_scoped_to_your_own_inbox(client: TestClient) -> None:
    login(client, "jan")
    jans = _inbox(client)["items"][0]["id"]
    login(client, "marie")
    assert client.post(f"{API}/{jans}/read", json={}).status_code == 404
    login(client, "jan")
    read = client.post(f"{API}/{jans}/read", json={})
    assert read.status_code == 200 and read.json()["read"] is True
    assert client.post(f"{API}/read-all", json={}).status_code == 204
    assert _inbox(client)["unread"] == 0
    assert client.post(f"{API}/not-an-id/read", json={}).status_code == 422
