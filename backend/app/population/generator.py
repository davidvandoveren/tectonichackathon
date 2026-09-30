"""A reproducible synthetic population of bank customers. No real data, no real names.

Each customer gets their *own* tiny `Bank`, because Kate's engine is a pure function of one
customer's data: that is exactly how it would run as a batch job over 2.3M customers, and it keeps
10.000 customers fast (no shared store to scan).

The archetype mix is an illustrative assumption for the demo, not KBC data.
"""

import random
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.bank import Bank
from app.domain.models import Account, AccountType, Category, Transaction, User

HISTORY_DAYS = 120


@dataclass(frozen=True)
class SyntheticCustomer:
    archetype: str
    bank: Bank
    user: User


class _Book:
    """Collects one customer's bookings."""

    def __init__(self, bank: Bank, today: date) -> None:
        self.bank = bank
        self.today = today
        self.count = 0

    def add(self, account_id: str, days_ago: int, who: str, amount: float, cat: Category) -> None:
        if days_ago < 0 or days_ago > HISTORY_DAYS:
            return
        self.count += 1
        self.bank.add_transaction(
            Transaction(
                id=f"t{self.count}",
                account_id=account_id,
                booked_at=self.today - timedelta(days=days_ago),
                description=who,
                counterparty=who,
                amount=Decimal(str(round(amount, 2))),
                category=cat,
            )
        )

    def monthly(
        self, account_id: str, day_offset: int, who: str, amount: float, cat: Category
    ) -> None:
        for days_ago in range(day_offset, HISTORY_DAYS + 1, 30):
            self.add(account_id, days_ago, who, amount, cat)

    def self_transfer(self, days_ago: int, amount: float, to_savings: bool = True) -> None:
        source, target = ("c", "s") if to_savings else ("s", "c")
        self.add(source, days_ago, "Eigen rekening", -amount, Category.TRANSFER)
        self.add(target, days_ago, "Eigen rekening", amount, Category.TRANSFER)


def _customer(index: int, archetype: str, current: float, savings: float) -> tuple[Bank, User]:
    bank = Bank()
    user = User(
        id=f"p_{index:05d}",
        username=f"klant{index:05d}",
        first_name="Klant",
        last_name=f"{index:05d}",
        persona=archetype,
        password_hash=b"",
        password_salt=b"",
    )
    bank.add_user(user)
    for account_id, name, kind, balance in (
        ("c", "Zichtrekening", AccountType.CURRENT, current),
        ("s", "Spaarrekening", AccountType.SAVINGS, savings),
    ):
        bank.add_account(
            Account(account_id, user.id, name, kind, "", Decimal(str(round(balance, 2))))
        )
    return bank, user


def _daily_life(book: _Book, rng: random.Random, scale: float = 1.0) -> None:
    shops = ("Colruyt", "Delhaize", "Aldi", "Lidl", "Carrefour")
    for days_ago in range(HISTORY_DAYS + 1):
        if rng.random() < 0.35:
            book.add(
                "c", days_ago, rng.choice(shops), -rng.uniform(8, 70) * scale, Category.GROCERIES
            )
        if rng.random() < 0.12:
            book.add(
                "c",
                days_ago,
                rng.choice(("Bol.com", "Zalando", "Fnac", "Action")),
                -rng.uniform(10, 90) * scale,
                Category.SHOPPING,
            )
        if rng.random() < 0.10:
            book.add("c", days_ago, rng.choice(TRANSPORT), -rng.uniform(3, 60), Category.TRANSPORT)


def _worker(book: _Book, rng: random.Random, salary: float, rent: float) -> None:
    book.monthly("c", rng.randint(0, 29), rng.choice(EMPLOYERS), salary, Category.INCOME)
    book.monthly("c", rng.randint(0, 29), "Huur / lening", -rent, Category.HOUSING)
    book.monthly(
        "c",
        rng.randint(0, 29),
        rng.choice(("Luminus", "Engie", "TotalEnergies")),
        -rng.uniform(90, 180),
        Category.UTILITIES,
    )
    book.monthly(
        "c",
        rng.randint(0, 29),
        rng.choice(("Telenet", "Proximus", "Orange")),
        -rng.uniform(40, 95),
        Category.UTILITIES,
    )


