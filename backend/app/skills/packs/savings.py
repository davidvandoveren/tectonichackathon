"""Sparen: move money between the customer's own accounts, and savings goals."""

from collections.abc import Callable
from typing import Annotated

from pydantic import Field, field_validator

from app.domain.models import AccountType
from app.skills.base import Action, Money, Outcome, Params, Risk, Skill, SkillContext, clean, euro
from app.skills.holdings import SavingsGoal
from app.skills.packs._accounts import move_between_own, own_account


class MoveParams(Params):
    amount: Money


def _can_move(
    source: AccountType, target: AccountType
) -> Callable[[SkillContext, MoveParams], str | None]:
    def check(ctx: SkillContext, params: MoveParams) -> str | None:
        src, dst = own_account(ctx, source), own_account(ctx, target)
        if src is None or dst is None:
            return "Je hebt geen zicht- én spaarrekening."
        if params.amount > src.balance:
            return f"Er staat niet genoeg op je {src.name.lower()}."
        return None

    return check


def _mover(
    source: AccountType, target: AccountType, text: str
) -> Callable[[SkillContext, MoveParams], Outcome]:
    def execute(ctx: SkillContext, params: MoveParams) -> Outcome:
        move_between_own(ctx, source, target, params.amount, text)
        return Outcome("done", f"{euro(params.amount)} staat op je {text.lower()}.")

    return execute


move_to_savings = Action(
    id="savings.move_to_savings",
    title="Geld opzij zetten",
    description="Zet een bedrag van de zichtrekening naar de eigen spaarrekening van de klant.",
    risk=Risk.INTERNAL_MONEY,
    params=MoveParams,
    summary=lambda p: f"{euro(p.amount)} naar je spaarrekening",
    eligible=_can_move(AccountType.CURRENT, AccountType.SAVINGS),
    execute=_mover(AccountType.CURRENT, AccountType.SAVINGS, "Spaarrekening"),
    amount_of=lambda p: p.amount,
)

move_to_current = Action(
    id="savings.move_to_current",
    title="Zichtrekening aanvullen",
    description="Zet een bedrag van de eigen spaarrekening terug naar de zichtrekening, "
    "bijvoorbeeld om een tekort voor een vaste kost te vermijden.",
    risk=Risk.INTERNAL_MONEY,
    params=MoveParams,
    summary=lambda p: f"{euro(p.amount)} van je spaarrekening naar je zichtrekening",
    eligible=_can_move(AccountType.SAVINGS, AccountType.CURRENT),
    execute=_mover(AccountType.SAVINGS, AccountType.CURRENT, "Zichtrekening"),
    amount_of=lambda p: p.amount,
)


class GoalParams(Params):
    name: Annotated[str, Field(min_length=1, max_length=40)]
    target: Money
    monthly: Money | None = None

    @field_validator("name")
    @classmethod
    def _clean(cls, value: str) -> str:
        return clean(value)


def _create_goal(ctx: SkillContext, params: GoalParams) -> Outcome:
    with ctx.holdings.lock:
        ctx.holdings.of(ctx.owner_id).goals.append(
            SavingsGoal(params.name, params.target, params.monthly)
        )
    return Outcome("done", f"Spaardoel '{params.name}' aangemaakt.")


create_goal = Action(
    id="savings.create_goal",
    title="Spaardoel maken",
    description="Maak een spaardoel met een naam, een doelbedrag en optioneel een maandbedrag.",
    risk=Risk.PRODUCT_CHANGE,
    params=GoalParams,
    summary=lambda p: f"Spaardoel '{p.name}' van {euro(p.target)}",
    execute=_create_goal,
)

SKILL = Skill(
    id="savings",
    title="Sparen",
    description="Geld opzij zetten, buffers en spaardoelen.",
    actions=(move_to_savings, move_to_current, create_goal),
)
