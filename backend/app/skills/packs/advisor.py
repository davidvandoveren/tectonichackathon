"""Adviseur: hand the conversation to a human with context, for anything Kate should not decide."""

from typing import Annotated

from pydantic import Field, field_validator

from app.skills.base import Params, Risk, Skill, clean
from app.skills.packs._handoff import handoff_action


class CallParams(Params):
    topic: Annotated[str, Field(min_length=1, max_length=140)]

    @field_validator("topic")
    @classmethod
    def _clean(cls, value: str) -> str:
        return clean(value)


book_call = handoff_action(
    id="advisor.book_call",
    title="Gesprek met een adviseur",
    description="Vraag een gesprek met een KBC-adviseur aan, met een korte samenvatting zodat "
    "de klant zijn verhaal niet opnieuw moet doen.",
    params=CallParams,
    summary=lambda p: f"Klant vraagt een gesprek over: {p.topic}",
    risk=Risk.INFO,
)

SKILL = Skill(
    id="advisor",
    title="Adviseur",
    description="Een mens, met de context al klaar.",
    actions=(book_call,),
)
