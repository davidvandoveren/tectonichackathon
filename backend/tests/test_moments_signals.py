"""Signal extraction: layer 1 of the moments engine.

Fixtures are hand-built here on purpose (see docs/design/moments-engine.md section 12) so these
tests keep passing when someone edits the synthetic seed.
"""

from datetime import date, timedelta
from decimal import Decimal

from app.domain.models import Account, AccountType, Category, Transaction
from app.moments.ledger import Ledger
from app.moments.signals import extract_signals

TODAY = date(2026, 9, 30)


def account(
    account_id: str, account_type: AccountType, balance: str, iban: str = "BE68539007547034"
) -> Account:
    return Account(
        id=account_id,
        owner_id="u1",
        name=account_id,
        type=account_type,
        iban=iban,
        balance=Decimal(balance),
    )


def tx(
    days_ago: int,
    amount: str,
    counterparty: str = "Shop",
    category: Category = Category.OTHER,
    account_id: str = "cur",
) -> Transaction:
    return Transaction(
        id=f"t_{days_ago}_{counterparty}_{amount}",
        account_id=account_id,
        booked_at=TODAY - timedelta(days=days_ago),
        description=counterparty,
        counterparty=counterparty,
        amount=Decimal(amount),
        category=category,
    )


def ledger(accounts: list[Account], transactions: list[Transaction]) -> Ledger:
    return Ledger(user_id="u1", accounts=accounts, transactions=transactions, today=TODAY)


def types_in(signals: list) -> set[str]:  # type: ignore[type-arg]
    return {s.type for s in signals}


def find(signals: list, signal_type: str):  # type: ignore[type-arg, no-untyped-def]
    return next((s for s in signals if s.type == signal_type), None)


CURRENT = account("cur", AccountType.CURRENT, "1000.00")
SAVINGS = account("sav", AccountType.SAVINGS, "5000.00", iban="BE71096123456769")


# --- income ------------------------------------------------------------------------------------


def test_new_income_payer_fires_for_a_payer_absent_from_older_history() -> None:
    history = [tx(d, "310.00", "Delhaize", Category.INCOME) for d in (75, 45)]
    signals = extract_signals(
        ledger([CURRENT], [*history, tx(5, "1985.00", "Proximus NV", Category.INCOME)])
    )

    signal = find(signals, "new_income_payer")
    assert signal is not None
    assert "Proximus NV" in signal.evidence
    assert signal.domain == "income"


def test_new_income_payer_stays_silent_for_a_known_payer() -> None:
    history = [tx(d, "3120.00", "Acme BV", Category.INCOME) for d in (95, 65, 35)]
    signals = extract_signals(
        ledger([CURRENT], [*history, tx(5, "3120.00", "Acme BV", Category.INCOME)])
    )

    assert find(signals, "new_income_payer") is None


def test_income_step_up_fires_when_recent_income_dwarfs_the_baseline() -> None:
    history = [tx(d, "310.00", "Delhaize", Category.INCOME) for d in (75, 45)]
    signals = extract_signals(
        ledger([CURRENT], [*history, tx(5, "1985.00", "Proximus NV", Category.INCOME)])
    )

    signal = find(signals, "income_step_up")
    assert signal is not None
    assert signal.strength > 0.5


def test_income_step_up_stays_silent_when_income_is_flat() -> None:
    txs = [tx(d, "3120.00", "Acme BV", Category.INCOME) for d in (95, 65, 35, 5)]

    assert find(extract_signals(ledger([CURRENT], txs)), "income_step_up") is None


def test_expected_income_missing_fires_when_a_recurring_salary_does_not_arrive() -> None:
    # Paid on the 5th for three months, then nothing: today is the 30th, so it is 25 days overdue.
    txs = [tx(d, "3120.00", "Acme BV", Category.INCOME) for d in (115, 85, 55)]

    signal = find(extract_signals(ledger([CURRENT], txs)), "expected_income_missing")
    assert signal is not None
    assert "Acme BV" in signal.evidence
    assert signal.strength > 0.5


def test_expected_income_missing_stays_silent_when_the_salary_did_arrive() -> None:
    txs = [tx(d, "3120.00", "Acme BV", Category.INCOME) for d in (115, 85, 55, 25)]

    assert find(extract_signals(ledger([CURRENT], txs)), "expected_income_missing") is None


# --- balances ----------------------------------------------------------------------------------


