"""Layer 2 - moment detection.

A moment is a *recipe* over signals: weighted evidence for, weighted evidence against, and a
confidence that falls out of the arithmetic. Nothing here is hand-authored per situation, which
is the whole point — adding a signal to the catalogue changes every recipe that references it,
so the set of recognisable situations grows combinatorially instead of one `if` at a time.

Two thresholds matter:

* `NOTICE_THRESHOLD` - below this we saw nothing worth remembering.
* `ACT_THRESHOLD` - below this we noticed something but are not sure enough to speak. Layer 3
  turns that into deliberate, explainable silence rather than a guess.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from app.moments.signals import Signal

Urgency = Literal["risk", "obligation", "opportunity"]

NOTICE_THRESHOLD = 0.35
ACT_THRESHOLD = 0.60

#: Conservative placeholder for a Kate Deals cashback rate. Used only to rank and to show an
#: order of magnitude; the real rate comes from the deal itself.
DEAL_CASHBACK_RATE = Decimal("0.02")


@dataclass(frozen=True)
class Moment:
    type: str
    confidence: float
    urgency: Urgency
    signals: tuple[Signal, ...]
    value_eur_per_year: Decimal | None = None
    meta: Mapping[str, str] = field(default_factory=dict)

    @property
    def reason(self) -> str:
        """The "Waarom zie ik dit?" text, assembled from the evidence that produced it.

        Built rather than written, so it can never drift from what was actually observed.
        """
        return " ".join(s.evidence for s in self.signals)


@dataclass(frozen=True)
class Recipe:
    type: str
    urgency: Urgency
    weights: Mapping[str, float]
    counters: Mapping[str, float] = field(default_factory=dict)
    #: Signal types that must all be present, however strong the rest of the evidence is.
    requires: tuple[str, ...] = ()


RECIPES: tuple[Recipe, ...] = (
    Recipe(
        type="cashflow_risk",
        urgency="risk",
        weights={"thin_buffer": 1.0},
    ),
    Recipe(
        type="income_missing",
        urgency="risk",
        weights={"expected_income_missing": 1.0},
    ),
    Recipe(
        type="first_salary",
        urgency="opportunity",
        # A new payer alone is a refund, a friend or a bonus. Only together with a jump in
        # income does it mean someone started working.
        weights={"new_income_payer": 0.5, "income_step_up": 0.5},
        requires=("new_income_payer", "income_step_up"),
    ),
    Recipe(
        type="moving_house",
        urgency="obligation",
        # No merchant list: a move is the shape of the spending, so it survives Leen Bakker,
        # a different mover and a customer in Wallonia.
        weights={
            "large_outflow_outlier": 0.3,
            "deposit_like_outflow": 0.4,
            "category_spend_spike": 0.3,
        },
    ),
    Recipe(
        type="idle_savings",
        urgency="opportunity",
        weights={"idle_liquidity": 1.0},
        counters={"thin_buffer": 0.8},
    ),
    Recipe(
        type="savings_habit_automatable",
        urgency="opportunity",
        weights={"recurring_self_transfer": 1.0},
        # Someone who has pulled money back out of savings needs that liquidity; a standing
        # order would harm them. A thin buffer says the same thing more weakly.
        counters={"reverse_savings_transfer": 1.0, "thin_buffer": 0.5},
    ),
    Recipe(
        type="deal_match",
        urgency="opportunity",
        weights={"merchant_concentration": 1.0},
    ),
)


def _confidence(recipe: Recipe, by_type: Mapping[str, Signal]) -> float:
    total = sum(recipe.weights.values())
    if total <= 0:
        return 0.0
    earned = sum(
        weight * by_type[name].strength
        for name, weight in recipe.weights.items()
        if name in by_type
    )
    against = sum(
        penalty * by_type[name].strength
        for name, penalty in recipe.counters.items()
        if name in by_type
    )
    return max(0.0, min(1.0, earned / total - against))


def _meta_for(recipe: Recipe, supporting: Sequence[Signal]) -> dict[str, str]:
    """Lift the numbers a suggestion needs out of the signals that produced it."""
    merged: dict[str, str] = {}
    for signal in supporting:
        merged.update(signal.meta)
    if recipe.type == "savings_habit_automatable" and "median_amount" in merged:
        merged["amount"] = merged["median_amount"]
    return merged


def _value_for(recipe: Recipe, meta: Mapping[str, str]) -> Decimal | None:
    """Estimated euros per year, used to rank suggestions against each other."""
    if recipe.type == "savings_habit_automatable" and "amount" in meta:
        return Decimal(meta["amount"]) * 12
    if recipe.type == "deal_match" and "yearly_spend" in meta:
        return (Decimal(meta["yearly_spend"]) * DEAL_CASHBACK_RATE).quantize(Decimal("0.01"))
    return None


def detect_moments(signals: Sequence[Signal], recipes: Sequence[Recipe] = RECIPES) -> list[Moment]:
    """Combine signals into moments. Returns everything worth *noticing*; layer 3 decides
    what is worth saying."""
    by_type = {s.type: s for s in signals}
    found: list[Moment] = []
    for recipe in recipes:
        if any(name not in by_type for name in recipe.requires):
            continue
        supporting = tuple(by_type[name] for name in recipe.weights if name in by_type)
        if not supporting:
            continue
        confidence = _confidence(recipe, by_type)
        if confidence < NOTICE_THRESHOLD:
            continue
        meta = _meta_for(recipe, supporting)
        found.append(
            Moment(
                type=recipe.type,
                confidence=confidence,
                urgency=recipe.urgency,
                signals=supporting,
                value_eur_per_year=_value_for(recipe, meta),
                meta=meta,
            )
        )
    return found
