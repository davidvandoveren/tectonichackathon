"""Beleggen: neutral preparation of an advisor meeting, never "buy X" (MiFID suitability)."""

from app.skills.base import Params, Skill
from app.skills.packs._handoff import handoff_action


class MeetingParams(Params):
    pass


prepare_meeting = handoff_action(
    id="investing.prepare_meeting",
    title="Beleggingsgesprek voorbereiden",
    description="Bereid een vrijblijvend gesprek met een adviseur voor over wat de klant met "
    "spaargeld kan doen. Geen concreet beleggingsadvies.",
    params=MeetingParams,
    summary=lambda _: (
        "Klant wil vrijblijvend bespreken wat past bij de eigen plannen en het eigen risicoprofiel."
    ),
)

SKILL = Skill(
    id="investing",
    title="Beleggen",
    description="Uitleg en een gesprek met een adviseur; nooit autonoom.",
    actions=(prepare_meeting,),
)
