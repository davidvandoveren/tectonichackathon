"""Layer 3 - arbitration: what to say, when, through which channel, and when to stay silent.

This is the layer that makes combinatorial moments safe. Once situations are composed instead of
hand-written, something has to decide what is worth interrupting someone for — otherwise the
customer gets spam with a confidence score attached.
"""

from datetime import date, timedelta
from decimal import Decimal

from app.moments.arbitration import (
    INTERRUPTIVE_CHANNELS,
    QUOTA_DAYS,
    arbitrate,
)
from app.moments.moments import Moment, Urgency
from app.moments.signals import Signal

TODAY = date(2026, 9, 30)


def moment(
    moment_type: str,
    urgency: Urgency,
    confidence: float = 1.0,
    value: str | None = None,
) -> Moment:
    return Moment(
        type=moment_type,
        confidence=confidence,
        urgency=urgency,
        signals=(
            Signal(
                type=f"s_{moment_type}",
                domain="spending",
                strength=confidence,
                observed_at=TODAY,
                evidence=f"evidence for {moment_type}",
            ),
        ),
        value_eur_per_year=Decimal(value) if value else None,
    )


def channels(verdict) -> dict[str, str]:  # type: ignore[no-untyped-def]
    return {d.moment.type: d.channel for d in verdict.decisions}


def silenced_codes(verdict) -> dict[str, str]:  # type: ignore[no-untyped-def]
    return {s.moment_type: s.reason_code for s in verdict.silenced}


# --- urgency score -----------------------------------------------------------------------------


def test_urgency_score_is_a_number_between_0_and_100() -> None:
    verdict = arbitrate([moment("cashflow_risk", "risk")], today=TODAY)

    score = verdict.decisions[0].urgency
    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_a_risk_always_outranks_an_opportunity_however_confident() -> None:
    # A money-saving opportunity, so this tests ranking only: a commercial one would be
    # suppressed by the risk and never reach the ranking at all (tested separately below).
    verdict = arbitrate(
        [
            moment("savings_habit_automatable", "opportunity", confidence=1.0),
            moment("cashflow_risk", "risk", confidence=0.65),
        ],
        today=TODAY,
    )

    assert verdict.decisions[0].moment.type == "cashflow_risk"
    assert verdict.decisions[0].urgency > verdict.decisions[1].urgency


# --- channel choice ----------------------------------------------------------------------------


def test_a_confident_risk_is_escalated_off_the_feed() -> None:
    verdict = arbitrate([moment("income_missing", "risk", confidence=1.0)], today=TODAY)

    assert channels(verdict)["income_missing"] in INTERRUPTIVE_CHANNELS


def test_an_opportunity_waits_quietly_in_the_feed() -> None:
    verdict = arbitrate([moment("deal_match", "opportunity", confidence=1.0)], today=TODAY)

    assert channels(verdict)["deal_match"] == "feed"


# --- the quota ---------------------------------------------------------------------------------


def test_only_one_moment_may_interrupt_the_customer() -> None:
    verdict = arbitrate(
        [
            moment("income_missing", "risk", confidence=1.0),
            moment("cashflow_risk", "risk", confidence=0.95),
        ],
        today=TODAY,
    )

    interruptions = [c for c in channels(verdict).values() if c in INTERRUPTIVE_CHANNELS]
    assert len(interruptions) == 1, "the second risk must fall back to the feed, not shout too"
    assert channels(verdict)["cashflow_risk"] == "feed"


def test_a_recent_interruption_keeps_everything_in_the_feed() -> None:
    verdict = arbitrate(
        [moment("income_missing", "risk", confidence=1.0)],
        today=TODAY,
        last_interruption=TODAY - timedelta(days=QUOTA_DAYS - 1),
    )

    assert channels(verdict)["income_missing"] == "feed"
    assert silenced_codes(verdict) == {}, "the moment is still shown, just not pushed"


