"""Synthetic subscription bookings for the demo personas.

Kept out of `domain/seed.py` on purpose (that file is owned by the Moments Engine work): this module
only *adds* bookings to personas that exist, after the base seed ran. Synthetic data only.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.bank import Bank
from app.domain.models import Category, Transaction


@dataclass(frozen=True)
class Plan:
    """A monthly subscription: `months` charges, the last one `last_days_ago` days before today."""

    account_id: str
    counterparty: str
    description: str
    amounts: tuple[str, ...]  # oldest first; a change of amount is a price increase
    last_days_ago: int
    category: Category = Category.LEISURE
    trial_first: bool = False


PLANS = (
    # Emma: two streaming services with the same kind of offer, one of them a converted trial.
    Plan("a_emma_1", "Netflix", "Netflix abonnement", ("13.49",) * 3, 4),
    Plan("a_emma_1", "Disney+", "Disney+ abonnement", ("10.99",) * 2, 9, trial_first=True),
    # Jan: a price increase, a gym and cloud storage, plus a trade union fee (sensitive: hidden).
    Plan("a_jan_1", "Netflix", "Netflix abonnement", ("13.49", "13.49", "15.99"), 2),
    Plan("a_jan_1", "Basic-Fit", "Basic-Fit lidmaatschap", ("29.99",) * 3, 12),
    Plan("a_jan_1", "iCloud", "iCloud+ 200 GB", ("2.99",) * 3, 18, Category.OTHER),
    Plan("a_jan_1", "ACV Vakbond", "Lidgeld", ("18.50",) * 3, 6, Category.OTHER),
    # Marie: a newspaper subscription.
    Plan("a_marie_1", "De Standaard", "Digitaal abonnement", ("24.99",) * 3, 11),
)


def book_subscriptions(bank: Bank, today: date) -> None:
    accounts = {a.id for user in bank.list_users() for a in bank.accounts_for(user.id)}
    counter = 0
    for plan in PLANS:
        if plan.account_id not in accounts:
            continue
        charges = [Decimal(a) for a in plan.amounts]
        for index, amount in enumerate(charges):
            months_before_last = len(charges) - 1 - index
            day = today - timedelta(days=plan.last_days_ago + 30 * months_before_last)
            counter += 1
            bank.add_transaction(_booking(plan, counter, day, -amount, plan.description))
        if plan.trial_first:
            first = today - timedelta(days=plan.last_days_ago + 30 * len(charges))
            counter += 1
            bank.add_transaction(
                _booking(plan, counter, first, Decimal("0.00"), f"{plan.counterparty} proefperiode")
            )


def _booking(plan: Plan, counter: int, day: date, amount: Decimal, text: str) -> Transaction:
    return Transaction(
        id=f"t_sub_{counter:03d}",
        account_id=plan.account_id,
        booked_at=day,
        description=text,
        counterparty=plan.counterparty,
        amount=amount,
        category=plan.category,
    )
