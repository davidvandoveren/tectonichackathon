""" "Voor jou" insights: the personalization hook of the PoC.

Each rule looks at one customer's own signals and either returns a single, explainable insight or
stays silent. Every insight carries a plain-language `reason` ("Waarom zie ik dit?"). Add new
rules to `RULES`; swap or extend them with an ML/LLM-backed engine later without touching the API.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.models import Account, AccountType, Category, Insight, Transaction

RECENT_DAYS = 30
MOVING_KEYWORDS = ("verhuis", "ikea", "waarborg")


@dataclass(frozen=True)
class CustomerSignals:
    user_id: str
    accounts: Sequence[Account]
    transactions: Sequence[Transaction]
    today: date

    def recent(self, days: int = RECENT_DAYS) -> list[Transaction]:
        since = self.today - timedelta(days=days)
        return [t for t in self.transactions if t.booked_at > since]

    def older(self, days: int = RECENT_DAYS) -> list[Transaction]:
        since = self.today - timedelta(days=days)
        return [t for t in self.transactions if t.booked_at <= since]

    def balance_of(self, account_type: AccountType) -> Decimal:
        return sum((a.balance for a in self.accounts if a.type == account_type), Decimal(0))

    def monthly_spend(self) -> Decimal:
        spent = sum((-t.amount for t in self.recent() if t.amount < 0), Decimal(0))
        return spent


Rule = Callable[[CustomerSignals], Insight | None]


def _euro(amount: Decimal) -> str:
    return f"€ {amount:,.2f}".replace(",", " ").replace(".", ",")


def first_salary(signals: CustomerSignals) -> Insight | None:
    known_payers = {t.counterparty for t in signals.older() if t.category == Category.INCOME}
    new_income = [
        t
        for t in signals.recent()
        if t.category == Category.INCOME
        and t.counterparty not in known_payers
        and t.amount >= Decimal("1000")
    ]
    if not new_income:
        return None
    salary = max(new_income, key=lambda t: t.amount)
    return Insight(
        id=f"i_first_salary_{signals.user_id}",
        kind="moment",
        title="Proficiat met je eerste loon!",
        body="Zet elke maand automatisch een klein deel opzij, dan groeit je buffer vanzelf.",
        cta_label="Start met sparen",
        cta_target="/transfer",
        reason=(
            f"We zagen op {salary.booked_at:%d/%m} een nieuwe storting van {salary.counterparty} "
            f"({_euro(salary.amount)}) die groter is dan je vroegere inkomsten."
        ),
    )


def moving_house(signals: CustomerSignals) -> Insight | None:
    hits = [
        t
        for t in signals.recent()
        if t.amount < 0 and any(k in t.counterparty.lower() for k in MOVING_KEYWORDS)
    ]
    if len(hits) < 2:
        return None
    names = ", ".join(sorted({t.counterparty for t in hits}))
    return Insight(
        id=f"i_moving_{signals.user_id}",
        kind="moment",
        title="Ga je verhuizen?",
        body="Denk aan je woonverzekering, je adreswijziging en energiecontracten. We helpen je.",
        cta_label="Mijn gegevens",
        cta_target="/profile",
        reason=f"Recente uitgaven bij {names} wijzen op een verhuis.",
    )


def idle_savings(signals: CustomerSignals) -> Insight | None:
    savings = signals.balance_of(AccountType.SAVINGS)
    monthly = signals.monthly_spend()
    if monthly <= 0 or savings < monthly * 12:
        return None
    return Insight(
        id=f"i_idle_savings_{signals.user_id}",
        kind="guidance",
        title="Je spaargeld kan meer voor je doen",
        body="Bespreek vrijblijvend met een adviseur wat past bij jouw plannen en risicoprofiel.",
        cta_label="Bekijk mijn rekeningen",
        cta_target="/",
        reason=(
            f"Je spaarsaldo ({_euro(savings)}) is meer dan 12 keer je uitgaven "
            f"van de afgelopen 30 dagen ({_euro(monthly)})."
        ),
    )


def low_buffer(signals: CustomerSignals) -> Insight | None:
    current = signals.balance_of(AccountType.CURRENT)
    rent = [t for t in signals.recent() if t.category == Category.HOUSING and t.amount < 0]
    if not rent:
        return None
    upcoming = max(-t.amount for t in rent)
    if current >= upcoming:
        return None
    return Insight(
        id=f"i_low_buffer_{signals.user_id}",
        kind="alert",
        title="Let op je saldo",
        body="Je zichtrekening is lager dan je grootste woonkost van vorige maand.",
        cta_label="Geld overschrijven",
        cta_target="/transfer",
        reason=f"Saldo {_euro(current)} tegenover een woonkost van {_euro(upcoming)}.",
    )


RULES: tuple[Rule, ...] = (low_buffer, first_salary, moving_house, idle_savings)


def insights_for(signals: CustomerSignals, rules: Sequence[Rule] = RULES) -> list[Insight]:
    """Apply every rule; silence (an empty list) is a valid, respectful answer."""
    return [insight for rule in rules if (insight := rule(signals)) is not None]
