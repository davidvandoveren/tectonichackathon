"""Golden tests: the seeded demo personas trigger the moments the demo relies on.

These run against the real synthetic seed on purpose (unlike the per-signal tests), so a change to
`seed.py` that breaks the demo story fails here instead of on stage.
"""

from datetime import date

import pytest

from app.domain.bank import Bank
from app.domain.models import AccountType, Category
from app.domain.seed import seed_bank
from app.moments.engine import build_ledger, run
from app.moments.moments import detect_moments
from app.moments.signals import extract_signals, self_transfers

# A handful of "todays", including month ends and a February, so day-of-month quirks cannot hide.
TODAYS = [date(2026, 9, 30), date(2026, 10, 3), date(2026, 3, 1), date(2026, 5, 31)]


def seeded(today: date) -> Bank:
    bank = Bank()
    seed_bank(bank, "test-demo-password", today)
    return bank


def sofie(bank: Bank):  # type: ignore[no-untyped-def]
    user = bank.find_user_by_username("sofie")
    assert user is not None
    return user


@pytest.mark.parametrize("today", TODAYS)
def test_sofie_has_a_current_and_a_savings_account(today: date) -> None:
    bank = seeded(today)
    types = {a.type for a in bank.accounts_for(sofie(bank).id)}
    assert {AccountType.CURRENT, AccountType.SAVINGS} <= types


@pytest.mark.parametrize("today", TODAYS)
def test_sofie_moves_money_to_her_own_savings_every_month(today: date) -> None:
    bank = seeded(today)
    led = build_ledger(bank, sofie(bank), today)
    deposits = [s for s in self_transfers(led) if s.to_savings]
    assert len(deposits) >= 3
    assert all(s.booked_at <= today for s in deposits)
    # Both legs are booked, so the savings account shows the money arriving too.
    savings = led.account_ids_of(AccountType.SAVINGS)
    assert any(
        t.account_id in savings and t.category == Category.TRANSFER and t.amount > 0
        for t in led.transactions
    )


@pytest.mark.parametrize("today", TODAYS)
def test_sofie_triggers_savings_habit_and_fuel_deal(today: date) -> None:
    bank = seeded(today)
    user = sofie(bank)
    verdict = run(bank, user, today)
    said = {d.moment.type: d.moment for d in verdict.decisions}
    silenced = {s.moment_type for s in verdict.silenced}

    assert "savings_habit_automatable" in said
    # The deal is the lower-value opportunity, so arbitration may hold it back - but it must be
    # recognised, and it must be about the fuel station, not about groceries.
    noticed = {m.type: m for m in detect_moments(extract_signals(build_ledger(bank, user, today)))}
    assert "deal_match" in noticed
    assert noticed["deal_match"].meta["category"] == Category.TRANSPORT.value
    assert "deal_match" in said or "deal_match" in silenced


@pytest.mark.parametrize("today", TODAYS)
def test_sofie_is_not_in_financial_trouble(today: date) -> None:
    bank = seeded(today)
    noticed = {
        m.type for m in detect_moments(extract_signals(build_ledger(bank, sofie(bank), today)))
    }
    assert not noticed & {"cashflow_risk", "income_missing", "moving_house", "idle_savings"}


def test_sofie_pays_for_a_luxury_card_package_without_travelling() -> None:
    today = TODAYS[0]
    bank = seeded(today)
    led = build_ledger(bank, sofie(bank), today)
    fees = [t for t in led.transactions if "Luxepakket" in t.description]
    assert len(fees) >= 3
    assert all(t.amount == -25 for t in fees)


def test_existing_personas_keep_their_story() -> None:
    today = TODAYS[0]
    bank = seeded(today)
    expected = {"emma": "first_salary", "jan": "moving_house", "marie": "idle_savings"}
    for username, moment in expected.items():
        user = bank.find_user_by_username(username)
        assert user is not None
        noticed = {m.type for m in detect_moments(extract_signals(build_ledger(bank, user, today)))}
        assert moment in noticed, (username, noticed)


# --- briefing scenarios ------------------------------------------------------------------------


def user_named(bank: Bank, username: str):  # type: ignore[no-untyped-def]
    user = bank.find_user_by_username(username)
    assert user is not None
    return user


@pytest.mark.parametrize("today", TODAYS)
def test_bram_gets_a_cashflow_warning_that_interrupts(today: date) -> None:
    bank = seeded(today)
    verdict = run(bank, user_named(bank, "bram"), today)
    assert verdict.decisions[0].moment.type == "cashflow_risk"
    assert verdict.decisions[0].channel in {"push", "sms", "call"}


@pytest.mark.parametrize("today", TODAYS)
def test_bram_deal_is_deliberately_withheld(today: date) -> None:
    bank = seeded(today)
    verdict = run(bank, user_named(bank, "bram"), today)
    said = {d.moment.type for d in verdict.decisions}
    withheld = {s.moment_type: s.reason_code for s in verdict.silenced}
    assert "deal_match" not in said
    assert withheld.get("deal_match") == "cashflow_first"


@pytest.mark.parametrize("today", TODAYS)
def test_els_inheritance_gets_no_sales_pitch(today: date) -> None:
    bank = seeded(today)
    user = user_named(bank, "els")
    said = {d.moment.type for d in run(bank, user, today).decisions}
    assert not said & {"deal_match", "idle_savings", "card_package_gap"}
    # A notary paying out an estate is not a first salary, and a funeral is not a house move.
    noticed = {m.type for m in detect_moments(extract_signals(build_ledger(bank, user, today)))}
    assert not noticed & {"first_salary", "moving_house", "cashflow_risk", "income_missing"}


def test_els_history_tells_the_inheritance_story() -> None:
    today = TODAYS[0]
    bank = seeded(today)
    led = build_ledger(bank, user_named(bank, "els"), today)
    texts = " ".join(t.description for t in led.transactions)
    assert "Uitvaart" in texts
    assert "Nalatenschap" in texts
    estate = [t for t in led.transactions if "Nalatenschap" in t.description]
    assert estate and all(t.amount > 0 for t in estate)
