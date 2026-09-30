from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import login

API = "/api/v1/family"


def _overview(client: TestClient) -> dict[str, Any]:
    response = client.get(API)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _link_with(client: TestClient, name: str) -> dict[str, Any]:
    return next(link for link in _overview(client)["links"] if link["other_name"].startswith(name))


def _wedding_pot(client: TestClient) -> dict[str, Any]:
    return next(p for p in _overview(client)["pots"] if p["name"] == "Ons trouwfeest")


def _shift_clock(client: TestClient, days: int) -> None:
    client.app.state.kate.time_offset_days = days  # type: ignore[attr-defined]


def test_requires_login(client: TestClient) -> None:
    assert client.get(API).status_code == 401
    assert client.post(
        f"{API}/invites", json={"username": "x", "my_role": "other"}
    ).status_code in (
        401,
        403,
    )


def test_new_family_personas_can_log_in(client: TestClient) -> None:
    names = {u["username"] for u in client.get("/api/v1/auth/demo-users").json()}
    assert {"emma", "jan", "marie", "lucas", "noor"} <= names
    login(client, "noor")
    assert client.get("/api/v1/accounts").status_code == 200


def test_emma_sees_her_circle_and_owns_the_wedding_pot(emma: TestClient) -> None:
    body = _overview(emma)
    others = {link["other_name"]: link for link in body["links"]}
    assert set(others) == {"Lucas Janssens", "Marie Dubois"}
    assert others["Lucas Janssens"]["my_role"] == "partner"
    assert others["Marie Dubois"]["their_role"] == "grandparent"
    assert others["Marie Dubois"]["i_share"] == "gift"
    pot = _wedding_pot(emma)
    assert pot["mine"] and pot["access"] == "owner"
    assert pot["balance"] == "2500.00" and pot["goal"] == "8000.00"
    assert pot["progress_percent"] == 31
    assert pot["members"] == ["Lucas Janssens", "Marie Dubois"]
    assert len(pot["contributions"]) == 4


def test_gift_level_sees_progress_but_not_who_gave_what(client: TestClient) -> None:
    login(client, "marie")
    pot = _wedding_pot(client)
    assert pot["access"] == "gift"
    assert pot["balance"] == "2500.00"
    assert pot["members"] is None
    assert pot["contributions"] == []
    # And Marie cannot see Emma's accounts: Emma only shares "gift".
    link = _link_with(client, "Emma")
    assert link["can_view_accounts"] is False
    assert client.get(f"{API}/links/{link['id']}/accounts").status_code == 404
    kinds = {s["kind"] for s in _overview(client)["suggestions"]}
    assert "pot_contribution" in kinds


def test_pot_level_sees_contributions(client: TestClient) -> None:
    login(client, "lucas")
    pot = _wedding_pot(client)
    assert pot["access"] == "pot"
    assert len(pot["contributions"]) == 4