def test_thin_buffer_fires_when_the_balance_cannot_cover_the_largest_housing_cost() -> None:
    poor = account("cur", AccountType.CURRENT, "180.00")
    txs = [tx(20, "-950.00", "Immo Gent", Category.HOUSING)]

    signal = find(extract_signals(ledger([poor], txs)), "thin_buffer")
    assert signal is not None
    assert signal.domain == "balances"


def test_thin_buffer_stays_silent_when_the_balance_is_comfortable() -> None:
    rich = account("cur", AccountType.CURRENT, "4000.00")
    txs = [tx(20, "-950.00", "Immo Gent", Category.HOUSING)]

    assert find(extract_signals(ledger([rich], txs)), "thin_buffer") is None


def test_idle_liquidity_fires_when_savings_dwarf_monthly_spending() -> None:
    fat = account("sav", AccountType.SAVINGS, "64250.00", iban="BE71096123456769")
    txs = [tx(10, "-200.00", "Carrefour", Category.GROCERIES)]

    signal = find(extract_signals(ledger([CURRENT, fat], txs)), "idle_liquidity")
    assert signal is not None
    assert signal.domain == "balances"


def test_idle_liquidity_stays_silent_when_savings_are_a_few_months_of_spending() -> None:
    thin = account("sav", AccountType.SAVINGS, "600.00", iban="BE71096123456769")
    txs = [tx(10, "-200.00", "Carrefour", Category.GROCERIES)]

    assert find(extract_signals(ledger([CURRENT, thin], txs)), "idle_liquidity") is None


# --- spending shape ----------------------------------------------------------------------------


def test_large_outflow_outlier_fires_on_a_payment_far_above_this_customers_normal() -> None:
    normal = [tx(d, "-45.00", "Bol.com", Category.SHOPPING) for d in (80, 70, 60, 50, 40)]
    txs = [*normal, tx(6, "-1240.50", "IKEA Gent", Category.SHOPPING)]

    signal = find(extract_signals(ledger([CURRENT], txs)), "large_outflow_outlier")
    assert signal is not None
    assert "IKEA Gent" in signal.evidence


def test_large_outflow_outlier_stays_silent_on_a_merely_bigger_payment() -> None:
    normal = [tx(d, "-45.00", "Bol.com", Category.SHOPPING) for d in (80, 70, 60, 50, 40)]
    txs = [*normal, tx(6, "-70.00", "Bol.com", Category.SHOPPING)]

    assert find(extract_signals(ledger([CURRENT], txs)), "large_outflow_outlier") is None


def test_deposit_like_outflow_fires_on_a_housing_payment_near_two_months_rent() -> None:
    rent = [tx(d, "-950.00", "Immo Gent", Category.HOUSING) for d in (95, 65, 35)]
    txs = [*rent, tx(3, "-1900.00", "Waarborgrekening", Category.HOUSING)]

    signal = find(extract_signals(ledger([CURRENT], txs)), "deposit_like_outflow")
    assert signal is not None
    # Detected from the shape of the amount, never from the counterparty's name.
    assert "1900" in signal.evidence.replace(" ", "").replace(".", "").replace(",", "")


def test_deposit_like_outflow_stays_silent_on_an_ordinary_rent_payment() -> None:
    rent = [tx(d, "-950.00", "Immo Gent", Category.HOUSING) for d in (95, 65, 35, 5)]

    assert find(extract_signals(ledger([CURRENT], rent)), "deposit_like_outflow") is None


def test_category_spend_spike_fires_when_a_category_doubles_against_its_own_baseline() -> None:
    baseline = [tx(d, "-50.00", "Bol.com", Category.SHOPPING) for d in (85, 75, 65, 55, 45)]
    recent = [tx(d, "-300.00", "Leen Bakker", Category.SHOPPING) for d in (20, 12, 4)]

    signal = find(extract_signals(ledger([CURRENT], [*baseline, *recent])), "category_spend_spike")
    assert signal is not None
    assert signal.meta["category"] == "shopping"


def test_category_spend_spike_stays_silent_on_steady_spending() -> None:
    steady = [tx(d, "-50.00", "Bol.com", Category.SHOPPING) for d in (85, 75, 65, 55, 20, 10)]

    assert find(extract_signals(ledger([CURRENT], steady)), "category_spend_spike") is None


