"""What each customer holds beyond accounts: card packages, Kate Deals, standing orders, goals.

In memory and owner-scoped, like `Bank`. Swap for a real product system later without touching
the skills that use it.
"""

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

# Per customer; card packages and deals are bounded by their fixed catalogues already.
MAX_STANDING_ORDERS = 10
MAX_GOALS = 20


@dataclass(frozen=True)
class StandingOrder:
    amount: Decimal
    day: int
    to_account_id: str


@dataclass(frozen=True)
class SavingsGoal:
    name: str
    target: Decimal
    monthly: Decimal | None


@dataclass
class CustomerHoldings:
    card_packages: set[str] = field(default_factory=set)
    active_deals: set[str] = field(default_factory=set)
    standing_orders: list[StandingOrder] = field(default_factory=list)
    goals: list[SavingsGoal] = field(default_factory=list)


class Holdings:
    def __init__(self) -> None:
        self._by_owner: defaultdict[str, CustomerHoldings] = defaultdict(CustomerHoldings)
        self.lock = threading.Lock()

    def of(self, owner_id: str) -> CustomerHoldings:
        return self._by_owner[owner_id]
