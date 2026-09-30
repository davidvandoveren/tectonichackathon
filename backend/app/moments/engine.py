"""The engine's single entry point.

`run` is a pure function of (this customer's data, today, this customer's choices). It reads
nothing global, so the same call can be made for one customer in a request or for a million in
a batch job — which is exactly what makes the scale story in the design doc true rather than
aspirational.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from app.domain.bank import Bank
from app.domain.models import User
from app.moments.arbitration import Silence, Verdict, arbitrate
from app.moments.composition import ComposedItem, compose
from app.moments.ledger import Ledger
from app.moments.moments import detect_moments
from app.moments.signals import Domain, extract_signals


@dataclass(frozen=True)
class Experience:
    """What Kate says, and what she deliberately did not say."""

    items: tuple[ComposedItem, ...]
    silenced: tuple[Silence, ...]


def build_ledger(bank: Bank, user: User, today: date) -> Ledger:
    """Owner-scoped by construction: both queries take the authenticated user's id."""
    return Ledger(
        user_id=user.id,
        accounts=bank.accounts_for(user.id),
        transactions=bank.all_transactions_for(user.id),
        today=today,
    )


def run(
    bank: Bank,
    user: User,
    today: date,
    *,
    consent: set[Domain] | frozenset[Domain] | None = None,
    dismissed: Mapping[str, date] | None = None,
    last_interruption: date | None = None,
) -> Verdict:
    led = build_ledger(bank, user, today)
    signals = extract_signals(led, consent=consent)
    moments = detect_moments(signals)
    return arbitrate(moments, today=today, dismissed=dismissed, last_interruption=last_interruption)


def experience(
    bank: Bank,
    user: User,
    today: date,
    *,
    consent: set[Domain] | frozenset[Domain] | None = None,
    dismissed: Mapping[str, date] | None = None,
    last_interruption: date | None = None,
) -> Experience:
    verdict = run(
        bank,
        user,
        today,
        consent=consent,
        dismissed=dismissed,
        last_interruption=last_interruption,
    )
    return Experience(
        items=tuple(compose(decision) for decision in verdict.decisions),
        silenced=verdict.silenced,
    )


def moment_types(verdict: Verdict) -> Sequence[str]:
    return [decision.moment.type for decision in verdict.decisions]
