"""Wire shapes for the Kate feed and the time machine.

Contract: `docs/plan.md` section 5 and `docs/api.md`. Kept in the engine package rather than in
the shared `app/schemas.py` so parallel work on the other endpoints cannot collide with it.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.moments.arbitration import Silence
from app.moments.composition import ComposedItem
from app.moments.engine import Experience
from app.moments.signals import Domain

Channel = Literal["feed", "push", "sms", "call", "none"]


class FeedItemOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    body: str
    urgency: int = Field(ge=0, le=100)
    channel: Channel
    reason: str
    cta_label: str
    cta_target: str
    requires_advisor: bool

    @classmethod
    def of(cls, item: ComposedItem) -> "FeedItemOut":
        return cls(
            id=item.id,
            title=item.title,
            body=item.body,
            urgency=item.urgency,
            channel=item.channel,
            reason=item.reason,
            cta_label=item.cta_label,
            cta_target=item.cta_target,
            requires_advisor=item.requires_advisor,
        )


class SilenceOut(BaseModel):
    """What Kate deliberately did not say, and why. A first-class part of the answer."""

    model_config = ConfigDict(frozen=True)

    moment: str
    reason_code: str
    reason: str

    @classmethod
    def of(cls, silence: Silence) -> "SilenceOut":
        return cls(
            moment=silence.moment_type,
            reason_code=silence.reason_code,
            reason=silence.reason,
        )


class FeedOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: tuple[FeedItemOut, ...]
    silenced: tuple[SilenceOut, ...]

    @classmethod
    def of(cls, result: Experience) -> "FeedOut":
        return cls(
            items=tuple(FeedItemOut.of(item) for item in result.items),
            silenced=tuple(SilenceOut.of(entry) for entry in result.silenced),
        )


class ConsentOut(BaseModel):
    """Which signal domains the customer allows Kate to look at."""

    model_config = ConfigDict(frozen=True)

    income: bool
    spending: bool
    balances: bool
    products: bool

    @classmethod
    def of(cls, allowed: set[Domain] | frozenset[Domain]) -> "ConsentOut":
        return cls(
            income="income" in allowed,
            spending="spending" in allowed,
            balances="balances" in allowed,
            products="products" in allowed,
        )


class ConsentIn(BaseModel):
    domain: Domain
    allowed: bool


class TimeMachineIn(BaseModel):
    days: int = Field(ge=1, le=365)
    scenario: Literal["none", "salary_paid", "salary_missing"] = "none"
    #: Which persona's timeline to simulate. Defaults to the calling admin.
    username: str | None = Field(default=None, max_length=64)


class TimeMachineOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    days_shifted: int
    clock_offset_days: int
    today: date
    username: str
    injected: int
    feed: FeedOut
