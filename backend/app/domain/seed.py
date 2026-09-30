"""Synthetic demo population. No real customer data, ever."""

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.bank import Bank
from app.domain.iban import make_be_iban
from app.domain.models import Account, AccountType, Category, Transaction, User
from app.security.passwords import hash_password

HISTORY_DAYS = 90


@dataclass(frozen=True)
class Recurring:
    """A monthly booking on a given day of the month."""

    day: int
    description: str
    counterparty: str
    amount: str
    category: Category


@dataclass(frozen=True)
class OneOff:
    """A single booking a number of days before today (the "life event" signals)."""

    days_ago: int
    description: str
    counterparty: str
    amount: str
    category: Category


@dataclass(frozen=True)
class Persona:
    username: str
    first_name: str
    last_name: str
    persona: str
    accounts: tuple[tuple[str, AccountType, str], ...]
    recurring: tuple[Recurring, ...]
    daily_spend: tuple[tuple[str, Category, float, float], ...]
    one_offs: tuple[OneOff, ...] = ()


PERSONAS = (
    Persona(
        username="emma",
        first_name="Emma",
        last_name="Peeters",
        persona="Studente, 21, Leuven, net afgestudeerd",
        accounts=(
            ("Zichtrekening", AccountType.CURRENT, "612.40"),
            ("Spaarrekening", AccountType.SAVINGS, "250.00"),
        ),
        recurring=(
            Recurring(1, "Huur kot", "Kotbaas Leuven", "-420.00", Category.HOUSING),
            Recurring(15, "Studentenjob", "Delhaize Leuven", "310.00", Category.INCOME),
            Recurring(8, "Spotify", "Spotify", "-11.99", Category.LEISURE),
        ),
        daily_spend=(
            ("Colruyt", Category.GROCERIES, 8, 45),
            ("De Lijn", Category.TRANSPORT, 2.5, 25),
            ("Café Het Moment", Category.LEISURE, 4, 30),
        ),
        one_offs=(OneOff(5, "Salaris", "Proximus NV", "1985.00", Category.INCOME),),
    ),
    Persona(
        username="jan",
        first_name="Jan",
        last_name="Maes",
        persona="Bediende, 34, Gent, verhuist binnenkort",
        accounts=(
            ("Zichtrekening", AccountType.CURRENT, "2840.15"),
            ("Spaarrekening", AccountType.SAVINGS, "18500.00"),
            ("KBC Mastercard", AccountType.CREDIT_CARD, "-312.80"),
        ),
        recurring=(
            Recurring(1, "Huur appartement", "Immo Gent", "-950.00", Category.HOUSING),
            Recurring(26, "Salaris", "Acme Logistics BV", "3120.00", Category.INCOME),
            Recurring(5, "Energie", "Luminus", "-142.00", Category.UTILITIES),
            Recurring(10, "Internet & mobiel", "Telenet", "-79.00", Category.UTILITIES),
        ),
        daily_spend=(
            ("Delhaize", Category.GROCERIES, 12, 80),
            ("NMBS", Category.TRANSPORT, 6, 30),
            ("Bol.com", Category.SHOPPING, 10, 90),
        ),
        one_offs=(
            OneOff(9, "Voorschot verhuis", "Verhuisfirma Snel", "-680.00", Category.HOUSING),
            OneOff(6, "Meubelen", "IKEA Gent", "-1240.50", Category.SHOPPING),
            OneOff(3, "Huurwaarborg", "Waarborgrekening", "-1900.00", Category.HOUSING),
        ),
    ),
    Persona(
        username="marie",
        first_name="Marie",
        last_name="Dubois",
        persona="Gepensioneerd, 67, Namen",
        accounts=(
            ("Zichtrekening", AccountType.CURRENT, "3120.60"),
            ("Spaarrekening", AccountType.SAVINGS, "64250.00"),
        ),
        recurring=(
            Recurring(20, "Pensioen", "Federale Pensioendienst", "1960.00", Category.INCOME),
            Recurring(3, "Energie", "Engie", "-118.00", Category.UTILITIES),
            Recurring(
                12, "Hospitalisatieverzekering", "KBC Verzekeringen", "-64.00", Category.OTHER
            ),
        ),
        daily_spend=(
            ("Carrefour Namur", Category.GROCERIES, 10, 60),
            ("Apotheek", Category.OTHER, 8, 35),
        ),
    ),
)


def seed_bank(bank: Bank, demo_password: str, today: date) -> None:
    rng = random.Random(42)  # noqa: S311 - reproducible synthetic data, not security-relevant
    account_number = 7_350_000_000
    for persona in PERSONAS:
        password_hash, salt = hash_password(demo_password)
        user = User(
            id=f"u_{persona.username}",
            username=persona.username,
            first_name=persona.first_name,
            last_name=persona.last_name,
            persona=persona.persona,
            password_hash=password_hash,
            password_salt=salt,
        )
        bank.add_user(user)
        for index, (name, account_type, balance) in enumerate(persona.accounts, start=1):
            account_number += 1
            bank.add_account(
                Account(
                    id=f"a_{persona.username}_{index}",
                    owner_id=user.id,
                    name=name,
                    type=account_type,
                    iban=make_be_iban(account_number),
                    balance=Decimal(balance),
                )
            )
        _seed_history(bank, persona, f"a_{persona.username}_1", today, rng)


def _seed_history(
    bank: Bank, persona: Persona, account_id: str, today: date, rng: random.Random
) -> None:
    counter = 0

    def book(
        day: date, description: str, counterparty: str, amount: Decimal, cat: Category
    ) -> None:
        nonlocal counter
        counter += 1
        bank.add_transaction(
            Transaction(
                id=f"t_{persona.username}_{counter:04d}",
                account_id=account_id,
                booked_at=day,
                description=description,
                counterparty=counterparty,
                amount=amount,
                category=cat,
            )
        )

    for days_ago in range(HISTORY_DAYS, -1, -1):
        day = today - timedelta(days=days_ago)
        for item in persona.recurring:
            if day.day == item.day:
                book(day, item.description, item.counterparty, Decimal(item.amount), item.category)
        for counterparty, category, low, high in persona.daily_spend:
            if rng.random() < 0.3:
                amount = Decimal(str(round(rng.uniform(low, high), 2)))
                book(day, counterparty, counterparty, -amount, category)

    for event in persona.one_offs:
        day = today - timedelta(days=event.days_ago)
        book(day, event.description, event.counterparty, Decimal(event.amount), event.category)
