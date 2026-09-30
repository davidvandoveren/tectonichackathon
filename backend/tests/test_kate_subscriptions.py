"""Subscription detection: recurring payments, duplicates and price rises (docs/plan.md §5)."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.domain.models import Account, AccountType, Category, Transaction
from app.kate.subscriptions import detect_subscriptions
from app.services.insights import CustomerSignals
from tests.conftest import login

TODAY = date(2026, 9, 30)


def _tx(
    booked_at: date,
    counterparty: str,
    amount: str,
    category: Category = Category.LEISURE,
) -> Transaction:
    return Transaction(
        id=f"t_{counterparty}_{booked_at.isoformat()}",
        account_id="a1",
        booked_at=booked_at,
        description=counterparty,
        counterparty=counterparty,
        amount=Decimal(amount),
        category=category,
    )


def _signals(*transactions: Transaction) -> CustomerSignals:
    account = Account(
        id="a1",
        owner_id="u1",
        name="Zichtrekening",
        type=AccountType.CURRENT,
        iban="BE78735000000186",
        balance=Decimal("500.00"),
    )
    return CustomerSignals(
        user_id="u1",
        accounts=[account],
        transactions=list(transactions),
        today=TODAY,
    )


def test_detects_a_monthly_payment_as_a_subscription() -> None:
    signals = _signals(
        _tx(date(2026, 7, 8), "Spotify", "-11.99"),
        _tx(date(2026, 8, 8), "Spotify", "-11.99"),
        _tx(date(2026, 9, 8), "Spotify", "-11.99"),
    )

    subscriptions = detect_subscriptions(signals)

    assert [s.name for s in subscriptions] == ["Spotify"]
    assert subscriptions[0].amount == Decimal("11.99")
    assert subscriptions[0].frequency == "monthly"


def test_daily_shopping_at_one_shop_is_not_a_subscription() -> None:
    signals = _signals(
        *[
            _tx(date(2026, month, day), "Colruyt", "-14.20", Category.GROCERIES)
            for month in (7, 8, 9)
            for day in (3, 11, 19, 27)
        ]
    )

    assert detect_subscriptions(signals) == []


def test_reports_a_price_rise_between_the_first_and_latest_booking() -> None:
    signals = _signals(
        _tx(date(2026, 7, 8), "Spotify", "-11.99"),
        _tx(date(2026, 8, 8), "Spotify", "-11.99"),
        _tx(date(2026, 9, 8), "Spotify", "-13.99"),
    )

    subscription = detect_subscriptions(signals)[0]

    assert subscription.amount == Decimal("13.99")
    assert subscription.price_change == Decimal("2.00")


def test_a_stable_price_reports_no_price_change() -> None:
    signals = _signals(
        _tx(date(2026, 7, 8), "Spotify", "-11.99"),
        _tx(date(2026, 8, 8), "Spotify", "-11.99"),
        _tx(date(2026, 9, 8), "Spotify", "-11.99"),
    )

    assert detect_subscriptions(signals)[0].price_change is None


def _monthly(
    counterparty: str, amount: str, category: Category = Category.LEISURE
) -> list[Transaction]:
    return [_tx(date(2026, month, 8), counterparty, amount, category) for month in (7, 8, 9)]


def test_flags_the_pricier_of_two_subscriptions_in_the_same_category_as_a_duplicate() -> None:
    signals = _signals(
        *_monthly("Spotify", "-11.99"),
        *_monthly("Deezer", "-14.99"),
    )

    by_name = {s.name: s for s in detect_subscriptions(signals)}

    assert by_name["Spotify"].duplicate_of is None
    assert by_name["Deezer"].duplicate_of == by_name["Spotify"].id


def test_a_lone_subscription_in_its_category_is_not_a_duplicate() -> None:
    signals = _signals(*_monthly("Spotify", "-11.99"))

    assert detect_subscriptions(signals)[0].duplicate_of is None


def test_never_surfaces_sensitive_recurring_payments() -> None:
    signals = _signals(
        *_monthly("KBC Verzekeringen", "-64.00", Category.OTHER),
        *_monthly("Spotify", "-11.99"),
    )

    assert [s.name for s in detect_subscriptions(signals)] == ["Spotify"]


def test_rent_is_recurring_but_not_a_subscription_you_can_cancel() -> None:
    signals = _signals(*_monthly("Kotbaas Leuven", "-420.00", Category.HOUSING))

    assert detect_subscriptions(signals) == []


def test_energy_and_internet_are_both_utilities_but_not_duplicates() -> None:
    signals = _signals(
        *_monthly("Luminus", "-142.00", Category.UTILITIES),
        *_monthly("Telenet", "-79.00", Category.UTILITIES),
    )

    assert [s.duplicate_of for s in detect_subscriptions(signals)] == [None, None]


# --- API ------------------------------------------------------------------------------------


def test_listing_subscriptions_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/subscriptions").status_code == 401


def test_lists_the_logged_in_customer_subscriptions(emma: TestClient) -> None:
    response = emma.get("/api/v1/subscriptions")

    assert response.status_code == 200, response.text
    names = [s["name"] for s in response.json()]
    assert "Spotify" in names
    assert "Kotbaas Leuven" not in names  # rent is a fixed cost, not a subscription


def test_a_listed_subscription_carries_the_documented_contract(emma: TestClient) -> None:
    spotify = next(s for s in emma.get("/api/v1/subscriptions").json() if s["name"] == "Spotify")

    assert spotify["frequency"] == "monthly"
    assert spotify["amount"] == "11.99"
    assert spotify["sensitive"] is False
    assert spotify["still_used"] is None
    assert spotify["remind_to_cancel"] is False


def test_feedback_is_remembered_for_the_next_page_load(emma: TestClient) -> None:
    spotify = next(s for s in emma.get("/api/v1/subscriptions").json() if s["name"] == "Spotify")

    posted = emma.post(
        f"/api/v1/subscriptions/{spotify['id']}/feedback",
        json={"still_used": False, "remind_to_cancel": True},
    )

    assert posted.status_code == 200, posted.text
    reloaded = next(s for s in emma.get("/api/v1/subscriptions").json() if s["name"] == "Spotify")
    assert reloaded["still_used"] is False
    assert reloaded["remind_to_cancel"] is True


def test_feedback_on_an_unknown_subscription_is_not_found(emma: TestClient) -> None:
    response = emma.post(
        "/api/v1/subscriptions/s_does_not_exist/feedback",
        json={"still_used": True, "remind_to_cancel": False},
    )

    assert response.status_code == 404


def test_cannot_leave_feedback_on_someone_elses_subscription(
    client: TestClient, emma: TestClient
) -> None:
    login(client, "jan")
    jan_ids = [s["id"] for s in client.get("/api/v1/subscriptions").json()]
    assert jan_ids, "jan should have subscriptions for this test to mean anything"
    login(emma, "emma")

    response = emma.post(
        f"/api/v1/subscriptions/{jan_ids[0]}/feedback",
        json={"still_used": True, "remind_to_cancel": False},
    )

    assert response.status_code == 404
