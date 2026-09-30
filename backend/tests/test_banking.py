from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from tests.conftest import login

VALID_IBAN = "BE71096123456769"


def _transfer(client: TestClient, **overrides: str) -> dict[str, str]:
    body = {
        "from_account_id": "a_emma_1",
        "to_iban": VALID_IBAN,
        "to_name": "Lucas Janssens",
        "amount": "25.00",
        "description": "Pizza",
    } | overrides
    response = client.post("/api/v1/transfers", json=body)
    return {"status": str(response.status_code), **response.json()}


def test_accounts_only_show_own_data(emma: TestClient) -> None:
    accounts = emma.get("/api/v1/accounts").json()
    assert accounts
    assert all(a["id"].startswith("a_emma_") for a in accounts)
    assert isinstance(accounts[0]["balance"], str)


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/accounts/a_jan_1",
        "/api/v1/accounts/a_jan_1/transactions",
        "/api/v1/accounts/does-not-exist",
    ],
)
def test_idor_other_users_account_is_not_found(emma: TestClient, path: str) -> None:
    response = emma.get(path)
    assert response.status_code == 404
    assert response.json() == {"detail": "Account not found"}


def test_cannot_transfer_from_someone_elses_account(emma: TestClient) -> None:
    result = _transfer(emma, from_account_id="a_jan_1")
    assert result["status"] == "404"


def test_transfer_moves_money_and_books_transaction(emma: TestClient) -> None:
    before = Decimal(emma.get("/api/v1/accounts/a_emma_1").json()["balance"])
    result = _transfer(emma, amount="25.10")
    assert result["status"] == "201"
    assert result["amount"] == "-25.10"
    after = Decimal(emma.get("/api/v1/accounts/a_emma_1").json()["balance"])
    assert before - after == Decimal("25.10")


def test_internal_transfer_credits_the_receiver(client: TestClient) -> None:
    login(client, "jan")
    jan_iban = client.get("/api/v1/accounts/a_jan_1").json()["iban"]
    jan_before = Decimal(client.get("/api/v1/accounts/a_jan_1").json()["balance"])
    login(client, "emma")
    assert _transfer(client, to_iban=jan_iban, amount="10.00")["status"] == "201"
    login(client, "jan")
    jan_after = Decimal(client.get("/api/v1/accounts/a_jan_1").json()["balance"])
    assert jan_after - jan_before == Decimal("10.00")


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"amount": "0"}, "422"),
        ({"amount": "-5.00"}, "422"),
        ({"amount": "1.001"}, "422"),
        ({"amount": "10000.01"}, "422"),
        ({"amount": "9999.00"}, "422"),  # more than the balance
        ({"to_iban": "BE00096123456769"}, "422"),  # bad checksum
        ({"to_name": ""}, "422"),
        ({"description": "x" * 141}, "422"),
    ],
)
def test_transfer_business_rules(
    emma: TestClient, overrides: dict[str, str], expected: str
) -> None:
    assert _transfer(emma, **overrides)["status"] == expected


def test_cannot_transfer_to_same_account(emma: TestClient) -> None:
    own_iban = emma.get("/api/v1/accounts/a_emma_1").json()["iban"]
    assert _transfer(emma, to_iban=own_iban)["status"] == "422"


def test_csrf_guard_rejects_non_json_and_foreign_origin(emma: TestClient) -> None:
    form = emma.post("/api/v1/transfers", data={"amount": "1"})
    assert form.status_code == 415
    foreign = emma.post(
        "/api/v1/transfers",
        json={"amount": "1"},
        headers={"Origin": "https://evil.example"},
    )
    assert foreign.status_code == 403


def test_security_headers_present(client: TestClient) -> None:
    headers = client.get("/health").headers
    assert "default-src 'self'" in headers["content-security-policy"]
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "SAMEORIGIN"


def test_insights_are_personal_and_explained(client: TestClient) -> None:
    expected = {
        "emma": "i_first_salary_u_emma",
        "jan": "i_moving_u_jan",
        "marie": "i_idle_savings_u_marie",
    }
    for username, insight_id in expected.items():
        login(client, username)
        insights = client.get("/api/v1/insights").json()
        assert insight_id in {i["id"] for i in insights}
        assert all(i["reason"] for i in insights)
