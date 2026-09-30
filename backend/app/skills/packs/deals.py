"""Kate Deals: cashback on card / KBC Mobile / Payconiq payments, credited monthly.

Activating a deal is free and only ever gives money back, so it may run automatically.
"""

from typing import Literal

from app.skills.base import Action, Outcome, Params, Risk, Skill, SkillContext

CATEGORIES: dict[str, str] = {
    "fuel": "tanken",
    "groceries": "supermarkt",
    "travel": "reizen",
    "dining": "restaurants",
}


class DealParams(Params):
    category: Literal["fuel", "groceries", "travel", "dining"]


def _inactive(ctx: SkillContext, params: DealParams) -> str | None:
    if params.category in ctx.holdings.of(ctx.owner_id).active_deals:
        return f"Je deal voor {CATEGORIES[params.category]} is al actief."
    return None


def _activate(ctx: SkillContext, params: DealParams) -> Outcome:
    with ctx.holdings.lock:
        ctx.holdings.of(ctx.owner_id).active_deals.add(params.category)
    return Outcome(
        "done",
        f"Deal voor {CATEGORIES[params.category]} actief. Je cashback komt op de eerste "
        "werkdag van de maand.",
    )


activate = Action(
    id="deals.activate",
    title="Kate Deal activeren",
    description="Activeer een gratis cashback-deal in een categorie waar de klant al vaak "
    "betaalt: " + ", ".join(f"{k} = {v}" for k, v in CATEGORIES.items()) + ".",
    risk=Risk.PRODUCT_CHANGE,
    params=DealParams,
    summary=lambda p: f"Cashback-deal voor {CATEGORIES[p.category]}",
    eligible=_inactive,
    execute=_activate,
)

SKILL = Skill(
    id="deals",
    title="Kate Deals",
    description="Cashback bij je vaste handelaars.",
    actions=(activate,),
)
