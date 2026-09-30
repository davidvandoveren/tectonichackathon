"""Recurring payments ("abonnementen") derived from a customer's own transactions.

Nothing here is an external lookup: a subscription is simply a counterparty that debits the
account once a month. Same idea as `services.insights` - plain rules, explainable, no ML, so
every field on the page can be traced back to bookings the customer can see for themselves.
"""

import threading
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal

from app.domain.models import Category, Transaction
from app.services.insights import CustomerSignals

MIN_MONTHS = 3

# Recurring payments we deliberately never put on the page. Guardrail from docs/plan.md: a
# hospitalisation policy or a pharmacy plan says something about someone's health, and Kate has
# no business nudging anyone about it.
SENSITIVE_CATEGORIES = frozenset({Category.OTHER})

# Recurring, but not a subscription anyone can cancel - asking "still using this?" about rent
# would be absurd.
FIXED_COST_CATEGORIES = frozenset({Category.HOUSING})

# Categories where a second subscription really is redundant (two music or video services).
# Deliberately NOT utilities: energy and internet are both UTILITIES yet complement each other,
# and telling someone their electricity duplicates their broadband would be plain wrong.
SUBSTITUTABLE_CATEGORIES = frozenset({Category.LEISURE})


@dataclass(frozen=True)
class Subscription:
    """One recurring debit, as shown on the Abonnementen page."""

    id: str
    name: str
    amount: Decimal
    frequency: str
    price_change: Decimal | None
    duplicate_of: str | None
    category: Category


def detect_subscriptions(signals: CustomerSignals) -> list[Subscription]:
    """Every monthly debit worth showing, cheapest-first duplicates already marked."""
    by_counterparty: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in signals.transactions:
        if transaction.amount < 0 and _is_showable(transaction.category):
            by_counterparty[transaction.counterparty].append(transaction)

    found = [
        _to_subscription(counterparty, bookings)
        for counterparty, bookings in by_counterparty.items()
        if _is_monthly(bookings)
    ]
    return sorted(_mark_duplicates(found), key=lambda s: s.name)


def _is_showable(category: Category) -> bool:
    return category not in SENSITIVE_CATEGORIES and category not in FIXED_COST_CATEGORIES


def _is_monthly(bookings: Sequence[Transaction]) -> bool:
    """Once a month, for at least MIN_MONTHS different months - not a daily shop."""
    months = {(t.booked_at.year, t.booked_at.month) for t in bookings}
    return len(months) >= MIN_MONTHS and len(bookings) <= len(months)


def _to_subscription(counterparty: str, bookings: Sequence[Transaction]) -> Subscription:
    ordered = sorted(bookings, key=lambda t: t.booked_at)
    first, latest = -ordered[0].amount, -ordered[-1].amount
    return Subscription(
        id=f"s_{ordered[-1].account_id}_{counterparty.lower().replace(' ', '_')}",
        name=counterparty,
        amount=latest,
        frequency="monthly",
        # Only a rise is worth telling someone about; a drop needs no action.
        price_change=latest - first if latest > first else None,
        duplicate_of=None,
        category=ordered[-1].category,
    )


def _mark_duplicates(subscriptions: Sequence[Subscription]) -> list[Subscription]:
    """Two subscriptions in one category overlap; point the pricier ones at the cheapest.

    Category is a coarse stand-in for "these do the same job" - we have no brand catalogue here.
    The customer still decides: the page only asks whether they still use it.
    """
    per_category: dict[Category, list[Subscription]] = defaultdict(list)
    marked: list[Subscription] = []
    for subscription in subscriptions:
        if subscription.category in SUBSTITUTABLE_CATEGORIES:
            per_category[subscription.category].append(subscription)
        else:
            marked.append(subscription)

    for group in per_category.values():
        cheapest, *pricier = sorted(group, key=lambda s: (s.amount, s.name))
        marked.append(cheapest)
        marked.extend(replace(s, duplicate_of=cheapest.id) for s in pricier)
    return marked


@dataclass(frozen=True)
class SubscriptionFeedback:
    """What the customer answered about one subscription. Nobody answers by default."""

    still_used: bool | None = None
    remind_to_cancel: bool = False


NO_FEEDBACK = SubscriptionFeedback()


class FeedbackStore:
    """In-memory answers, keyed by owner *and* subscription, so one customer can never read or
    overwrite another's. Same trade-off as `Bank`: swap for Firestore later, keep the interface.
    """

    def __init__(self) -> None:
        self._answers: dict[tuple[str, str], SubscriptionFeedback] = {}
        self._lock = threading.Lock()

    def get(self, owner_id: str, subscription_id: str) -> SubscriptionFeedback:
        return self._answers.get((owner_id, subscription_id), NO_FEEDBACK)

    def set(self, owner_id: str, subscription_id: str, feedback: SubscriptionFeedback) -> None:
        with self._lock:
            self._answers[(owner_id, subscription_id)] = feedback
