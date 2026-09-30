"""What Kate may know about the logged-in customer, and nothing more.

The context is built only from owner-scoped Bank queries, so Kate can never see another customer's
data. It is data minimised (summaries, no IBANs) and sensitive spending (health, religion, politics,
trade union, dating) is neutralised before it can reach the model or a profile.
"""

import json
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.bank import Bank
from app.domain.models import Category, Transaction, User

RECENT_DAYS = 30
MAX_RECENT_TRANSACTIONS = 15
MAX_TEXT = 60

# GDPR art. 9-style categories: never labelled, never profiled, never commented on.
SENSITIVE_KEYWORDS = (
    "apotheek",
    "pharmacie",
    "pharmacy",
    "psycholoog",
    "psychiater",
    "therapeut",
    "ziekenhuis",
    "hospitalisatie",
    "dokter",
    "kliniek",
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
)
NEUTRAL_LABEL = "Overige uitgave"


def is_sensitive(transaction: Transaction) -> bool:
    text = f"{transaction.counterparty} {transaction.description}".lower()
    return any(keyword in text for keyword in SENSITIVE_KEYWORDS)


def clean_text(value: str, limit: int = MAX_TEXT) -> str:
    """Untrusted free text (transaction descriptions): printable, single line, short."""
    printable = "".join(
        ch for ch in value if unicodedata.category(ch)[0] != "C" and ch not in "<>{}`"
    )
    return " ".join(printable.split())[:limit]


@dataclass(frozen=True)
class CustomerContext:
    first_name: str
    persona: str
    today: date
    accounts: list[dict[str, str]]
    spend_last_30_days: dict[str, str]
    recent_transactions: list[dict[str, str]]

    def as_data_block(self) -> str:
        """JSON handed to the model strictly as data, never as instructions."""
        return json.dumps(
            {
                "first_name": self.first_name,
                "persona": self.persona,
                "today": self.today.isoformat(),
                "accounts": self.accounts,
                "spend_last_30_days": self.spend_last_30_days,
                "recent_transactions": self.recent_transactions,
            },
            ensure_ascii=False,
        )


def build_context(bank: Bank, user: User, today: date) -> CustomerContext:
    accounts = bank.accounts_for(user.id)
    transactions = bank.all_transactions_for(user.id)
    since = today - timedelta(days=RECENT_DAYS)
    recent = sorted(
        (t for t in transactions if t.booked_at > since), key=lambda t: t.booked_at, reverse=True
    )

    spend: defaultdict[str, Decimal] = defaultdict(Decimal)
    for t in recent:
        if t.amount < 0:
            key = Category.OTHER.value if is_sensitive(t) else t.category.value
            spend[key] += -t.amount

    return CustomerContext(
        first_name=user.first_name,
        persona=user.persona,
        today=today,
        accounts=[
            {"name": a.name, "type": a.type.value, "balance": f"{a.balance:.2f}"} for a in accounts
        ],
        spend_last_30_days={k: f"{v:.2f}" for k, v in sorted(spend.items())},
        recent_transactions=[_transaction_view(t) for t in recent[:MAX_RECENT_TRANSACTIONS]],
    )


def _transaction_view(t: Transaction) -> dict[str, str]:
    if is_sensitive(t):
        return {
            "date": t.booked_at.isoformat(),
            "counterparty": NEUTRAL_LABEL,
            "amount": f"{t.amount:.2f}",
            "category": Category.OTHER.value,
        }
    return {
        "date": t.booked_at.isoformat(),
        "counterparty": clean_text(t.counterparty),
        "description": clean_text(t.description),
        "amount": f"{t.amount:.2f}",
        "category": t.category.value,
    }
