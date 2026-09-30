from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.domain.models import Category, Transaction
from app.subscriptions.detect import detect
from tests.conftest import login


def _subs(client: TestClient) -> dict[str, dict[str, object]]:
    body = client.get("/api/v1/subscriptions").json()
    return {s["name"]: s for s in body["subscriptions"]}


def test_requires_login(client: TestClient) -> None:
    assert client.get("/api/v1/subscriptions").status_code == 401


def test_emma_pays_twice_for_streaming_and_has_a_converted_trial(emma: TestClient) -> None:
    subs = _subs(emma)
    assert set(subs) == {"Netflix", "Disney+", "Spotify"}
    assert "duplicate" in subs["Netflix"]["flags"]  # type: ignore[operator]
    assert subs["Netflix"]["duplicate_of"] == ["Disney+"]
    assert set(subs["Disney+"]["flags"]) == {"duplicate", "trial_converted"}  # type: ignore[arg-type]
    assert subs["Spotify"]["flags"] == []
    assert subs["Netflix"]["yearly_cost"] == "161.88"
    assert "We weten niet of je het gebruikt" in str(subs["Netflix"]["reason"])


def test_price_increase_and_sensitive_subscription_hidden(client: TestClient) -> None:
    login(client, "jan")
    body = client.get("/api/v1/subscriptions").json()
    subs = {s["name"]: s for s in body["subscriptions"]}
    assert subs["Netflix"]["flags"] == ["price_increase"]
    assert subs["Netflix"]["previous_amount"] == "13.49"
    assert subs["Netflix"]["amount"] == "15.99"
    assert body["hidden_sensitive"] == 1
    assert not any("ACV" in name or "Vakbond" in name for name in subs)
    assert "Vakbond" not in str(body)
    assert "Luminus" not in subs  # energy above the subscription range is not a subscription


def test_only_own_subscriptions(emma: TestClient) -> None:
    names = set(_subs(emma))
    assert "Basic-Fit" not in names and "De Standaard" not in names


