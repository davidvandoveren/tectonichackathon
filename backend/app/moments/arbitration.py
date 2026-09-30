"""Layer 3 - arbitration.

Layers 1 and 2 answer "what is going on?". This layer answers the harder question the brief
actually asks: *what is worth saying, when, through which channel — and when is the right answer
to say nothing?*

It exists because moments are composed rather than hand-written. A catalogue of signals produces
far more situations than a person would ever author one by one, so without arbitration the
customer receives all of them at once. Silence is therefore a first-class output here, with a
reason attached, not an empty list.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from app.moments.moments import ACT_THRESHOLD, Moment, Urgency

Channel = Literal["feed", "push", "sms", "call", "none"]

#: Channels that reach into the customer's day. Everything else waits to be looked at.
INTERRUPTIVE_CHANNELS: frozenset[Channel] = frozenset(("push", "sms", "call"))

#: At most one interruption per customer per week.
QUOTA_DAYS = 7
#: A dismissed suggestion does not come back for a month.
DISMISSAL_DAYS = 30

#: Urgency bands, kept non-overlapping so a risk can never be outranked by an eager opportunity.
BANDS: Mapping[Urgency, tuple[int, int]] = {
    "risk": (70, 30),
    "obligation": (40, 29),
    "opportunity": (10, 29),
}

#: Suggestions that ask the customer to spend or commit money.
COMMERCIAL_MOMENTS: frozenset[str] = frozenset(("deal_match", "idle_savings", "card_package_gap"))
#: Suggestions that hand the customer money back. These are never held back for commercial
#: reasons — that asymmetry is the whole point.
SAVING_MOMENTS: frozenset[str] = frozenset(("savings_habit_automatable", "card_package_waste"))

SILENCE_REASONS: Mapping[str, str] = {
    "low_confidence": (
        "We zien hier iets, maar we weten het nog niet zeker genoeg om je ermee lastig te "
        "vallen. We houden het in de gaten."
    ),
    "cashflow_first": (
        "Je saldo staat krap. Voorstellen die je geld kosten houden we daarom even voor ons; "
        "eerst je rekening."
    ),
    "dismissed": ("Je gaf aan dit niet te willen zien. We vragen het pas over een maand opnieuw."),
}


@dataclass(frozen=True)
class Decision:
    moment: Moment
    channel: Channel
    urgency: int


@dataclass(frozen=True)
class Silence:
    moment_type: str
    reason_code: str
    reason: str


@dataclass(frozen=True)
class Verdict:
    decisions: tuple[Decision, ...] = ()
    silenced: tuple[Silence, ...] = ()

    @property
    def interrupted(self) -> bool:
        return any(d.channel in INTERRUPTIVE_CHANNELS for d in self.decisions)


def urgency_score(moment: Moment) -> int:
    base, span = BANDS[moment.urgency]
    return base + round(span * moment.confidence)


def _preferred_channel(moment: Moment) -> Channel:
    if moment.urgency == "risk":
        if moment.confidence >= 0.98:
            return "call"
        if moment.confidence >= 0.85:
            return "sms"
        return "push"
    if moment.urgency == "obligation" and moment.confidence >= 0.8:
        return "push"
    return "feed"


def _silence(moment_type: str, code: str) -> Silence:
    return Silence(moment_type=moment_type, reason_code=code, reason=SILENCE_REASONS[code])


def arbitrate(
    moments: Sequence[Moment],
    *,
    today: date,
    dismissed: Mapping[str, date] | None = None,
    last_interruption: date | None = None,
) -> Verdict:
    """Rank, suppress and route. Returns what Kate says *and* what she deliberately withheld."""
    dismissals = dismissed or {}
    has_risk = any(m.urgency == "risk" and m.confidence >= ACT_THRESHOLD for m in moments)

    speaking: list[Moment] = []
    silenced: list[Silence] = []
    for moment in moments:
        if moment.confidence < ACT_THRESHOLD:
            silenced.append(_silence(moment.type, "low_confidence"))
            continue
        # A warning about the rent is never muted by a dismissed nudge.
        dismissed_on = dismissals.get(moment.type)
        if (
            moment.urgency != "risk"
            and dismissed_on is not None
            and (today - dismissed_on).days < DISMISSAL_DAYS
        ):
            silenced.append(_silence(moment.type, "dismissed"))
            continue
        if has_risk and moment.type in COMMERCIAL_MOMENTS:
            silenced.append(_silence(moment.type, "cashflow_first"))
            continue
        speaking.append(moment)

    speaking.sort(
        key=lambda m: (
            -urgency_score(m),
            -m.confidence,
            -(m.value_eur_per_year or Decimal(0)),
        )
    )

    quota_spent = last_interruption is not None and (today - last_interruption).days <= QUOTA_DAYS
    decisions: list[Decision] = []
    for moment in speaking:
        channel = _preferred_channel(moment)
        if channel in INTERRUPTIVE_CHANNELS and quota_spent:
            channel = "feed"  # still shown, just not shouted
        elif channel in INTERRUPTIVE_CHANNELS:
            quota_spent = True
        decisions.append(Decision(moment=moment, channel=channel, urgency=urgency_score(moment)))

    return Verdict(decisions=tuple(decisions), silenced=tuple(silenced))
