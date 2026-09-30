"""The demo time machine.

Moves the app's clock forward and projects the customer's *own* recurring income into the
window, so Kate reacts to something that really would have happened rather than to a scripted
fixture. The rhythm is derived from the ledger, not from the seed file, so it keeps working when
someone adds a persona.

The interesting scenario is `salary_missing`: skip the projection and the payment the customer
counts on simply never arrives, which is exactly the situation the engine should escalate for.

Demo only. It lives behind the admin gate and never runs in a customer request.
"""

import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import Literal

from app.domain.bank import Bank
from app.domain.models import Category, Transaction, User
from app.moments.engine import build_ledger
from app.moments.ledger import median_of

Scenario = Literal["none", "salary_paid", "salary_missing"]

MIN_OCCURRENCES = 3
MIN_CADENCE_DAYS = 20
MAX_CADENCE_DAYS = 40
#: Defensive bound; a 365-day jump at a 20-day cadence cannot exceed this.
MAX_INJECTIONS = 32


@dataclass(frozen=True)
class Recurrence:
    counterparty: str
    account_id: str
    description: str
    amount: Decimal
    last_paid: date
    cadence_days: int


def monthly_income(bank: Bank, user: User, today: date) -> list[Recurrence]:
    """Income the customer receives on a roughly monthly rhythm, derived from their history."""
    led = build_ledger(bank, user, today)
    grouped: dict[str, list[Transaction]] = {}
    for transaction in led.income(led.transactions):
        grouped.setdefault(transaction.counterparty, []).append(transaction)

    found: list[Recurrence] = []
    for name, items in grouped.items():
        payments = sorted(items, key=lambda t: t.booked_at)
        if len(payments) < MIN_OCCURRENCES:
            continue
        gaps = [Decimal((b.booked_at - a.booked_at).days) for a, b in pairwise(payments)]
        cadence = int(median_of(gaps))
        if not MIN_CADENCE_DAYS <= cadence <= MAX_CADENCE_DAYS:
            continue
        latest = payments[-1]
        found.append(
            Recurrence(
                counterparty=name,
                account_id=latest.account_id,
                description=latest.description,
                amount=latest.amount,
                last_paid=latest.booked_at,
                cadence_days=cadence,
            )
        )
    return found


def project(bank: Bank, user: User, today: date, days: int, scenario: Scenario) -> int:
    """Book the recurring income that falls in `(today, today + days]`. Returns how many.

    `salary_missing` deliberately books nothing: that is the whole scenario.
    """
    if scenario != "salary_paid":
        return 0
    horizon = today + timedelta(days=days)
    accounts = {a.id: a for a in bank.accounts_for(user.id)}
    booked = 0
    for recurrence in monthly_income(bank, user, today):
        due = recurrence.last_paid + timedelta(days=recurrence.cadence_days)
        while due <= horizon and booked < MAX_INJECTIONS:
            if due > today:
                bank.add_transaction(
                    Transaction(
                        id=f"t_tm_{secrets.token_hex(6)}",
                        account_id=recurrence.account_id,
                        booked_at=due,
                        description=recurrence.description,
                        counterparty=recurrence.counterparty,
                        amount=recurrence.amount,
                        category=Category.INCOME,
                    )
                )
                account = accounts.get(recurrence.account_id)
                if account is not None:
                    account.balance += recurrence.amount
                booked += 1
            due += timedelta(days=recurrence.cadence_days)
    return booked


def scenarios() -> Sequence[str]:
    return ("none", "salary_paid", "salary_missing")