def test_an_old_interruption_no_longer_holds_anything_back() -> None:
    verdict = arbitrate(
        [moment("income_missing", "risk", confidence=1.0)],
        today=TODAY,
        last_interruption=TODAY - timedelta(days=QUOTA_DAYS + 1),
    )

    assert channels(verdict)["income_missing"] in INTERRUPTIVE_CHANNELS


# --- suppression: cashflow first ---------------------------------------------------------------


def test_a_commercial_suggestion_is_silenced_while_the_customer_is_short() -> None:
    verdict = arbitrate(
        [
            moment("cashflow_risk", "risk", confidence=0.9),
            moment("deal_match", "opportunity", confidence=1.0, value="62.40"),
        ],
        today=TODAY,
    )

    assert "deal_match" not in channels(verdict)
    assert silenced_codes(verdict)["deal_match"] == "cashflow_first"


def test_a_suggestion_that_saves_money_is_never_silenced_by_a_thin_buffer() -> None:
    # The asymmetry that matters: we stop selling to someone who is short, but we never stop
    # telling them how to keep more of their own money.
    verdict = arbitrate(
        [
            moment("cashflow_risk", "risk", confidence=0.9),
            moment("savings_habit_automatable", "opportunity", confidence=0.8, value="2400.00"),
            moment("deal_match", "opportunity", confidence=1.0, value="62.40"),
        ],
        today=TODAY,
    )

    assert "savings_habit_automatable" in channels(verdict)
    assert "deal_match" in silenced_codes(verdict)


# --- suppression: not sure enough --------------------------------------------------------------


def test_a_noticed_but_unconfident_moment_is_deliberately_silent() -> None:
    verdict = arbitrate([moment("moving_house", "obligation", confidence=0.45)], today=TODAY)

    assert channels(verdict) == {}
    assert silenced_codes(verdict)["moving_house"] == "low_confidence"


def test_silence_is_always_explained_in_plain_language() -> None:
    verdict = arbitrate([moment("moving_house", "obligation", confidence=0.45)], today=TODAY)

    assert verdict.silenced[0].reason.strip()
    assert "moving_house" not in verdict.silenced[0].reason, "explain it, do not leak internals"


# --- suppression: the customer said no ---------------------------------------------------------


def test_a_dismissed_moment_stays_away_for_a_month() -> None:
    verdict = arbitrate(
        [moment("deal_match", "opportunity", confidence=1.0)],
        today=TODAY,
        dismissed={"deal_match": TODAY - timedelta(days=5)},
    )

    assert silenced_codes(verdict)["deal_match"] == "dismissed"


def test_a_dismissal_expires() -> None:
    verdict = arbitrate(
        [moment("deal_match", "opportunity", confidence=1.0)],
        today=TODAY,
        dismissed={"deal_match": TODAY - timedelta(days=60)},
    )

    assert "deal_match" in channels(verdict)


def test_a_dismissal_never_suppresses_a_risk() -> None:
    # Dismissing a nudge must not mute a warning that the rent cannot be paid.
    verdict = arbitrate(
        [moment("cashflow_risk", "risk", confidence=0.9)],
        today=TODAY,
        dismissed={"cashflow_risk": TODAY - timedelta(days=1)},
    )

    assert "cashflow_risk" in channels(verdict)


# --- nothing to say ---------------------------------------------------------------------------


def test_no_moments_means_no_decisions_and_no_silence() -> None:
    verdict = arbitrate([], today=TODAY)

    assert verdict.decisions == ()
    assert verdict.silenced == ()


def test_ranking_uses_value_when_urgency_and_confidence_tie() -> None:
    verdict = arbitrate(
        [
            moment("deal_match", "opportunity", confidence=0.9, value="62.40"),
            moment("savings_habit_automatable", "opportunity", confidence=0.9, value="2400.00"),
        ],
        today=TODAY,
    )

    assert verdict.decisions[0].moment.type == "savings_habit_automatable"
