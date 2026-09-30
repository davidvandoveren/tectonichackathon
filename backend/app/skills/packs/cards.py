"""Kaarten: KBC's optional credit-card packages (facts: docs/design/moments-engine.md §5.2, §11).

Adding a paid package always needs the customer's tap. Dropping one saves money, so the customer
may let Kate do it automatically.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.skills.base import Action, Level, Outcome, Params, Risk, Skill, SkillContext, euro


@dataclass(frozen=True)
class Package:
    name: str
    monthly: Decimal
    covers: str


PACKAGES: dict[str, Package] = {
    "shopping": Package(
        "Shoppingpakket", Decimal("1.50"), "aankoopverzekering en 2 jaar extra garantie"
    ),
    "reis": Package(
        "Reispakket", Decimal("7.00"), "annulering, franchise huurwagen en vertraagde bagage"
    ),
    "luxe": Package(
        "Luxepakket", Decimal("25.00"), "24/7 Lifestyle & Travel Manager en airport lounges"
    ),
}

PackageId = Literal["shopping", "reis", "luxe"]


class PackageParams(Params):
    package: PackageId


def _not_held(ctx: SkillContext, params: PackageParams) -> str | None:
    if params.package in ctx.holdings.of(ctx.owner_id).card_packages:
        return f"Je hebt het {PACKAGES[params.package].name} al."
    return None


def _held(ctx: SkillContext, params: PackageParams) -> str | None:
    if params.package not in ctx.holdings.of(ctx.owner_id).card_packages:
        return f"Je hebt geen {PACKAGES[params.package].name}."
    return None


def _add(ctx: SkillContext, params: PackageParams) -> Outcome:
    package = PACKAGES[params.package]
    with ctx.holdings.lock:
        ctx.holdings.of(ctx.owner_id).card_packages.add(params.package)
    return Outcome("done", f"{package.name} is actief ({euro(package.monthly)} per maand).")


def _drop(ctx: SkillContext, params: PackageParams) -> Outcome:
    package = PACKAGES[params.package]
    with ctx.holdings.lock:
        ctx.holdings.of(ctx.owner_id).card_packages.discard(params.package)
    return Outcome(
        "done", f"{package.name} opgezegd: je bespaart {euro(package.monthly * 12)} per jaar."
    )


add_package = Action(
    id="cards.add_package",
    title="Kaartpakket toevoegen",
    description="Voeg een optioneel pakket toe aan de KBC-kredietkaart: "
    + "; ".join(
        f"{k} = {p.name} ({euro(p.monthly)}/maand: {p.covers})" for k, p in PACKAGES.items()
    ),
    risk=Risk.PRODUCT_CHANGE,
    params=PackageParams,
    summary=lambda p: f"{PACKAGES[p.package].name} voor {euro(PACKAGES[p.package].monthly)}/maand",
    eligible=_not_held,
    execute=_add,
    max_level=Level.PREPARE,  # costs the customer money
)

drop_package = Action(
    id="cards.drop_package",
    title="Kaartpakket opzeggen",
    description="Zeg een optioneel kaartpakket op dat de klant niet gebruikt, zodat de klant "
    "geld bespaart.",
    risk=Risk.PRODUCT_CHANGE,
    params=PackageParams,
    summary=lambda p: (
        f"{PACKAGES[p.package].name} opzeggen, "
        f"{euro(PACKAGES[p.package].monthly * 12)} per jaar terug"
    ),
    eligible=_held,
    execute=_drop,
)

SKILL = Skill(
    id="cards",
    title="Kaarten",
    description="Kredietkaart en optionele pakketten.",
    actions=(add_package, drop_package),
)
