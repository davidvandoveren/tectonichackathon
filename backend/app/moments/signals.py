"""Layer 1 - signal extraction.

A signal is *evidence*, never a verdict: a typed observation about this customer's own history
with a strength in (0, 1] and a plain-language explanation. Moments are built by combining
signals (layer 2), which is why no single extractor here decides anything on its own.

Every extractor declares a consent `domain`. Consent is applied *before* extraction, so a signal
the customer switched off is never computed, let alone acted on.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from itertools import pairwise
from typing import Literal

from app.domain.models import AccountType, Category, Transaction
from app.kate.context import is_sensitive
from app.moments.ledger import Ledger, euro, median_of, percentile

Domain = Literal["income", "spending", "balances", "products"]

ALL_DOMAINS: frozenset[Domain] = frozenset(("income", "spending", "balances", "products"))

#: A payment is "late" only after a few days of grace; banks that nag on day one get muted.
INCOME_GRACE_DAYS = 3
#: An outflow this many times the category's 90th percentile is out of character.
OUTLIER_FACTOR = Decimal(4)
#: A rental deposit in Belgium is customarily two or three months' rent.
DEPOSIT_MULTIPLES = (Decimal(2), Decimal(3))
DEPOSIT_TOLERANCE = Decimal("0.10")
#: Savings worth more than a year of spending are doing nothing for the customer.
IDLE_MONTHS = Decimal(12)
CONCENTRATION_MIN_BOOKINGS = 6
CONCENTRATION_MIN_SHARE = Decimal("0.40")
#: Public transport has no Kate Deal, so being loyal to it is not a deal opportunity (#35).
PUBLIC_TRANSPORT = re.compile(r"\b(de lijn|nmbs|sncb|stib|mivb|tec)\b", re.IGNORECASE)
SELF_TRANSFER_MIN_MONTHS = 3
#: Three monthly transfers span up to 92 days, so a 90-day window would always miss the oldest.
SELF_TRANSFER_WINDOW_DAYS = 100


@dataclass(frozen=True)
class Signal:
    type: str
    domain: Domain
    strength: float
    observed_at: date
    evidence: str
    meta: Mapping[str, str] = field(default_factory=dict)


def clamp(value: float) -> float:
    """Keep a strength inside (0, 1]; 0 would mean "no evidence", which is not a signal."""
    return max(0.01, min(1.0, value))


def _money(amount: Decimal) -> str:
    return f"{amount:.2f}"


# --- self-transfers ----------------------------------------------------------------------------


@dataclass(frozen=True)
class SelfTransfer:
    booked_at: date
    amount: Decimal
    to_savings: bool


def self_transfers(led: Ledger) -> list[SelfTransfer]:
    """Transfers between the customer's own accounts, found by matching debit to credit.

    Deliberately not detected from the counterparty name: a payment to someone else who happens
    to be called "spaarrekening" must not count, and a transfer to your own savings must count
    whatever you typed in the description.
    """
    current = led.account_ids_of(AccountType.CURRENT)
    savings = led.account_ids_of(AccountType.SAVINGS)
    credits = [t for t in led.transactions if t.category == Category.TRANSFER and t.amount > 0]
    matched: list[SelfTransfer] = []
    for debit in (t for t in led.transactions if t.category == Category.TRANSFER and t.amount < 0):
        amount = -debit.amount
        credit = next(
            (
                c
                for c in credits
                if c.booked_at == debit.booked_at
                and c.amount == amount
                and c.account_id != debit.account_id
            ),
            None,
        )
        if credit is None:
            continue
        if debit.account_id in current and credit.account_id in savings:
            matched.append(SelfTransfer(debit.booked_at, amount, to_savings=True))
        elif debit.account_id in savings and credit.account_id in current:
            matched.append(SelfTransfer(debit.booked_at, amount, to_savings=False))
    return matched


# --- income ------------------------------------------------------------------------------------


def new_income_payer(led: Ledger) -> Signal | None:
    known = {t.counterparty for t in led.income(led.older())}
    fresh = [t for t in led.income(led.recent()) if t.counterparty not in known]
    if not fresh:
        return None
    arrival = max(fresh, key=lambda t: t.amount)
    baseline = median_of([t.amount for t in led.income(led.older())])
    ratio = float(arrival.amount / (baseline * 2)) if baseline > 0 else 1.0
    return Signal(
        type="new_income_payer",
        domain="income",
        strength=clamp(0.5 + 0.5 * min(1.0, ratio)),
        observed_at=arrival.booked_at,
        evidence=(
            f"Op {arrival.booked_at:%d/%m} kwam er {euro(arrival.amount)} binnen van "
            f"{arrival.counterparty}, een betaler die we niet eerder zagen."
        ),
        meta={
            "counterparty": arrival.counterparty,
            "amount": _money(arrival.amount),
        },
    )


def income_step_up(led: Ledger) -> Signal | None:
    baseline = median_of([t.amount for t in led.income(led.older())])
    recent = led.income(led.recent())
    if baseline <= 0 or not recent:
        return None
    arrival = max(recent, key=lambda t: t.amount)
    ratio = arrival.amount / baseline
    if ratio < 2:
        return None
    return Signal(
        type="income_step_up",
        domain="income",
        strength=clamp(float((ratio - 1) / 3)),
        observed_at=arrival.booked_at,
        evidence=(
            f"Je inkomsten gingen van ongeveer {euro(baseline)} naar {euro(arrival.amount)}, "
            f"ruim {ratio:.1f} keer zoveel."
        ),
        meta={"baseline": _money(baseline), "amount": _money(arrival.amount)},
    )


def _monthly_payers(led: Ledger) -> dict[str, list[Transaction]]:
    grouped: dict[str, list[Transaction]] = {}
    for transaction in led.income(led.transactions):
        grouped.setdefault(transaction.counterparty, []).append(transaction)
    return {name: sorted(items, key=lambda t: t.booked_at) for name, items in grouped.items()}


def expected_income_missing(led: Ledger) -> Signal | None:
    """The strongest signal in the engine: money the customer counts on did not arrive."""
    worst: tuple[int, str, Transaction] | None = None
    for name, payments in _monthly_payers(led).items():
        if len(payments) < 3:
            continue  # too little history to know a rhythm
        gaps = [Decimal((b.booked_at - a.booked_at).days) for a, b in pairwise(payments)]
        cadence = int(median_of(gaps))
        if not 20 <= cadence <= 40:
            continue  # not a monthly payer
        overdue = (led.today - payments[-1].booked_at).days - cadence
        if overdue <= INCOME_GRACE_DAYS:
            continue
        if worst is None or overdue > worst[0]:
            worst = (overdue, name, payments[-1])
    if worst is None:
        return None
    overdue, name, last = worst
    return Signal(
        type="expected_income_missing",
        domain="income",
        strength=clamp(overdue / 14),
        observed_at=led.today,
        evidence=(
            f"{name} betaalde je elke maand, maar de storting is nu {overdue} dagen te laat "
            f"(laatste keer {last.booked_at:%d/%m})."
        ),
        meta={
            "counterparty": name,
            "days_overdue": str(overdue),
            "amount": _money(last.amount),
        },
    )


# --- balances ----------------------------------------------------------------------------------


def thin_buffer(led: Ledger) -> Signal | None:
    balance = led.balance_of(AccountType.CURRENT)
    housing = led.outflows(led.recent(60), Category.HOUSING)
    if not housing:
        return None
    obligation = max(-t.amount for t in housing)
    if balance >= obligation:
        return None
    return Signal(
        type="thin_buffer",
        domain="balances",
        strength=clamp(1.0 - float(balance / obligation) if obligation > 0 else 1.0),
        observed_at=led.today,
        evidence=(
            f"Je zichtrekening staat op {euro(balance)}, minder dan je grootste woonkost van "
            f"de afgelopen twee maanden ({euro(obligation)})."
        ),
        meta={"balance": _money(balance), "obligation": _money(obligation)},
    )


def idle_liquidity(led: Ledger) -> Signal | None:
    savings = led.balance_of(AccountType.SAVINGS)
    monthly = led.monthly_spend()
    if monthly <= 0 or savings < monthly * IDLE_MONTHS:
        return None
    months = savings / monthly
    return Signal(
        type="idle_liquidity",
        domain="balances",
        strength=clamp(float(months / 24)),
        observed_at=led.today,
        evidence=(
            f"Je spaarsaldo ({euro(savings)}) dekt ongeveer {int(months)} maanden van je "
            f"huidige uitgaven ({euro(monthly)} per maand)."
        ),
        meta={"savings": _money(savings), "months": str(int(months))},
    )


# --- spending shape ----------------------------------------------------------------------------


def large_outflow_outlier(led: Ledger) -> Signal | None:
    best: tuple[Decimal, Transaction, Decimal] | None = None
    for category in led.spend_categories():
        history = [-t.amount for t in led.outflows(led.older(), category)]
        if len(history) < 3:
            continue
        threshold = percentile(history, 0.9) * OUTLIER_FACTOR
        if threshold <= 0:
            continue
        for transaction in led.outflows(led.recent(), category):
            amount = -transaction.amount
            if amount >= threshold and (best is None or amount > best[0]):
                best = (amount, transaction, percentile(history, 0.9))
    if best is None:
        return None
    amount, transaction, reference = best
    return Signal(
        type="large_outflow_outlier",
        domain="spending",
        strength=clamp(float(amount / reference) / 10),
        observed_at=transaction.booked_at,
        evidence=(
            f"Je betaalde {euro(amount)} bij {transaction.counterparty}, veel meer dan je "
            f"gewoonlijk aan {transaction.category.value} uitgeeft."
        ),
        meta={
            "counterparty": transaction.counterparty,
            "amount": _money(amount),
            "category": transaction.category.value,
        },
    )


def deposit_like_outflow(led: Ledger) -> Signal | None:
    rents = [-t.amount for t in led.outflows(led.older(), Category.HOUSING)]
    if len(rents) < 2:
        return None
    rent = median_of(rents)
    if rent <= 0:
        return None
    for transaction in led.outflows(led.recent(), Category.HOUSING):
        amount = -transaction.amount
        for multiple in DEPOSIT_MULTIPLES:
            expected = rent * multiple
            deviation = abs(amount - expected) / expected
            if deviation > DEPOSIT_TOLERANCE:
                continue
            return Signal(
                type="deposit_like_outflow",
                domain="spending",
                strength=clamp(0.6 + 0.4 * (1 - float(deviation / DEPOSIT_TOLERANCE))),
                observed_at=transaction.booked_at,
                evidence=(
                    f"Er ging {euro(amount)} weg aan wonen, ongeveer {int(multiple)} keer je "
                    f"maandhuur van {euro(rent)} — dat lijkt op een huurwaarborg."
                ),
                meta={
                    "amount": _money(amount),
                    "rent": _money(rent),
                    "multiple": str(int(multiple)),
                },
            )
    return None


def category_spend_spike(led: Ledger) -> Signal | None:
    best: tuple[Decimal, Category, Decimal, Decimal] | None = None
    for category in led.spend_categories():
        recent = led.spend(led.outflows(led.recent(), category))
        prior = led.spend(led.outflows(led.between(30, 90), category))
        if prior <= 0:
            continue
        baseline = prior / 2  # two months of history -> a monthly average
        if recent < baseline * 2:
            continue
        excess = recent - baseline
        if best is None or excess > best[0]:
            best = (excess, category, recent, baseline)
    if best is None:
        return None
    _, category, recent, baseline = best
    return Signal(
        type="category_spend_spike",
        domain="spending",
        strength=clamp(float(recent / (baseline * 4))),
        observed_at=led.today,
        evidence=(
            f"Je gaf de afgelopen maand {euro(recent)} uit aan {category.value}, tegenover "
            f"gemiddeld {euro(baseline)} in de twee maanden daarvoor."
        ),
        meta={
            "category": category.value,
            "recent": _money(recent),
            "baseline": _money(baseline),
        },
    )


def merchant_concentration(led: Ledger) -> Signal | None:
    window = led.recent(90)
    best: tuple[int, str, Category, Decimal, Decimal] | None = None
    for category in led.spend_categories():
        outflows = led.outflows(window, category)
        total = sum((-t.amount for t in outflows), Decimal(0))
        if total <= 0:
            continue
        counts: dict[str, list[Decimal]] = {}
        for transaction in outflows:
            if PUBLIC_TRANSPORT.search(transaction.counterparty):
                continue
            counts.setdefault(transaction.counterparty, []).append(-transaction.amount)
        for name, amounts in counts.items():
            share = sum(amounts, Decimal(0)) / total
            if len(amounts) < CONCENTRATION_MIN_BOOKINGS or share < CONCENTRATION_MIN_SHARE:
                continue
            if best is None or len(amounts) > best[0]:
                best = (len(amounts), name, category, sum(amounts, Decimal(0)), share)
    if best is None:
        return None
    bookings, name, category, spent, share = best
    yearly = spent * 4  # a 90-day window, extrapolated
    return Signal(
        type="merchant_concentration",
        domain="spending",
        strength=clamp(0.5 + float(share) / 2),
        observed_at=led.today,
        evidence=(
            f"Je betaalde {bookings} keer bij {name} in de laatste drie maanden, "
            f"{int(share * 100)}% van alles wat je aan {category.value} uitgeeft."
        ),
        meta={
            "counterparty": name,
            "category": category.value,
            "bookings": str(bookings),
            "yearly_spend": _money(yearly),
        },
    )


def recurring_self_transfer(led: Ledger) -> Signal | None:
    deposits = [
        s
        for s in self_transfers(led)
        if s.to_savings and (led.today - s.booked_at).days <= SELF_TRANSFER_WINDOW_DAYS
    ]
    months = {(s.booked_at.year, s.booked_at.month) for s in deposits}
    if len(months) < SELF_TRANSFER_MIN_MONTHS:
        return None
    amounts = [s.amount for s in deposits]
    typical = median_of(amounts)
    steady = max(amounts) == min(amounts)
    return Signal(
        type="recurring_self_transfer",
        domain="spending",
        strength=clamp(min(1.0, len(months) / 4) * (1.0 if steady else 0.8)),
        observed_at=max(s.booked_at for s in deposits),
        evidence=(
            f"Je zette de laatste {len(months)} maanden zelf geld op je spaarrekening, "
            f"meestal {euro(typical)} per keer."
        ),
        meta={
            "median_amount": _money(typical),
            "months": str(len(months)),
            "day_of_month": str(median_of([Decimal(s.booked_at.day) for s in deposits])),
        },
    )


def reverse_savings_transfer(led: Ledger) -> Signal | None:
    withdrawals = [s for s in self_transfers(led) if not s.to_savings]
    if not withdrawals:
        return None
    latest = max(withdrawals, key=lambda s: s.booked_at)
    return Signal(
        type="reverse_savings_transfer",
        domain="spending",
        strength=1.0,
        observed_at=latest.booked_at,
        evidence=(
            f"Op {latest.booked_at:%d/%m} haalde je {euro(latest.amount)} terug van je "
            f"spaarrekening — dat geld had je blijkbaar nodig."
        ),
        meta={"amount": _money(latest.amount)},
    )


Extractor = Callable[[Ledger], Signal | None]

EXTRACTORS: tuple[Extractor, ...] = (
    expected_income_missing,
    new_income_payer,
    income_step_up,
    thin_buffer,
    idle_liquidity,
    large_outflow_outlier,
    deposit_like_outflow,
    category_spend_spike,
    merchant_concentration,
    recurring_self_transfer,
    reverse_savings_transfer,
)

_DOMAIN_OF: Mapping[str, Domain] = {
    "expected_income_missing": "income",
    "new_income_payer": "income",
    "income_step_up": "income",
    "thin_buffer": "balances",
    "idle_liquidity": "balances",
    "large_outflow_outlier": "spending",
    "deposit_like_outflow": "spending",
    "category_spend_spike": "spending",
    "merchant_concentration": "spending",
    "recurring_self_transfer": "spending",
    "reverse_savings_transfer": "spending",
}


def extract_signals(
    led: Ledger,
    rules: Sequence[Extractor] = EXTRACTORS,
    consent: frozenset[Domain] | set[Domain] | None = None,
) -> list[Signal]:
    """Run every extractor the customer has consented to. Silence is a valid answer.

    Sensitive transactions (health, religion, politics, unions, dating) are removed before any
    extractor runs, so no signal can be built on them — not merely hidden afterwards (#35).
    """
    allowed = ALL_DOMAINS if consent is None else frozenset(consent)
    led = replace(led, transactions=[t for t in led.transactions if not is_sensitive(t)])
    found: list[Signal] = []
    for rule in rules:
        if _DOMAIN_OF[rule.__name__] not in allowed:
            continue
        signal = rule(led)
        if signal is not None:
            found.append(signal)
    return found