TRANSPORT = (
    "NMBS",
    "De Lijn",
    "Q8",
    "TotalEnergies",
    "Esso",
    "Shell",
    "Lukoil",
    "Cambio",
    "Parking Interparking",
    "Blue-bike",
)
EMPLOYERS = (
    "Acme Logistics BV",
    "Zorgnet VZW",
    "Stad Gent",
    "Retail Group NV",
    "Techno SA",
    "Bouwbedrijf NV",
    "Onderwijs Vlaanderen",
    "Consult BV",
)


def _steady(i: int, rng: random.Random, today: date) -> tuple[Bank, User]:
    salary, rent = rng.uniform(1900, 4200), rng.uniform(650, 1300)
    bank, user = _customer(i, "steady", rng.uniform(rent * 1.3, 6000), rng.uniform(1000, 20000))
    book = _Book(bank, today)
    _worker(book, rng, salary, rent)
    _daily_life(book, rng)
    return bank, user


def _family(i: int, rng: random.Random, today: date) -> tuple[Bank, User]:
    rent = rng.uniform(900, 1500)
    bank, user = _customer(i, "family", rng.uniform(rent * 1.2, 7000), rng.uniform(2000, 30000))
    book = _Book(bank, today)
    _worker(book, rng, rng.uniform(1800, 3500), rent)
    book.monthly(
        "c",
        rng.randint(0, 29),
        rng.choice(EMPLOYERS[::-1]),
        rng.uniform(1500, 3000),
        Category.INCOME,
    )
    book.monthly("c", rng.randint(0, 29), "Kinderbijslag Groeipakket", 180, Category.INCOME)
    _daily_life(book, rng, scale=1.6)
    return bank, user


def _first_job(i: int, rng: random.Random, today: date) -> tuple[Bank, User]:
    rent = rng.uniform(380, 550)
    bank, user = _customer(i, "first_job", rng.uniform(rent * 1.5, 2500), rng.uniform(100, 1500))
    book = _Book(bank, today)
    book.monthly("c", rng.randint(0, 29), "Studentenjob", rng.uniform(250, 600), Category.INCOME)
    book.add(
        "c", rng.randint(2, 25), rng.choice(EMPLOYERS), rng.uniform(1700, 2500), Category.INCOME
    )
    book.monthly("c", rng.randint(0, 29), "Kot / studio", -rent, Category.HOUSING)
    _daily_life(book, rng, scale=0.6)
    return bank, user


def _salary_missing(i: int, rng: random.Random, today: date) -> tuple[Bank, User]:
    rent = rng.uniform(700, 1100)
    bank, user = _customer(i, "salary_missing", rng.uniform(100, rent * 1.5), rng.uniform(0, 3000))
    book = _Book(bank, today)
    book.monthly(
        "c", rng.randint(42, 50), rng.choice(EMPLOYERS), rng.uniform(1700, 2800), Category.INCOME
    )
    book.monthly("c", rng.randint(0, 29), "Huur / lening", -rent, Category.HOUSING)
    _daily_life(book, rng, scale=0.8)
    return bank, user


def _tight(i: int, rng: random.Random, today: date) -> tuple[Bank, User]:
    rent = rng.uniform(750, 1000)
    bank, user = _customer(i, "tight_budget", rng.uniform(20, rent * 0.9), rng.uniform(0, 400))
    book = _Book(bank, today)
    _worker(book, rng, rng.uniform(1450, 1900), rent)
    _daily_life(book, rng, scale=0.7)
    return bank, user


def _mover(i: int, rng: random.Random, today: date) -> tuple[Bank, User]:
    rent = rng.uniform(800, 1200)
    bank, user = _customer(i, "moving", rng.uniform(2000, 6000), rng.uniform(3000, 20000))
    book = _Book(bank, today)
    _worker(book, rng, rng.uniform(2400, 4000), rent)
    _daily_life(book, rng)
    book.add("c", rng.randint(2, 20), "Huurwaarborg", -rent * rng.choice((2, 3)), Category.HOUSING)
    book.add(
        "c",
        rng.randint(2, 20),
        rng.choice(("IKEA", "Leen Bakker", "JYSK")),
        -rng.uniform(900, 2600),
        Category.SHOPPING,
    )
    for _ in range(rng.randint(3, 6)):
        book.add(
            "c",
            rng.randint(1, 25),
            rng.choice(("Brico", "Gamma", "Hubo")),
            -rng.uniform(60, 250),
            Category.SHOPPING,
        )
    return bank, user


