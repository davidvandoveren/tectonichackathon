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
class Weekly:
    """A booking on the same weekday every week (0 = Monday), with a varying amount."""

    weekday: int
    counterparty: str
    low: float
    high: float
    category: Category


@dataclass(frozen=True)
class SavingsHabit:
    """A manual transfer to the customer's own savings, a few days after payday.

    Booked as two legs (current -> savings) like a real internal transfer, so the engine finds it
    by matching debit to credit rather than by reading the description. The day wanders by up to
    `jitter_days`, which is what makes it a *habit* rather than a standing order.
    """

    day: int
    jitter_days: int
    amount: str
    description: str
    #: How many of the most recent months carry the transfer. More than fits in 90 days on
    #: purpose, so at least three always land inside the engine's 100-day window.
    months: int = 4


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
    weekly: tuple[Weekly, ...] = ()
    savings_habits: tuple[SavingsHabit, ...] = ()


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
    Persona(
        username="sofie",
        first_name="Sofie",
        last_name="Janssens",
        persona="Projectingenieur, 29, Antwerpen, pendelt met de auto",
        accounts=(
            ("Zichtrekening", AccountType.CURRENT, "2185.30"),
            ("Spaarrekening", AccountType.SAVINGS, "9400.00"),
            ("KBC Mastercard", AccountType.CREDIT_CARD, "-164.20"),
        ),
        recurring=(
            Recurring(1, "Huur appartement", "Immo Zuid Antwerpen", "-890.00", Category.HOUSING),
            Recurring(25, "Salaris", "Scheldebouw NV", "2780.00", Category.INCOME),
            Recurring(5, "Energie", "Engie", "-96.00", Category.UTILITIES),
            Recurring(12, "Internet & mobiel", "Proximus", "-54.00", Category.UTILITIES),
            # Paid every month, while nothing in her history looks like travel.
            Recurring(3, "Luxepakket kredietkaart", "KBC Bank", "-25.00", Category.OTHER),
        ),
        # Four shops per category at similar amounts: spending stays spread out, so the fuel
        # station is the one place she is loyal to.
        daily_spend=(
            ("Colruyt Berchem", Category.GROCERIES, 10, 55),
            ("Albert Heijn Berchem", Category.GROCERIES, 10, 55),
            ("Delhaize Zurenborg", Category.GROCERIES, 10, 55),
            ("Lidl Borgerhout", Category.GROCERIES, 10, 55),
            ("Bar Zurenborg", Category.LEISURE, 5, 35),
            ("Kinepolis Antwerpen", Category.LEISURE, 5, 35),
            ("Bolt Food", Category.LEISURE, 5, 35),
            ("Sportoase Antwerpen", Category.LEISURE, 5, 35),
        ),
        weekly=(Weekly(0, "TotalEnergies Berchem", 55, 75, Category.TRANSPORT),),
        savings_habits=(SavingsHabit(28, 2, "250.00", "Naar spaarrekening"),),
    ),
    Persona(
        username="bram",
        first_name="Bram",
        last_name="Wouters",
        persona="Magazijnier via interim, 26, Mechelen, krap bij kas",
        accounts=(
            # Well under next month's rent: the engine must warn before the 1st, not after.
            ("Zichtrekening", AccountType.CURRENT, "212.40"),
            ("Spaarrekening", AccountType.SAVINGS, "35.00"),
        ),
        recurring=(
            Recurring(1, "Huur studio", "Immo Mechelen Centrum", "-720.00", Category.HOUSING),
            Recurring(28, "Loon interim", "Randstad Mechelen", "1740.00", Category.INCOME),
            Recurring(6, "Energie", "Eneco", "-85.00", Category.UTILITIES),
            Recurring(14, "Internet & mobiel", "Telenet", "-45.00", Category.UTILITIES),
            Recurring(18, "Afbetaling", "Klarna", "-39.90", Category.OTHER),
        ),
        # One cheap supermarket for everything: a real deal exists, and Kate must hold it back
        # while the rent is at risk.
        daily_spend=(
            ("Aldi Mechelen", Category.GROCERIES, 6, 40),
            ("Frituur 't Hoekske", Category.LEISURE, 4, 18),
            ("Bolt Food", Category.LEISURE, 4, 18),
            ("Snooker Mechelen", Category.LEISURE, 4, 18),
            ("Pizza Hut Mechelen", Category.LEISURE, 4, 18),
        ),
    ),
    Persona(
        # The control case: a steady, healthy customer with nothing going on. Kate must say
        # nothing at all to him, which is the point: no signal, no message, no spam.
        username="tom",
        first_name="Tom",
        last_name="Claes",
        persona="Leerkracht, 45, Hasselt, niets bijzonders aan de hand",
        accounts=(
            ("Zichtrekening", AccountType.CURRENT, "2480.00"),
            ("Spaarrekening", AccountType.SAVINGS, "6200.00"),
        ),
        recurring=(
            Recurring(1, "Huur woning", "Immo Hasselt", "-850.00", Category.HOUSING),
            Recurring(25, "Wedde", "Vlaamse Overheid Onderwijs", "2650.00", Category.INCOME),
            Recurring(8, "Energie", "Luminus", "-110.00", Category.UTILITIES),
        ),
        # Spread over several shops per category, so no single merchant stands out.
        daily_spend=(
            ("Colruyt Hasselt", Category.GROCERIES, 15, 45),
            ("Delhaize Hasselt", Category.GROCERIES, 15, 45),
            ("Aldi Hasselt", Category.GROCERIES, 15, 45),
            ("Lidl Hasselt", Category.GROCERIES, 15, 45),
            ("Bakkerij Vandijck", Category.GROCERIES, 3, 9),
        ),
    ),
    Persona(
        username="els",
        first_name="Els",
        last_name="Claes",
        persona="Lerares, 54, Hasselt, haar moeder overleed onlangs",
        accounts=(
            ("Zichtrekening", AccountType.CURRENT, "41280.55"),
            ("Spaarrekening", AccountType.SAVINGS, "8600.00"),
            ("KBC Mastercard", AccountType.CREDIT_CARD, "-96.40"),
        ),
        recurring=(
            Recurring(2, "Woonkrediet", "KBC Bank", "-980.00", Category.HOUSING),
            Recurring(28, "Wedde", "AgODi Vlaamse Gemeenschap", "3150.00", Category.INCOME),
            Recurring(6, "Energie", "Luminus", "-135.00", Category.UTILITIES),
            Recurring(10, "Internet & tv", "Telenet", "-89.00", Category.UTILITIES),
        ),
        daily_spend=(
            ("Delhaize Hasselt", Category.GROCERIES, 10, 60),
            ("Colruyt Hasselt", Category.GROCERIES, 10, 60),
            ("Carrefour Hasselt", Category.GROCERIES, 10, 60),
            ("Lidl Hasselt", Category.GROCERIES, 10, 60),
        ),
        # The estate is paid out by the notary, not by an employer: booked as "other", the way a
        # bank would categorise it, so it can never pass for a first salary.
        one_offs=(
            OneOff(82, "Uitvaart mama", "Uitvaartzorg Hasselt", "-5840.00", Category.OTHER),
            OneOff(
                79, "Provisie notaris", "Notariskantoor Vandersteen", "-1250.00", Category.OTHER
            ),
            OneOff(71, "Rouwkaarten", "Drukkerij Limburg", "-310.00", Category.OTHER),
            OneOff(
                4,
                "Nalatenschap mama - uitkering",
                "Notariskantoor Vandersteen",
                "38450.00",
                Category.OTHER,
            ),
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
        savings_index = next(
            (
                i
                for i, (_, t, _) in enumerate(persona.accounts, start=1)
                if t == AccountType.SAVINGS
            ),
            None,
        )
        savings_id = f"a_{persona.username}_{savings_index}" if savings_index else None
        _seed_history(bank, persona, f"a_{persona.username}_1", savings_id, today, rng)


def _seed_history(
    bank: Bank,
    persona: Persona,
    account_id: str,
    savings_id: str | None,
    today: date,
    rng: random.Random,
) -> None:
    counter = 0

    def book(
        day: date,
        description: str,
        counterparty: str,
        amount: Decimal,
        cat: Category,
        on: str = account_id,
    ) -> None:
        nonlocal counter
        counter += 1
        bank.add_transaction(
            Transaction(
                id=f"t_{persona.username}_{counter:04d}",
                account_id=on,
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
        for weekly in persona.weekly:
            if day.weekday() == weekly.weekday:
                amount = Decimal(str(round(rng.uniform(weekly.low, weekly.high), 2)))
                book(day, weekly.counterparty, weekly.counterparty, -amount, weekly.category)

    for event in persona.one_offs:
        day = today - timedelta(days=event.days_ago)
        book(day, event.description, event.counterparty, Decimal(event.amount), event.category)

    if savings_id is None:
        return
    for habit in persona.savings_habits:
        for day in _habit_days(habit, today, rng):
            amount = Decimal(habit.amount)
            book(day, habit.description, "Eigen spaarrekening", -amount, Category.TRANSFER)
            book(
                day, habit.description, "Eigen zichtrekening", amount, Category.TRANSFER, savings_id
            )


def _habit_days(habit: SavingsHabit, today: date, rng: random.Random) -> list[date]:
    """The habit's dates in the last `habit.months` months that have already happened."""
    days: list[date] = []
    year, month = today.year, today.month
    while len(days) < habit.months:
        jitter = rng.randint(-habit.jitter_days, habit.jitter_days)
        day = date(year, month, min(habit.day, 28)) + timedelta(days=jitter)
        if day <= today:
            days.append(day)
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return days
