"""Synthetic family circle for the demo. No real customer data, ever.

Kept out of `domain/seed.py` on purpose (that file is owned by the Moments Engine work): this module
only *adds* two new synthetic customers and the links between them and the existing personas.

The story:
- **Emma ↔ Lucas** (engaged): both share `pot`. Emma's pot "Ons trouwfeest" is shared with Lucas.
- **Emma ↔ Marie** (granddaughter ↔ grandmother): Emma shares `gift`, so Marie may contribute to
  the wedding pot and sees only its progress, not Emma's accounts, not who gave what.
- **Jan ↔ Noor** (father ↔ daughter, from the registry): Noor is 17 and turns 18 in three weeks.
  Until then Jan sees her balances by law; after that (try the time machine) Noor decides.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from app.domain.bank import Bank
from app.domain.iban import make_be_iban
from app.domain.models import Account, AccountType, Category, Transaction, User
from app.family.circle import Contribution, FamilyCircle, Level, Role
from app.security.passwords import hash_password

NOOR_DAYS_UNTIL_18 = 21
# Separate IBAN range from `domain/seed.py` so the two seeds can never collide.
_ACCOUNT_BASE = 7_360_000_000

_NEW_CUSTOMERS = (
    # username, first, last, persona, accounts
    (
        "lucas",
        "Lucas",
        "Janssens",
        "Verpleegkundige, 23, Leuven, verloofd met Emma",
        (
            ("Zichtrekening", AccountType.CURRENT, "1840.20"),
            ("Spaarrekening", AccountType.SAVINGS, "5200.00"),
        ),
    ),
    (
        "noor",
        "Noor",
        "Maes",
        "Scholier, 17, Gent, dochter van Jan (wordt binnenkort 18)",
        (
            ("Jongerenrekening", AccountType.CURRENT, "420.35"),
            ("Spaarrekening", AccountType.SAVINGS, "1150.00"),
        ),
    ),
)


def _years_ago(today: date, years: int, extra_days: int = 0) -> date:
    try:
        anchor = today.replace(year=today.year - years)
    except ValueError:  # today is 29 February
        anchor = date(today.year - years, 3, 1)
    return anchor - timedelta(days=extra_days)


def seed_family(bank: Bank, circle: FamilyCircle, demo_password: str, today: date) -> None:
    _add_customers(bank, demo_password, today)
    users = {u.username: u for u in bank.list_users()}
    needed = {"emma", "jan", "marie", "lucas", "noor"}
    if not needed <= users.keys():  # a persona was renamed or removed: seed nothing half-way
        return
    emma, jan, marie, lucas, noor = (users[n] for n in ("emma", "jan", "marie", "lucas", "noor"))

    circle.set_birth_date(emma.id, _years_ago(today, 21, 140))
    circle.set_birth_date(jan.id, _years_ago(today, 34, 200))
    circle.set_birth_date(marie.id, _years_ago(today, 67, 45))
    circle.set_birth_date(lucas.id, _years_ago(today, 23, 80))
    # Turns 18 in three weeks: 18 years ago plus 21 days is still 17 today.
    circle.set_birth_date(noor.id, _years_ago(today, 18) + timedelta(days=NOOR_DAYS_UNTIL_18))

    engaged = circle.invite(emma, lucas.username, Role.PARTNER, Level.POT, today - timedelta(90))
    circle.accept(lucas.id, engaged.id, Level.POT, today - timedelta(89))
    grandma = circle.invite(
        emma, marie.username, Role.GRANDCHILD, Level.GIFT, today - timedelta(60)
    )
    circle.accept(marie.id, grandma.id, Level.EXISTS, today - timedelta(59))
    circle.add_registry_guardianship(jan.id, noor.id, since=circle.birth_date(noor.id) or today)

    pot = circle.create_pot(
        emma.id,
        "Ons trouwfeest",
        Decimal("8000.00"),
        [engaged.id, grandma.id],
        today - timedelta(80),
    )
    if pot is None:
        return
    for user, amount, days_ago in (
        (emma, "1200.00", 75),
        (lucas, "950.00", 60),
        (emma, "200.00", 30),
        (lucas, "150.00", 2),
    ):
        circle.seed_pot_contribution(
            pot, Contribution(user.id, Decimal(amount), today - timedelta(days_ago), "")
        )


def _add_customers(bank: Bank, demo_password: str, today: date) -> None:
    account_number = _ACCOUNT_BASE
    for username, first, last, persona, accounts in _NEW_CUSTOMERS:
        if bank.find_user_by_username(username) is not None:
            continue
        password_hash, salt = hash_password(demo_password)
        user = User(
            id=f"u_{username}",
            username=username,
            first_name=first,
            last_name=last,
            persona=persona,
            password_hash=password_hash,
            password_salt=salt,
        )
        bank.add_user(user)
        for index, (name, account_type, balance) in enumerate(accounts, start=1):
            account_number += 1
            bank.add_account(
                Account(
                    id=f"a_{username}_{index}",
                    owner_id=user.id,
                    name=name,
                    type=account_type,
                    iban=make_be_iban(account_number),
                    balance=Decimal(balance),
                )
            )
    _book_history(bank, today)


def _book_history(bank: Bank, today: date) -> None:
    """A little everyday history so the new customers' app does not look empty."""
    rng = random.Random(7)  # noqa: S311 - reproducible synthetic data, not security-relevant
    monthly = {
        "a_lucas_1": (
            (25, "Salaris", "UZ Leuven", "2210.00", Category.INCOME),
            (1, "Huur appartement", "Immo Leuven", "-690.00", Category.HOUSING),
        ),
        "a_noor_1": ((1, "Zakgeld", "Jan Maes", "40.00", Category.TRANSFER),),
    }
    daily = {
        "a_lucas_1": (("Aldi", Category.GROCERIES, 6, 55), ("De Lijn", Category.TRANSPORT, 2.5, 3)),
        "a_noor_1": (("Frituur 't Hoekske", Category.LEISURE, 4, 12),),
    }
    counter = 0
    for days_ago in range(60, -1, -1):
        day = today - timedelta(days=days_ago)
        for account_id, items in monthly.items():
            for dom, text, counterparty, amount, category in items:
                if day.day == dom:
                    counter += 1
                    bank.add_transaction(
                        Transaction(
                            f"t_fam_{counter:04d}",
                            account_id,
                            day,
                            text,
                            counterparty,
                            Decimal(amount),
                            category,
                        )
                    )
        for account_id, spends in daily.items():
            for counterparty, category, low, high in spends:
                if rng.random() < 0.25:
                    counter += 1
                    spent = Decimal(str(round(rng.uniform(low, high), 2)))
                    bank.add_transaction(
                        Transaction(
                            f"t_fam_{counter:04d}",
                            account_id,
                            day,
                            counterparty,
                            counterparty,
                            -spent,
                            category,
                        )
                    )
