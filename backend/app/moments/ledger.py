"""One customer's own data, and nothing from anyone else.

`Ledger` is the only input the engine ever sees. It is built from owner-scoped `Bank` queries, so
a signal extractor physically cannot reach another customer's transactions.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.models import Account, AccountType, Category, Transaction

#: Moving money to your own savings is not spending, and neither is being paid.
SPEND_CATEGORIES: frozenset[Category] = frozenset(
    c for c in Category if c not in {Category.INCOME, Category.TRANSFER, Category.SAVINGS}
)


def euro(amount: Decimal) -> str:
    """Belgian formatting: space for thousands, comma for decimals."""
    integer, _, decimals = f"{amount:,.2f}".partition(".")
    return f"€ {integer.replace(',', ' ')},{decimals}"


def percentile(values: Sequence[Decimal], fraction: float) -> Decimal:
    """Nearest-rank percentile. Small samples are the norm here, so no interpolation."""
    if not values:
        return Decimal(0)
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def median_of(values: Sequence[Decimal]) -> Decimal:
    if not values:
        return Decimal(0)
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


@dataclass(frozen=True)
class Ledger:
    user_id: str
    accounts: Sequence[Account]
    transactions: Sequence[Transaction]
    today: date

    # --- time windows --------------------------------------------------------------------------
    def days_ago(self, transaction: Transaction) -> int:
        return (self.today - transaction.booked_at).days

    def recent(self, days: int = 30) -> list[Transaction]:
        return [t for t in self.transactions if self.days_ago(t) <= days]

    def older(self, days: int = 30) -> list[Transaction]:
        return [t for t in self.transactions if self.days_ago(t) > days]

    def between(self, newer_than: int, older_than: int) -> list[Transaction]:
        """Transactions in `(newer_than, older_than]` days ago."""
        return [t for t in self.transactions if newer_than < self.days_ago(t) <= older_than]

    # --- accounts ------------------------------------------------------------------------------
    def account_ids_of(self, account_type: AccountType) -> set[str]:
        return {a.id for a in self.accounts if a.type == account_type}

    def balance_of(self, account_type: AccountType) -> Decimal:
        return sum((a.balance for a in self.accounts if a.type == account_type), Decimal(0))

    # --- money ---------------------------------------------------------------------------------
    @staticmethod
    def income(transactions: Iterable[Transaction]) -> list[Transaction]:
        return [t for t in transactions if t.category == Category.INCOME and t.amount > 0]

    @staticmethod
    def outflows(
        transactions: Iterable[Transaction], category: Category | None = None
    ) -> list[Transaction]:
        return [
            t
            for t in transactions
            if t.amount < 0
            and t.category in SPEND_CATEGORIES
            and (category is None or t.category == category)
        ]

    def spend(self, transactions: Iterable[Transaction]) -> Decimal:
        return sum((-t.amount for t in self.outflows(transactions)), Decimal(0))

    def monthly_spend(self) -> Decimal:
        return self.spend(self.recent())

    def spend_categories(self) -> set[Category]:
        return {t.category for t in self.outflows(self.transactions)}