def _saver(i: int, rng: random.Random, today: date) -> tuple[Bank, User]:
    rent = rng.uniform(650, 1100)
    bank, user = _customer(i, "saver", rng.uniform(rent * 1.5, 5000), rng.uniform(2000, 15000))
    book = _Book(bank, today)
    _worker(book, rng, rng.uniform(2300, 4000), rent)
    _daily_life(book, rng)
    amount = rng.choice((100, 150, 200, 250, 300))
    for month in range(4):
        book.self_transfer(rng.randint(3, 8) + 30 * month, amount + rng.choice((0, 0, 25, 50)))
    if rng.random() < 0.3:  # needed the money back once: a standing order would hurt them
        book.self_transfer(rng.randint(10, 80), rng.uniform(200, 800), to_savings=False)
    return bank, user


def _retiree(i: int, rng: random.Random, today: date) -> tuple[Bank, User]:
    bank, user = _customer(i, "retiree", rng.uniform(1500, 6000), rng.uniform(15000, 150000))
    book = _Book(bank, today)
    book.monthly(
        "c", rng.randint(0, 29), "Federale Pensioendienst", rng.uniform(1500, 2400), Category.INCOME
    )
    book.monthly(
        "c",
        rng.randint(0, 29),
        rng.choice(("Engie", "Luminus")),
        -rng.uniform(90, 160),
        Category.UTILITIES,
    )
    _daily_life(book, rng, scale=0.8)
    return bank, user


def _commuter(i: int, rng: random.Random, today: date) -> tuple[Bank, User]:
    bank, user = _steady(i, rng, today)
    book = _Book(bank, today)
    book.count = 10_000  # keep ids unique next to the steady bookings
    station = rng.choice(("Q8 Wetteren", "TotalEnergies Aalst", "Esso Mechelen"))
    for week in range(12):
        book.add(
            "c", 2 + 7 * week + rng.randint(0, 2), station, -rng.uniform(45, 80), Category.TRANSPORT
        )
    return bank, _relabel(bank, user, "commuter")


def _relabel(bank: Bank, user: User, archetype: str) -> User:
    relabelled = User(**{**user.__dict__, "persona": archetype})
    bank.add_user(relabelled)
    return relabelled


Builder = Callable[[int, random.Random, date], tuple[Bank, User]]

#: Share of each archetype in the synthetic population (illustrative, sums to 1).
MIX: tuple[tuple[str, float, Builder], ...] = (
    ("steady", 0.34, _steady),
    ("family", 0.16, _family),
    ("retiree", 0.14, _retiree),
    ("saver", 0.10, _saver),
    ("tight_budget", 0.08, _tight),
    ("commuter", 0.06, _commuter),
    ("first_job", 0.05, _first_job),
    ("moving", 0.04, _mover),
    ("salary_missing", 0.03, _salary_missing),
)

ARCHETYPE_LABELS = {
    "steady": "Vaste job, geen bijzonderheden",
    "family": "Gezin met twee inkomens",
    "retiree": "Gepensioneerd",
    "saver": "Spaart met de hand",
    "tight_budget": "Krap budget",
    "commuter": "Pendelaar met de auto",
    "first_job": "Eerste job",
    "moving": "Verhuist",
    "salary_missing": "Loon blijft uit",
}


def generate(size: int, today: date, seed: int = 42) -> Iterator[SyntheticCustomer]:
    """Yield `size` customers, one at a time, so memory stays flat even for large runs."""
    rng = random.Random(seed)  # noqa: S311 - reproducible synthetic data, not security-relevant
    names = [name for name, _, _ in MIX]
    weights = [weight for _, weight, _ in MIX]
    builders = {name: builder for name, _, builder in MIX}
    for index in range(size):
        archetype = rng.choices(names, weights)[0]
        bank, user = builders[archetype](index, rng, today)
        yield SyntheticCustomer(archetype=archetype, bank=bank, user=user)
