"""Betalen: pay someone (pre-fill only) and standing orders to the customer's own savings."""

from typing import Annotated
from urllib.parse import urlencode

from pydantic import Field, field_validator

from app.domain.models import AccountType
from app.skills.base import (
    Action,
    Level,
    Money,
    Outcome,
    Params,
    Risk,
    Skill,
    SkillContext,
    clean,
    euro,
)
from app.skills.holdings import StandingOrder
from app.skills.packs._accounts import own_account


class TransferParams(Params):
    to_name: Annotated[str, Field(min_length=1, max_length=70)]
    amount: Money
    description: Annotated[str, Field(max_length=140)] = ""

    @field_validator("to_name", "description")
    @classmethod
    def _clean(cls, value: str) -> str:
        return clean(value)


def _prefill_transfer(_: SkillContext, params: TransferParams) -> Outcome:
    # Kate never pays a third party: the customer finishes on the normal, validated screen.
    query = urlencode(
        {
            "to_name": params.to_name,
            "amount": f"{params.amount:.2f}",
            "description": params.description,
        }
    )
    return Outcome("navigate", "Controleer en bevestig je overschrijving.", f"/transfer?{query}")


transfer = Action(
    id="payments.transfer",
    title="Overschrijving voorbereiden",
    description="Vul een overschrijving naar iemand anders vooraf in. De klant controleert en "
    "bevestigt zelf op het gewone overschrijvingsscherm; Kate betaalt nooit zelf.",
    risk=Risk.EXTERNAL_MONEY,
    params=TransferParams,
    summary=lambda p: f"{euro(p.amount)} naar {p.to_name}",
    execute=_prefill_transfer,
    amount_of=lambda p: p.amount,
)


class StandingOrderParams(Params):
    amount: Money
    day: Annotated[int, Field(ge=1, le=28)]


def _has_savings(ctx: SkillContext, _: StandingOrderParams) -> str | None:
    if own_account(ctx, AccountType.SAVINGS) is None:
        return "Je hebt nog geen spaarrekening."
    return None


def _create_standing_order(ctx: SkillContext, params: StandingOrderParams) -> Outcome:
    savings = own_account(ctx, AccountType.SAVINGS)
    if savings is None:
        raise LookupError("account not found")
    with ctx.holdings.lock:
        ctx.holdings.of(ctx.owner_id).standing_orders.append(
            StandingOrder(params.amount, params.day, savings.id)
        )
    return Outcome(
        "done",
        f"Vanaf nu gaat elke maand op de {params.day}e {euro(params.amount)} naar je sparen.",
    )


standing_order = Action(
    id="payments.standing_order",
    title="Automatisch sparen",
    description="Maak een bestendige opdracht: elke maand een vast bedrag op een vaste dag van "
    "de zichtrekening naar de eigen spaarrekening.",
    risk=Risk.PRODUCT_CHANGE,
    params=StandingOrderParams,
    summary=lambda p: f"Elke maand op de {p.day}e {euro(p.amount)} naar je spaarrekening",
    eligible=_has_savings,
    execute=_create_standing_order,
    # A standing order *is* a lasting commitment: always the customer's own tap.
    max_level=Level.PREPARE,
)

SKILL = Skill(
    id="payments",
    title="Betalen",
    description="Overschrijvingen en bestendige opdrachten.",
    actions=(transfer, standing_order),
)
