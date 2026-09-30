"""The shape every KBC function takes when it plugs into Kate (see docs/design/kate-skills.md).

A `Skill` is one KBC domain; it owns `Action`s. An action says what Kate may fill in (`params`),
how risky it is (`risk`, which caps autonomy), whether this customer can do it right now
(`eligible`) and what happens once approved (`execute`). Nothing here knows about a channel: chat,
voice, proactive cards and the UI all go through the same actions.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

from app.domain.bank import Bank

if TYPE_CHECKING:
    from app.skills.holdings import Holdings

Money = Annotated[
    Decimal,
    Field(gt=0, le=Decimal("10000.00"), max_digits=7, decimal_places=2),
    PlainSerializer(lambda value: f"{value:.2f}", return_type=str),
]

# Hard server-side ceilings for automatic execution; no customer setting can go above these.
MANDATE_MAX_PER_EXECUTION = Decimal("500.00")
MANDATE_MAX_PER_MONTH = Decimal("1000.00")


class Level(IntEnum):
    """The consent ladder: how far Kate may go with one action for one customer."""

    OFF = 0
    SUGGEST = 1
    PREPARE = 2
    AUTO = 3

    @property
    def label(self) -> str:
        return self.name.lower()

    @classmethod
    def parse(cls, label: str) -> "Level":
        return cls[label.upper()]


class Risk(StrEnum):
    INFO = "info"
    INTERNAL_MONEY = "internal_money"
    EXTERNAL_MONEY = "external_money"
    PRODUCT_CHANGE = "product_change"
    REGULATED = "regulated"

    @property
    def ceiling(self) -> Level:
        # Paying someone else or anything credit/investment/insurance-advice related always needs
        # a human confirmation (and for regulated: a human advisor).
        if self in (Risk.EXTERNAL_MONEY, Risk.REGULATED):
            return Level.PREPARE
        return Level.AUTO


class Mandate(BaseModel):
    """A customer's standing permission for automatic execution, within limits."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_per_execution: Money
    max_per_month: Money

    @model_validator(mode="after")
    def _within_ceilings(self) -> Self:
        if self.max_per_execution > MANDATE_MAX_PER_EXECUTION:
            raise ValueError(f"max_per_execution cannot exceed {MANDATE_MAX_PER_EXECUTION}")
        if self.max_per_month > MANDATE_MAX_PER_MONTH:
            raise ValueError(f"max_per_month cannot exceed {MANDATE_MAX_PER_MONTH}")
        if self.max_per_execution > self.max_per_month:
            raise ValueError("max_per_execution cannot exceed max_per_month")
        return self


class Params(BaseModel):
    """Base for every action's params: strict, so Kate cannot smuggle in extra fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


@dataclass(frozen=True)
class SkillContext:
    """Everything an action may touch, already scoped to the authenticated customer."""

    owner_id: str
    bank: Bank
    holdings: "Holdings"
    today: date


@dataclass(frozen=True)
class Outcome:
    kind: Literal["done", "navigate", "advisor_handoff"]
    message: str
    navigate_to: str | None = None
    handoff_summary: str | None = None


def _no_amount(_: Any) -> Decimal | None:
    return None


def _always_eligible(_: SkillContext, __: Any) -> str | None:
    return None


@dataclass(frozen=True)
class Action:
    id: str
    title: str
    description: str
    risk: Risk
    params: type[Params]
    summary: Callable[[Any], str]
    execute: Callable[[SkillContext, Any], Outcome]
    # Returns a plain-Dutch reason when the customer can NOT do this now, else None.
    eligible: Callable[[SkillContext, Any], str | None] = _always_eligible
    # The money an execution moves; drives mandate limits. None = no money involved.
    amount_of: Callable[[Any], Decimal | None] = _no_amount
    default_level: Level = Level.PREPARE
    # Optional tighter cap than the risk class allows (e.g. adding a paid package).
    max_level: Level | None = None

    @property
    def ceiling(self) -> Level:
        cap = self.risk.ceiling
        return min(cap, self.max_level) if self.max_level is not None else cap

    @property
    def moves_money(self) -> bool:
        return self.risk in (Risk.INTERNAL_MONEY, Risk.EXTERNAL_MONEY)


@dataclass(frozen=True)
class Skill:
    id: str
    title: str
    description: str
    actions: tuple[Action, ...] = field(default_factory=tuple)


_CONTROL = re.compile(r"[\x00-\x1f\x7f<>]")


def clean(value: str) -> str:
    """Free text from a model or a customer: no control characters or markup, trimmed."""
    return _CONTROL.sub(" ", value).strip()


def euro(amount: Decimal) -> str:
    return f"€ {amount:,.2f}".replace(",", " ").replace(".", ",")
