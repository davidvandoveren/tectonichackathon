"""Detect subscriptions in one customer's own transactions.

Deterministic and cheap (no LLM), so it runs for millions of customers. We only know *that* someone
pays, never whether they use it, so we never guess usage: the customer tells us ("Gebruik je dit
nog?"). Sensitive subscriptions (health, religion, politics, trade union, dating) are counted but
never analysed, labelled or shown.
"""

import hashlib
import itertools
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from app.domain.models import Category, Transaction

MONTHLY_MIN_DAYS = 25
MONTHLY_MAX_DAYS = 35
MAX_AMOUNT = Decimal("100.00")  # above this it is rent/insurance/loan territory, not a subscription
PRICE_INCREASE_MIN = Decimal("0.01")
TRIAL_MAX_AMOUNT = Decimal("1.00")
TRIAL_WORDS = ("proef", "trial", "gratis", "free")
# Shown as "Nieuw gedetecteerd" while the first paid charge is this recent.
NEW_DAYS = 45

# Known services -> comparison group. Two active subscriptions in one group = possible duplicate.
CATALOG: dict[str, str] = {
    "netflix": "streaming",
    "disney": "streaming",
    "streamz": "streaming",
    "prime video": "streaming",
    "hbo": "streaming",
    "vrt max": "streaming",
    "spotify": "muziek",
    "apple music": "muziek",
    "deezer": "muziek",
    "youtube music": "muziek",
    "icloud": "cloudopslag",
    "google one": "cloudopslag",
    "dropbox": "cloudopslag",
    "basic-fit": "fitness",
    "jims": "fitness",
    "telenet": "telecom",
    "proximus": "telecom",
    "orange": "telecom",
    "mobile vikings": "telecom",
}
GROUP_LABELS = {
    "streaming": "streamingdiensten",
    "muziek": "muziekdiensten",
    "cloudopslag": "cloudopslag",
    "fitness": "fitnessabonnementen",
    "telecom": "telecomabonnementen",
}
SUBSCRIPTION_CATEGORIES = {Category.LEISURE, Category.SHOPPING, Category.UTILITIES, Category.OTHER}

SENSITIVE_KEYWORDS = (
    "apotheek",
    "psycholoog",
    "therapeut",
    "ziekenhuis",
    "hospitalisatie",
    "mutualiteit",
    "ziekenfonds",
    "kerk",
    "moskee",
    "synagoge",
    "parochie",
    "partij",
    "vakbond",
    "acv",
    "abvv",
    "aclvb",
    "tinder",
    "bumble",
    "grindr",
    "dating",
    "meditatie",
    "headspace",
)

Flag = Literal["price_increase", "duplicate", "trial_converted"]


@dataclass
class Subscription:
    id: str
    name: str
    group: str | None
    amount: Decimal
    previous_amount: Decimal | None
    frequency: Literal["monthly"]
    first_seen: date
    last_charged: date
    next_expected: date
    flags: list[Flag] = field(default_factory=list)
    duplicate_of: list[str] = field(default_factory=list)
    reason: str = ""
    source: Literal["detected", "manual"] = "detected"
    is_new: bool = False

    @property
    def yearly_cost(self) -> Decimal:
        return self.amount * 12


@dataclass(frozen=True)
class DetectionResult:
    subscriptions: list[Subscription]
    hidden_sensitive: int


def subscription_id(owner_id: str, name: str) -> str:
    """Stable per customer and service; opaque, so it reveals nothing about other customers."""
    digest = hashlib.sha256(f"{owner_id}:{name.lower()}".encode()).hexdigest()[:12]
    return f"sub_{digest}"


def detect(
    owner_id: str,
    transactions: Sequence[Transaction],
    today: date,
    *,
    dismissed: frozenset[str] = frozenset(),
    manual: Sequence[Subscription] = (),
) -> DetectionResult:
    """`dismissed`: ids the customer said are not a subscription. `manual`: ones they added."""
    by_merchant: defaultdict[str, list[Transaction]] = defaultdict(list)
    for t in transactions:
        if t.amount <= 0 and t.category in SUBSCRIPTION_CATEGORIES:
            by_merchant[t.counterparty.strip().lower()].append(t)

    found: list[Subscription] = []
    hidden = 0
    for key, bookings in by_merchant.items():
        bookings.sort(key=lambda t: t.booked_at)
        paid = [t for t in bookings if -t.amount > TRIAL_MAX_AMOUNT]
        if not _is_monthly(paid) or -paid[-1].amount > MAX_AMOUNT:
            continue
        if any(_is_sensitive(t) for t in bookings):
            hidden += 1
            continue
        sub = _build(owner_id, key, bookings, paid, today)
        if sub.id not in dismissed:
            found.append(sub)

    # Copies: flags are computed per request and must not accumulate on the stored objects.
    found.extend(replace(m, flags=[], duplicate_of=[]) for m in manual if m.id not in dismissed)
    _mark_duplicates(found)
    for sub in found:
        sub.reason = _reason(sub)
    found.sort(key=lambda s: (-len(s.flags), -s.amount))
    return DetectionResult(found, hidden)