def test_merchant_concentration_fires_on_a_repeatedly_used_counterparty() -> None:
    fuel = [tx(d, "-65.00", "Q8 Wilrijk", Category.TRANSPORT) for d in (80, 66, 52, 38, 24, 10)]

    signal = find(extract_signals(ledger([CURRENT], fuel)), "merchant_concentration")
    assert signal is not None
    assert signal.meta["counterparty"] == "Q8 Wilrijk"
    assert signal.meta["category"] == "transport"


def test_merchant_concentration_stays_silent_on_scattered_spending() -> None:
    scattered = [
        tx(d, "-65.00", name, Category.TRANSPORT)
        for d, name in ((80, "NMBS"), (66, "De Lijn"), (52, "Q8"), (38, "Shell"), (24, "Total"))
    ]

    assert find(extract_signals(ledger([CURRENT], scattered)), "merchant_concentration") is None


def test_a_sensitive_merchant_never_becomes_a_signal() -> None:
    """Issue #35: health, religion, politics, unions and dating must never feed the profile."""
    pharmacy = [tx(d, "-20.00", "Apotheek", Category.OTHER) for d in (80, 66, 52, 38, 24, 10)]

    signals = extract_signals(ledger([CURRENT], pharmacy))

    assert find(signals, "merchant_concentration") is None
    assert not any("Apotheek" in s.evidence or "Apotheek" in s.meta.values() for s in signals)


def test_sensitive_spending_is_invisible_to_every_extractor() -> None:
    """Filtered before extraction, not afterwards: a large hospital bill is no 'outlier' either."""
    history = [tx(d, "-40.00", f"Winkel {d}", Category.OTHER) for d in range(35, 90, 7)]

    def big_bill_at(merchant: str) -> Transaction:
        return tx(3, "-2400.00", merchant, Category.OTHER)

    ordinary = extract_signals(ledger([CURRENT], [*history, big_bill_at("Mediamarkt")]))
    sensitive = extract_signals(ledger([CURRENT], [*history, big_bill_at("AZ Ziekenhuis")]))

    assert find(ordinary, "large_outflow_outlier") is not None, "the fixture must be meaningful"
    assert sensitive == extract_signals(ledger([CURRENT], history))


def test_public_transport_is_not_a_deal_merchant() -> None:
    """Issue #35: De Lijn and NMBS have no Kate Deal; a fuel station does."""
    for operator in ("De Lijn", "NMBS", "SNCB", "STIB", "MIVB", "TEC"):
        rides = [tx(d, "-6.00", operator, Category.TRANSPORT) for d in (80, 66, 52, 38, 24, 10)]

        assert find(extract_signals(ledger([CURRENT], rides)), "merchant_concentration") is None


# --- self-transfers (the savings habit) --------------------------------------------------------


def paired_transfer(days_ago: int, amount: str) -> list[Transaction]:
    """A transfer between the customer's own accounts: a debit and a matching credit."""
    return [
        tx(days_ago, f"-{amount}", "Eigen spaarrekening", Category.TRANSFER, account_id="cur"),
        tx(days_ago, amount, "Eigen zichtrekening", Category.TRANSFER, account_id="sav"),
    ]


def test_recurring_self_transfer_fires_on_a_monthly_transfer_to_own_savings() -> None:
    txs = [t for d in (92, 61, 30) for t in paired_transfer(d, "200.00")]

    signal = find(extract_signals(ledger([CURRENT, SAVINGS], txs)), "recurring_self_transfer")
    assert signal is not None
    assert signal.meta["median_amount"] == "200.00"
    assert signal.meta["months"] == "3"


def test_recurring_self_transfer_stays_silent_on_a_single_transfer() -> None:
    txs = paired_transfer(30, "200.00")

    assert find(extract_signals(ledger([CURRENT, SAVINGS], txs)), "recurring_self_transfer") is None


def test_recurring_self_transfer_ignores_payments_to_other_people() -> None:
    # Same amounts and cadence, but no matching credit on an own account: not a self-transfer.
    txs = [tx(d, "-200.00", "Lucas Janssens", Category.TRANSFER) for d in (92, 61, 30)]

    assert find(extract_signals(ledger([CURRENT, SAVINGS], txs)), "recurring_self_transfer") is None


