"""Public API shapes (see docs/api.md). Internal fields such as password hashes never leave here."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

from app.domain.iban import format_iban, is_valid_iban, normalize_iban
from app.domain.models import AccountType, Category

Money = Annotated[Decimal, PlainSerializer(lambda value: f"{value:.2f}", return_type=str)]
MAX_TRANSFER = Decimal("10000.00")


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class DemoUserOut(ApiModel):
    username: str
    display_name: str
    persona: str


class LoginIn(ApiModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class AuthConfigOut(ApiModel):
    passwordless_login: bool


class DemoLoginIn(ApiModel):
    username: str = Field(min_length=1, max_length=64)


class MeOut(ApiModel):
    id: str
    username: str
    first_name: str
    last_name: str
    persona: str


class AccountOut(ApiModel):
    id: str
    name: str
    type: AccountType
    iban: str
    balance: Money
    currency: str

    @field_validator("iban")
    @classmethod
    def _pretty_iban(cls, value: str) -> str:
        return format_iban(value)


class TransactionOut(ApiModel):
    id: str
    account_id: str
    booked_at: date
    description: str
    counterparty: str
    amount: Money
    currency: str
    category: Category


class TransferIn(ApiModel):
    from_account_id: str = Field(min_length=1, max_length=64)
    to_iban: str = Field(min_length=15, max_length=42)
    to_name: str = Field(min_length=1, max_length=70)
    amount: Decimal = Field(gt=0, le=MAX_TRANSFER, max_digits=7, decimal_places=2)
    description: str = Field(default="", max_length=140)

    @field_validator("to_iban")
    @classmethod
    def _valid_iban(cls, value: str) -> str:
        if not is_valid_iban(value):
            raise ValueError("Invalid IBAN")
        return normalize_iban(value)

    @field_validator("to_name", "description")
    @classmethod
    def _clean_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if any(not char.isprintable() for char in cleaned):
            raise ValueError("Contains control characters")
        return cleaned


class InsightOut(ApiModel):
    id: str
    kind: str
    title: str
    body: str
    cta_label: str
    cta_target: str
    reason: str
