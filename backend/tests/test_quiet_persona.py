"""Tom is the control case: a healthy customer with nothing going on gets no message at all."""

from fastapi.testclient import TestClient

from tests.conftest import login


def test_tom_gets_no_kate_message_anywhere(client: TestClient) -> None:
    login(client, "tom")
    feed = client.get("/api/v1/kate/feed").json()
    assert feed == {"items": [], "silenced": []}
    assert client.get("/api/v1/insights").json() == []
    assert client.get("/api/v1/skills/feed-actions").json() == []
    assert client.get("/api/v1/subscriptions").json()["subscriptions"] == []


def test_tom_is_not_in_anyones_family_circle(client: TestClient) -> None:
    login(client, "tom")
    body = client.get("/api/v1/family").json()
    assert not body.get("links")
    assert not body.get("suggestions")
