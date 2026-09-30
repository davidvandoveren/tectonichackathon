"""Verzekeren: Kate prepares a quote request; an advisor makes the offer."""

from typing import Literal

from app.skills.base import Params, Skill
from app.skills.packs._handoff import handoff_action

REASONS = {"moving": "verhuis", "new_home": "nieuwe woning", "renovation": "verbouwing"}


class HomeQuoteParams(Params):
    reason: Literal["moving", "new_home", "renovation"] = "moving"


class TravelQuoteParams(Params):
    trips_per_year: int | None = None


home_quote = handoff_action(
    id="insurance.home_quote",
    title="Woonverzekering bekijken",
    description="Bereid een offerteaanvraag voor een woonverzekering voor (bv. bij een verhuis) "
    "en draag over aan een adviseur.",
    params=HomeQuoteParams,
    summary=lambda p: f"Klant wil een woonverzekering bekijken (reden: {REASONS[p.reason]}).",
)

travel_quote = handoff_action(
    id="insurance.travel_quote",
    title="Reisverzekering bekijken",
    description="Bereid een vraag rond reisbijstand en annulering voor en draag over aan een "
    "adviseur.",
    params=TravelQuoteParams,
    summary=lambda p: (
        "Klant wil een reisverzekering bekijken"
        + (f" (± {p.trips_per_year} reizen per jaar)." if p.trips_per_year else ".")
    ),
)

SKILL = Skill(
    id="insurance",
    title="Verzekeren",
    description="Woon- en reisverzekeringen, altijd met een adviseur.",
    actions=(home_quote, travel_quote),
)
