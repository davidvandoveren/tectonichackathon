"""Lenen: Kate never proposes credit herself; she prepares the conversation with an advisor."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, PlainSerializer

from app.skills.base import Params, Skill, euro
from app.skills.packs._handoff import handoff_action

# Credit amounts are far above the transfer limit; this is only context for the advisor.
LoanAmount = Annotated[
    Decimal,
    Field(gt=0, le=Decimal("5000000.00"), max_digits=9, decimal_places=2),
    PlainSerializer(lambda value: f"{value:.2f}", return_type=str),
]

PURPOSES = {"home": "woning", "car": "wagen", "renovation": "verbouwing"}


class ExploreParams(Params):
    purpose: Literal["home", "car", "renovation"]
    amount: LoanAmount | None = None


explore = handoff_action(
    id="loans.explore",
    title="Lening bespreken",
    description="Bereid een gesprek over een lening (woning, wagen, verbouwing) voor met een "
    "adviseur. Kate doet zelf geen kredietvoorstel.",
    params=ExploreParams,
    summary=lambda p: (
        f"Klant wil een lening voor een {PURPOSES[p.purpose]} bespreken"
        + (f", ± {euro(p.amount)}." if p.amount else ".")
    ),
)

SKILL = Skill(
    id="loans",
    title="Lenen",
    description="Woonkrediet, autolening, renovatie; beslist door een adviseur.",
    actions=(explore,),
)