def test_contribution_moves_own_money_and_shows_up(client: TestClient) -> None:
    login(client, "marie")
    before = client.get("/api/v1/accounts/a_marie_1").json()["balance"]
    pot = _wedding_pot(client)
    response = client.post(
        f"{API}/pots/{pot['id']}/contributions",
        json={"from_account_id": "a_marie_1", "amount": "250.00", "note": "Van oma"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["balance"] == "2750.00"
    assert [c["amount"] for c in response.json()["contributions"]] == ["250.00"]  # only her own
    after = client.get("/api/v1/accounts/a_marie_1").json()["balance"]
    assert float(before) - float(after) == 250.0
    login(client, "emma")
    assert _wedding_pot(client)["contributions"][0]["name"] == "Marie Dubois"


def test_cannot_contribute_from_someone_elses_account(client: TestClient) -> None:
    login(client, "marie")
    pot = _wedding_pot(client)
    response = client.post(
        f"{API}/pots/{pot['id']}/contributions",
        json={"from_account_id": "a_jan_1", "amount": "10.00"},
    )
    assert response.status_code == 404


def test_contribution_respects_transfer_rules(client: TestClient) -> None:
    login(client, "lucas")
    pot = _wedding_pot(client)
    too_much = client.post(
        f"{API}/pots/{pot['id']}/contributions",
        json={"from_account_id": "a_lucas_1", "amount": "9999.00"},
    )
    assert too_much.status_code == 422
    assert "Insufficient funds" in too_much.json()["detail"]


def test_outsider_cannot_see_or_use_the_pot(client: TestClient) -> None:
    login(client, "emma")
    pot_id = _wedding_pot(client)["id"]
    login(client, "jan")
    assert all(p["id"] != pot_id for p in _overview(client)["pots"])
    response = client.post(
        f"{API}/pots/{pot_id}/contributions",
        json={"from_account_id": "a_jan_1", "amount": "10.00"},
    )
    assert response.status_code == 404
    assert "Jan" not in str(_overview(client)["pots"])


def test_links_of_others_are_404(client: TestClient) -> None:
    login(client, "emma")
    emmas_link = _link_with(client, "Lucas")["id"]
    login(client, "jan")
    assert client.post(f"{API}/links/{emmas_link}/end", json={}).status_code == 404
    assert (
        client.post(f"{API}/links/{emmas_link}/sharing", json={"share": "balances"}).status_code
        == 404
    )
    assert client.get(f"{API}/links/{emmas_link}/accounts").status_code == 404
    unknown = "fl_000000000000"
    assert client.post(f"{API}/links/{unknown}/end", json={}).status_code == 404
    assert client.post(f"{API}/links/not-an-id/end", json={}).status_code == 422  # path pattern


def test_guardian_sees_minor_balances_until_18(client: TestClient) -> None:
    login(client, "jan")
    link = _link_with(client, "Noor")
    assert link["guardianship"]["my_side"] == "guardian"
    assert link["guardianship"]["active"] is True
    assert link["they_share"] == "balances"
    accounts = client.get(f"{API}/links/{link['id']}/accounts").json()
    assert {a["name"] for a in accounts} == {"Jongerenrekening", "Spaarrekening"}
    assert all("iban" not in a for a in accounts)
    kinds = {s["kind"] for s in _overview(client)["suggestions"]}
    assert "guardianship_ending" in kinds


def test_guardianship_cannot_be_ended_early_by_either_side(client: TestClient) -> None:
    login(client, "noor")
    link = _link_with(client, "Jan")
    assert link["can_end"] is False
    assert client.post(f"{API}/links/{link['id']}/end", json={}).status_code == 409
    # Lowering her own share does not override the law yet: Jan still sees her balances.
    client.post(f"{API}/links/{link['id']}/sharing", json={"share": "exists"})
    login(client, "jan")
    assert client.get(f"{API}/links/{link['id']}/accounts").status_code == 200


def test_access_ends_automatically_at_18(client: TestClient) -> None:
    login(client, "jan")
    link_id = _link_with(client, "Noor")["id"]
    _shift_clock(client, 30)  # the time machine: Noor is now 18
    link = _link_with(client, "Noor")
    assert link["guardianship"]["active"] is False
    assert link["they_share"] == "exists"
    assert client.get(f"{API}/links/{link_id}/accounts").status_code == 404

    login(client, "noor")
    body = _overview(client)
    assert body["me"]["minor"] is False
    assert "now_adult" in {s["kind"] for s in body["suggestions"]}
    # Noor decides: she shares pot-level with her dad, not her balances.
    chosen = client.post(f"{API}/links/{link_id}/sharing", json={"share": "pot"})
    assert chosen.json()["i_share"] == "pot"
    assert "now_adult" not in {s["kind"] for s in _overview(client)["suggestions"]}
    login(client, "jan")
    assert client.get(f"{API}/links/{link_id}/accounts").status_code == 404
    # And now she may end the link, which Jan cannot block.
    login(client, "noor")
    assert client.post(f"{API}/links/{link_id}/end", json={}).status_code == 204


def test_invite_accept_and_end_flow(client: TestClient) -> None:
    login(client, "jan")
    sent = client.post(
        f"{API}/invites", json={"username": "lucas", "my_role": "other", "share": "gift"}
    )
    assert sent.status_code == 202
    link_id = sent.json()["link"]["id"]
    assert sent.json()["link"]["direction"] == "outgoing"
    # Jan cannot accept his own invite.
    assert client.post(f"{API}/links/{link_id}/accept", json={"share": "exists"}).status_code == 404

    login(client, "lucas")
    incoming = _link_with(client, "Jan")
    assert incoming["direction"] == "incoming" and incoming["status"] == "pending"
    assert "invite" in {s["kind"] for s in _overview(client)["suggestions"]}
    accepted = client.post(f"{API}/links/{link_id}/accept", json={"share": "exists"})
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "active"
    assert accepted.json()["they_share"] == "gift"
    assert client.post(f"{API}/links/{link_id}/accept", json={"share": "exists"}).status_code == 409

    # Either side ends it; afterwards it is gone for both.
    assert client.post(f"{API}/links/{link_id}/end", json={}).status_code == 204
    login(client, "jan")
    assert all(link["id"] != link_id for link in _overview(client)["links"])


def test_invite_does_not_reveal_whether_someone_is_a_customer(client: TestClient) -> None:
    login(client, "jan")
    real = client.post(f"{API}/invites", json={"username": "marie", "my_role": "other"})
    fake = client.post(f"{API}/invites", json={"username": "nobody-here", "my_role": "other"})
    assert real.status_code == fake.status_code == 202
    assert real.json()["message"] == fake.json()["message"]
    assert real.json()["link"]["other_name"] == "marie"
    assert fake.json()["link"]["other_name"] == "nobody-here"
    strip = {"id", "other_name", "since"}
    assert {k: v for k, v in real.json()["link"].items() if k not in strip} == {
        k: v for k, v in fake.json()["link"].items() if k not in strip
    }


def test_minors_cannot_be_invited_and_cannot_invite(client: TestClient) -> None:
    login(client, "emma")
    sent = client.post(f"{API}/invites", json={"username": "noor", "my_role": "other"})
    assert sent.status_code == 202  # same answer as for anyone...
    login(client, "noor")
    assert all(link["direction"] != "incoming" for link in _overview(client)["links"])  # ...no-op
    response = client.post(f"{API}/invites", json={"username": "emma", "my_role": "other"})
    assert response.status_code == 422
    # Minors get no nudges to give money.
    assert {s["kind"] for s in _overview(client)["suggestions"]} <= {"now_adult", "invite"}


def test_cannot_raise_what_the_other_side_shares(client: TestClient) -> None:
    login(client, "marie")
    link = _link_with(client, "Emma")
    # Marie can only change what *she* shares; Emma still shares "gift" with her.
    response = client.post(f"{API}/links/{link['id']}/sharing", json={"share": "balances"})
    assert response.json()["i_share"] == "balances"
    assert response.json()["they_share"] == "gift"
    assert client.get(f"{API}/links/{link['id']}/accounts").status_code == 404


def test_ending_a_link_removes_pot_access(client: TestClient) -> None:
    login(client, "marie")
    link = _link_with(client, "Emma")
    assert client.post(f"{API}/links/{link['id']}/end", json={}).status_code == 204
    assert all(p["name"] != "Ons trouwfeest" for p in _overview(client)["pots"])


def test_create_pot_only_with_own_active_links(client: TestClient) -> None:
    login(client, "jan")
    noor_link = _link_with(client, "Noor")["id"]
    login(client, "emma")
    lucas_link = _link_with(client, "Lucas")["id"]
    created = client.post(
        f"{API}/pots", json={"name": "Huis", "goal": "20000.00", "member_link_ids": [lucas_link]}
    )
    assert created.status_code == 201
    assert created.json()["members"] == ["Lucas Janssens"]
    stolen = client.post(f"{API}/pots", json={"name": "X", "member_link_ids": [noor_link]})
    assert stolen.status_code == 404
    bad_name = client.post(f"{API}/pots", json={"name": "a\u0000b"})
    assert bad_name.status_code == 422


def test_validation(emma: TestClient) -> None:
    assert (
        emma.post(f"{API}/invites", json={"username": "../x", "my_role": "other"}).status_code
        == 422
    )
    assert (
        emma.post(f"{API}/invites", json={"username": "lucas", "my_role": "boss"}).status_code
        == 422
    )
    assert (
        emma.post(
            f"{API}/invites", json={"username": "lucas", "my_role": "other", "extra": 1}
        ).status_code
        == 422
    )
    pot_id = _wedding_pot(emma)["id"]
    for amount in ("0", "-5.00", "10.001", "20000.00"):
        response = emma.post(
            f"{API}/pots/{pot_id}/contributions",
            json={"from_account_id": "a_emma_1", "amount": amount},
        )
        assert response.status_code == 422, amount