def test_feedback_reminder_and_savings(emma: TestClient) -> None:
    disney = _subs(emma)["Disney+"]
    response = emma.post(
        f"/api/v1/subscriptions/{disney['id']}/feedback",
        json={"still_used": False, "remind_to_cancel": True},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancel_reminder"
    assert date.fromisoformat(response.json()["remind_on"]) >= date.today()
    body = emma.get("/api/v1/subscriptions").json()
    assert body["yearly_savings"] == "131.88"

    netflix = _subs(emma)["Netflix"]
    in_use = emma.post(f"/api/v1/subscriptions/{netflix['id']}/feedback", json={"still_used": True})
    assert in_use.json()["status"] == "in_use"


def test_feedback_on_someone_elses_subscription_is_404(client: TestClient) -> None:
    login(client, "jan")
    jans_gym = {s["name"]: s for s in client.get("/api/v1/subscriptions").json()["subscriptions"]}[
        "Basic-Fit"
    ]["id"]
    login(client, "emma")
    response = client.post(f"/api/v1/subscriptions/{jans_gym}/feedback", json={"still_used": True})
    assert response.status_code == 404


def test_feedback_validates_id_and_body(emma: TestClient) -> None:
    assert (
        emma.post("/api/v1/subscriptions/../../admin/feedback", json={"still_used": True})
    ).status_code == 404
    assert (
        emma.post("/api/v1/subscriptions/sub_zzzzzzzzzzzz/feedback", json={"still_used": True})
    ).status_code == 422
    sub_id = next(iter(_subs(emma).values()))["id"]
    bad = emma.post(f"/api/v1/subscriptions/{sub_id}/feedback", json={"still_used": "maybe"})
    assert bad.status_code == 422


def _monthly(
    name: str, amounts: list[str], category: Category = Category.LEISURE
) -> list[Transaction]:
    today = date.today()
    return [
        Transaction(
            id=f"t_{name}_{i}",
            account_id="a_x",
            booked_at=today - timedelta(days=30 * (len(amounts) - 1 - i)),
            description=name,
            counterparty=name,
            amount=-Decimal(amount),
            category=category,
        )
        for i, amount in enumerate(amounts)
    ]


def test_detection_ignores_irregular_spending_and_large_bills() -> None:
    random_spend = _monthly("Colruyt", ["12.10", "48.30", "23.99"])
    rent = _monthly("Immo", ["950.00", "950.00"], Category.OTHER)
    single = _monthly("Netflix", ["13.49"])
    result = detect("u_x", [*random_spend, *rent, *single], date.today())
    assert result.subscriptions == []


def test_sensitive_is_counted_not_shown() -> None:
    result = detect("u_x", _monthly("Headspace meditatie", ["12.99", "12.99"]), date.today())
    assert result.subscriptions == [] and result.hidden_sensitive == 1


# --- new detections, one-click removal, manual add ------------------------------------------------
def test_recent_subscription_is_marked_new(emma: TestClient) -> None:
    subs = _subs(emma)
    assert subs["Disney+"]["is_new"] is True
    assert subs["Spotify"]["is_new"] is False
    assert subs["Disney+"]["source"] == "detected"


def test_dismiss_removes_with_one_click_and_can_be_undone(emma: TestClient) -> None:
    disney = _subs(emma)["Disney+"]
    body = emma.post(
        f"/api/v1/subscriptions/{disney['id']}/dismiss", json={"dismissed": True}
    ).json()
    names = {s["name"] for s in body["subscriptions"]}
    assert "Disney+" not in names
    assert body["dismissed"] == 1
    # Netflix is no longer a duplicate once Disney+ is gone.
    netflix = next(s for s in body["subscriptions"] if s["name"] == "Netflix")
    assert "duplicate" not in netflix["flags"]

    undo = emma.post(f"/api/v1/subscriptions/{disney['id']}/dismiss", json={"dismissed": False})
    assert "Disney+" in {s["name"] for s in undo.json()["subscriptions"]}
    assert undo.json()["dismissed"] == 0


def test_cannot_dismiss_someone_elses_subscription(client: TestClient) -> None:
    login(client, "jan")
    gym = {s["name"]: s for s in client.get("/api/v1/subscriptions").json()["subscriptions"]}[
        "Basic-Fit"
    ]["id"]
    login(client, "emma")
    response = client.post(f"/api/v1/subscriptions/{gym}/dismiss", json={"dismissed": True})
    assert response.status_code == 404
    login(client, "jan")
    assert "Basic-Fit" in {
        s["name"] for s in client.get("/api/v1/subscriptions").json()["subscriptions"]
    }


def test_add_subscription_manually(emma: TestClient) -> None:
    response = emma.post("/api/v1/subscriptions", json={"name": "  Streamz  ", "amount": "9.99"})
    assert response.status_code == 201
    subs = {s["name"]: s for s in response.json()["subscriptions"]}
    assert subs["Streamz"]["source"] == "manual"
    assert subs["Streamz"]["group"] == "streaming"
    assert "duplicate" in subs["Streamz"]["flags"]  # a third streaming service
    assert "zelf toe" in subs["Streamz"]["reason"]

    # Manual ones are private to the customer and can be removed again.
    sub_id = subs["Streamz"]["id"]
    body = emma.post(f"/api/v1/subscriptions/{sub_id}/dismiss", json={"dismissed": True}).json()
    assert "Streamz" not in {s["name"] for s in body["subscriptions"]}


def test_manual_flags_do_not_accumulate(emma: TestClient) -> None:
    emma.post("/api/v1/subscriptions", json={"name": "Streamz", "amount": "9.99"})
    for _ in range(3):
        subs = _subs(emma)
    assert subs["Streamz"]["flags"] == ["duplicate"]


def test_manual_input_is_validated(emma: TestClient) -> None:
    for body in (
        {"name": "", "amount": "9.99"},
        {"name": "X", "amount": "0"},
        {"name": "X", "amount": "5000"},
        {"name": "X", "amount": "9.999"},
        {"name": "X\u0000", "amount": "9.99"},
        {"name": "X", "amount": "9.99", "next_charge": "2020-01-01"},
        {"name": "X", "amount": "9.99", "owner_id": "u_jan"},
    ):
        assert emma.post("/api/v1/subscriptions", json=body).status_code == 422, body
