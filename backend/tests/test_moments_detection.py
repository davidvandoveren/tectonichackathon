"""Layer 2 - moment detection.

A moment is a weighted combination of signals, never a single threshold. These tests build
signals by hand so they document exactly which evidence produces which moment, and what
counter-evidence does.
"""

from datetime import date
from decimal import Decimal

from app.moments.moments import (
    ACT_THRESHOLD,
    NOTICE_THRESHOLD,
    detect_moments,
)
from app.moments.signals import Signal

TODAY = date(2026, 9, 30)


def signal(signal_type: str, strength: float = 1.0, **meta: str) -> Signal:
    return Signal(
        type=signal_type,
        domain="spending",
        strength=strength,
        observed_at=TODAY,
        evidence=f"evidence for {signal_type}",
        meta=meta,
    )


def find(moments: list, moment_type: str):  # type: ignore[type-arg, no-untyped-def]
    return next((m for m in moments if m.type == moment_type), None)


# --- risk --------------------------------------------------------------------------------------


def test_thin_buffer_produces_a_cashflow_risk_moment() -> None:
    moment = find(detect_moments([signal("thin_buffer", 0.8)]), "cashflow_risk")

    assert moment is not None
    assert moment.urgency == "risk"
    assert moment.confidence >= ACT_THRESHOLD


def test_missing_salary_produces_its_own_risk_moment() -> None:
    moment = find(
        detect_moments([signal("expected_income_missing", 1.0, days_overdue="9")]),
        "income_missing",
    )

    assert moment is not None
    assert moment.urgency == "risk"


# --- first salary needs two independent pieces of evidence -------------------------------------


def test_first_salary_fires_when_a_new_payer_and_a_step_up_agree() -> None:
    moment = find(
        detect_moments([signal("new_income_payer", 1.0), signal("income_step_up", 1.0)]),
        "first_salary",
    )

    assert moment is not None
    assert moment.confidence >= ACT_THRESHOLD


def test_first_salary_stays_silent_on_a_new_payer_alone() -> None:
    # A new payer without a jump in income is just a new payer: a refund, a friend, a bonus.
    assert find(detect_moments([signal("new_income_payer", 1.0)]), "first_salary") is None


# --- moving house is composed, not keyword-matched ---------------------------------------------


def test_moving_house_is_confident_when_three_independent_signals_agree() -> None:
    moment = find(
        detect_moments(
            [
                signal("large_outflow_outlier", 1.0),
                signal("deposit_like_outflow", 1.0),
                signal("category_spend_spike", 1.0),
            ]
        ),
        "moving_house",
    )

    assert moment is not None
    assert moment.confidence >= ACT_THRESHOLD
    assert len(moment.signals) == 3


def test_moving_house_is_noticed_but_not_acted_on_with_one_signal() -> None:
    moment = find(detect_moments([signal("deposit_like_outflow", 1.0)]), "moving_house")

    assert moment is not None, "a single deposit-shaped payment is worth noticing"
    assert NOTICE_THRESHOLD <= moment.confidence < ACT_THRESHOLD, "but not worth acting on"


def test_moving_house_stays_silent_on_a_spending_spike_alone() -> None:
    assert find(detect_moments([signal("category_spend_spike", 1.0)]), "moving_house") is None


# --- counter-evidence --------------------------------------------------------------------------


def test_idle_savings_fires_on_idle_liquidity() -> None:
    moment = find(
        detect_moments([signal("idle_liquidity", 1.0, savings="64250.00")]), "idle_savings"
    )

    assert moment is not None
    assert moment.urgency == "opportunity"


def test_idle_savings_is_suppressed_by_a_thin_buffer() -> None:
    # Telling someone with no buffer that their savings are lazy is tone deaf.
    moments = detect_moments(
        [signal("idle_liquidity", 1.0, savings="64250.00"), signal("thin_buffer", 0.9)]
    )

    assert find(moments, "idle_savings") is None


def test_savings_habit_fires_on_a_repeated_self_transfer() -> None:
    moment = find(
        detect_moments(
            [
                signal(
                    "recurring_self_transfer",
                    0.75,
                    median_amount="200.00",
                    months="3",
                    day_of_month="28",
                )
            ]
        ),
        "savings_habit_automatable",
    )

    assert moment is not None
    assert moment.meta["amount"] == "200.00"
    assert moment.value_eur_per_year == Decimal("2400.00")


def test_savings_habit_is_killed_by_a_withdrawal_from_savings() -> None:
    # Someone who has pulled money back out needs the liquidity; a standing order would harm them.
    moments = detect_moments(
        [
            signal("recurring_self_transfer", 0.75, median_amount="200.00", months="3"),
            signal("reverse_savings_transfer", 1.0),
        ]
    )

    assert find(moments, "savings_habit_automatable") is None


def test_deal_match_carries_the_estimated_yearly_value() -> None:
    moment = find(
        detect_moments(
            [
                signal(
                    "merchant_concentration",
                    1.0,
                    counterparty="Q8 Wilrijk",
                    category="transport",
                    bookings="18",
                    yearly_spend="3120.00",
                )
            ]
        ),
        "deal_match",
    )

    assert moment is not None
    assert moment.meta["counterparty"] == "Q8 Wilrijk"
    assert moment.value_eur_per_year is not None
    assert moment.value_eur_per_year > 0


# --- properties that must hold for every moment ------------------------------------------------


def test_no_signals_means_no_moments() -> None:
    assert detect_moments([]) == []


def test_every_moment_explains_itself_from_its_signals() -> None:
    moments = detect_moments(
        [
            signal("large_outflow_outlier", 1.0),
            signal("deposit_like_outflow", 1.0),
            signal("category_spend_spike", 1.0),
        ]
    )

    assert moments
    for moment in moments:
        assert moment.signals, f"{moment.type} has no supporting signals"
        # Explainability is structural: the reason is assembled from the evidence, not written
        # separately per rule, so it can never drift from what was actually observed.
        for supporting in moment.signals:
            assert supporting.evidence in moment.reason


def test_confidence_always_stays_within_bounds() -> None:
    moments = detect_moments(
        [
            signal("thin_buffer", 1.0),
            signal("idle_liquidity", 1.0),
            signal("recurring_self_transfer", 1.0, median_amount="200.00", months="3"),
            signal("reverse_savings_transfer", 1.0),
            signal(
                "merchant_concentration",
                1.0,
                yearly_spend="100.00",
                counterparty="X",
                category="transport",
                bookings="7",
            ),
        ]
    )

    for moment in moments:
        assert 0.0 <= moment.confidence <= 1.0, f"{moment.type}: {moment.confidence}"