def test_reverse_savings_transfer_fires_when_money_came_back_out_of_savings() -> None:
    out = [
        tx(20, "-500.00", "Eigen zichtrekening", Category.TRANSFER, account_id="sav"),
        tx(20, "500.00", "Eigen spaarrekening", Category.TRANSFER, account_id="cur"),
    ]

    signal = find(extract_signals(ledger([CURRENT, SAVINGS], out)), "reverse_savings_transfer")
    assert signal is not None
    assert signal.domain == "spending"


def test_reverse_savings_transfer_stays_silent_when_savings_only_grew() -> None:
    txs = [t for d in (92, 61, 30) for t in paired_transfer(d, "200.00")]

    assert (
        find(extract_signals(ledger([CURRENT, SAVINGS], txs)), "reverse_savings_transfer") is None
    )


# --- consent -----------------------------------------------------------------------------------


def test_switching_off_a_consent_domain_removes_its_signals() -> None:
    history = [tx(d, "310.00", "Delhaize", Category.INCOME) for d in (75, 45)]
    txs = [*history, tx(5, "1985.00", "Proximus NV", Category.INCOME)]

    allowed = extract_signals(ledger([CURRENT], txs))
    assert "income" in {s.domain for s in allowed}

    withheld = extract_signals(ledger([CURRENT], txs), consent={"spending", "balances"})
    assert "income" not in {s.domain for s in withheld}


def test_every_signal_carries_a_plain_language_evidence_string() -> None:
    history = [tx(d, "310.00", "Delhaize", Category.INCOME) for d in (75, 45)]
    txs = [*history, tx(5, "1985.00", "Proximus NV", Category.INCOME)]

    for signal in extract_signals(ledger([CURRENT], txs)):
        assert signal.evidence.strip(), f"{signal.type} has no evidence"
        assert 0.0 < signal.strength <= 1.0, f"{signal.type} has strength {signal.strength}"


# --- card packages (design §5.2) ---------------------------------------------------------------


def package_fees(name: str, amount: str) -> list[Transaction]:
    return [tx(d, f"-{amount}", f"{name} kredietkaart", Category.OTHER) for d in (87, 57, 27)]


def test_an_unused_luxepakket_is_noticed() -> None:
    signal = find(
        extract_signals(ledger([CURRENT], package_fees("Luxepakket", "25.00"))),
        "paid_package_unused",
    )

    assert signal is not None
    assert signal.domain == "products"
    assert signal.meta["package"] == "luxe"
    assert signal.meta["yearly_cost"] == "300.00"
    assert "Luxepakket" in signal.evidence


def test_a_package_that_is_used_for_travel_is_not_waste() -> None:
    txs = [*package_fees("Luxepakket", "25.00"), tx(40, "-189.00", "Ryanair", Category.LEISURE)]

    signals = extract_signals(ledger([CURRENT], txs))

    assert find(signals, "paid_package_unused") is None
    assert find(signals, "travel_cover_held") is not None


def test_a_shoppingpakket_is_never_called_waste_for_lack_of_travel() -> None:
    signals = extract_signals(ledger([CURRENT], package_fees("Shoppingpakket", "1.50")))

    assert find(signals, "paid_package_unused") is None
    assert find(signals, "travel_cover_held") is None


def test_travel_spend_counts_flights_hotels_and_foreign_payments() -> None:
    abroad = Transaction(
        id="t_abroad",
        account_id="cur",
        booked_at=TODAY - timedelta(days=12),
        description="Restaurant Lisboa",
        counterparty="Restaurant Lisboa",
        amount=Decimal("-42.00"),
        category=Category.LEISURE,
        currency="USD",
    )
    txs = [
        tx(70, "-240.00", "Brussels Airlines", Category.LEISURE),
        tx(69, "-310.00", "Booking.com", Category.LEISURE),
        abroad,
    ]

    signal = find(extract_signals(ledger([CURRENT], txs)), "travel_spend")

    assert signal is not None
    assert signal.meta["trips"] == "3"
    assert signal.strength == 1.0


def test_travel_spend_stays_silent_on_ordinary_spending() -> None:
    txs = [tx(d, "-40.00", "Colruyt", Category.GROCERIES) for d in (60, 30, 5)]

    assert find(extract_signals(ledger([CURRENT], txs)), "travel_spend") is None


def test_package_signals_respect_the_products_consent() -> None:
    signals = extract_signals(
        ledger([CURRENT], package_fees("Luxepakket", "25.00")),
        consent={"income", "spending", "balances"},
    )

    assert find(signals, "paid_package_unused") is None