def _is_monthly(paid: list[Transaction]) -> bool:
    if len(paid) < 2:
        return False
    gaps = [(b.booked_at - a.booked_at).days for a, b in itertools.pairwise(paid)]
    if not all(MONTHLY_MIN_DAYS <= gap <= MONTHLY_MAX_DAYS for gap in gaps):
        return False
    amounts = [-t.amount for t in paid]
    # Allow one price change, but not random amounts (that is shopping, not a subscription).
    return len(set(amounts)) <= 2


def _is_sensitive(t: Transaction) -> bool:
    text = f"{t.counterparty} {t.description}".lower()
    return any(word in text for word in SENSITIVE_KEYWORDS)


def _group_for(key: str) -> str | None:
    # Longest match first, so the most specific service name wins.
    for name in sorted(CATALOG, key=len, reverse=True):
        if name in key:
            return CATALOG[name]
    return None


def _build(
    owner_id: str,
    key: str,
    bookings: list[Transaction],
    paid: list[Transaction],
    today: date,
) -> Subscription:
    name = paid[-1].counterparty.strip()
    amount = -paid[-1].amount
    previous = -paid[-2].amount
    flags: list[Flag] = []
    if amount - previous >= PRICE_INCREASE_MIN:
        flags.append("price_increase")
    trial = [
        t
        for t in bookings
        if -t.amount <= TRIAL_MAX_AMOUNT
        and t.booked_at < paid[0].booked_at
        and any(word in t.description.lower() for word in TRIAL_WORDS)
    ]
    if trial and (today - paid[0].booked_at).days <= 60:
        flags.append("trial_converted")
    next_expected = paid[-1].booked_at + timedelta(days=30)
    while next_expected < today:
        next_expected += timedelta(days=30)
    return Subscription(
        id=subscription_id(owner_id, key),
        name=name,
        group=_group_for(key),
        amount=amount,
        previous_amount=previous if "price_increase" in flags else None,
        frequency="monthly",
        first_seen=bookings[0].booked_at,
        last_charged=paid[-1].booked_at,
        next_expected=next_expected,
        flags=flags,
        is_new=(today - paid[0].booked_at).days <= NEW_DAYS,
    )


def manual_subscription(
    subscription_id: str, name: str, amount: Decimal, next_charge: date, added_on: date
) -> Subscription:
    """A subscription the customer entered themselves (e.g. paid by card elsewhere)."""
    return Subscription(
        id=subscription_id,
        name=name,
        group=_group_for(name.lower()),
        amount=amount,
        previous_amount=None,
        frequency="monthly",
        first_seen=added_on,
        last_charged=added_on,
        next_expected=next_charge,
        source="manual",
    )


def _mark_duplicates(subs: list[Subscription]) -> None:
    by_group: defaultdict[str, list[Subscription]] = defaultdict(list)
    for sub in subs:
        if sub.group:
            by_group[sub.group].append(sub)
    for members in by_group.values():
        if len(members) < 2:
            continue
        for sub in members:
            sub.flags.append("duplicate")
            sub.duplicate_of = [other.name for other in members if other is not sub]


def _euro(amount: Decimal) -> str:
    return f"€ {amount:.2f}".replace(".", ",")


def _reason(sub: Subscription) -> str:
    if sub.source == "manual":
        return f"Je voegde dit abonnement zelf toe op {sub.first_seen:%d/%m}."
    parts = [
        f"We zien sinds {sub.first_seen:%d/%m} elke maand een betaling van {_euro(sub.amount)} "
        f"aan {sub.name}."
    ]
    if "price_increase" in sub.flags and sub.previous_amount is not None:
        parts.append(
            f"De laatste betaling was {_euro(sub.amount - sub.previous_amount)} hoger dan de "
            f"vorige ({_euro(sub.previous_amount)})."
        )
    if "duplicate" in sub.flags and sub.group:
        others = ", ".join(sub.duplicate_of)
        parts.append(f"Je betaalt ook voor {others}: allebei {GROUP_LABELS[sub.group]}.")
    if "trial_converted" in sub.flags:
        parts.append("Dit begon als proefperiode en is nu een betalend abonnement.")
    parts.append("We weten niet of je het gebruikt, alleen dat je ervoor betaalt.")
    return " ".join(parts)
