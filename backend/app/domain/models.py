from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class AccountType(StrEnum):
    CURRENT = "current"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"


class Category(StrEnum):
    INCOME = "income"
    GROCERIES = "groceries"
    HOUSING = "housing"
    TRANSPORT = "transport"
    LEISURE = "leisure"
    SHOPPING = "shopping"
    UTILITIES = "utilities"
    SAVINGS = "savings"
    TRANSFER = "transfer"
    OTHER = "other"


@dataclass(frozen=True)
class User:
    id: str
    username: str
    first_name: str
    last_name: str
    persona: str
    password_hash: bytes
    password_salt: bytes


@dataclass
class Account:
    id: str
    owner_id: str
    name: str
    type: AccountType
    iban: str
    balance: Decimal
    currency: str = "EUR"


@dataclass(frozen=True)
class Transaction:
    id: str
    account_id: str
    booked_at: date
    description: str
    counterparty: str
    amount: Decimal
    category: Category
    currency: str = "EUR"


@dataclass(frozen=True)
class Insight:
    id: str
    kind: str
    title: str
    body: str
    cta_label: str
    cta_target: str
    reason: str
