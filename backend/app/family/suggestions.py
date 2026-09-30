"""What Kate says about the family circle, each with a plain-language "Waarom zie ik dit?".

Deliberately few and respectful: an invite waiting for you, a guardianship about to end, the
decision that is yours once you turn 18, and a pot you were invited to contribute to. Nothing is
ever said *to* a minor except about their own rights, and no suggestion sells a product.
"""

from dataclasses import dataclass
from datetime import date

from app.domain.bank import Bank
from app.family.circle import (
    ADULT_AGE,
    FamilyCircle,
    Level,
    Role,
    Status,
    eighteenth_birthday,
)

GUARDIANSHIP_HEADS_UP_DAYS = 45
JUST_TURNED_ADULT_DAYS = 60

ROLE_LABELS = {
    Role.PARTNER: "partner",
    Role.PARENT: "ouder",
    Role.CHILD: "kind",
    Role.GRANDPARENT: "grootouder",
    Role.GRANDCHILD: "kleinkind",
    Role.GODPARENT: "meter of peter",
    Role.GODCHILD: "petekind",
    Role.SIBLING: "broer of zus",
    Role.OTHER: "familielid",
}


@dataclass(frozen=True)
class Suggestion:
    id: str
    kind: str
    title: str
    body: str
    reason: str
    cta_label: str
    cta_target: str


def _first_name(bank: Bank, user_id: str | None) -> str:
    user = bank.get_user(user_id) if user_id else None
    return user.first_name if user else "Iemand"


def suggestions_for(
    user_id: str, circle: FamilyCircle, bank: Bank, today: date
) -> list[Suggestion]:
    result: list[Suggestion] = []
    minor = circle.is_minor(user_id, today)

    for link in circle.links_for(user_id):
        other = link.other(user_id)
        name = _first_name(bank, other)

        if link.status == Status.PENDING and link.invitee_id == user_id:
            role = ROLE_LABELS[link.roles[link.inviter_id]]
            result.append(
                Suggestion(
                    id=f"invite-{link.id}",
                    kind="invite",
                    title=f"{name} wil jou toevoegen aan de familiekring",
                    body=f"{name} noemt zichzelf je {role}. "
                    "Jij kiest wat je deelt, of je zegt nee.",
                    reason="Je kreeg een uitnodiging. Zonder jouw akkoord deelt niemand iets met "
                    "de ander, en je kan de link later altijd stopzetten.",
                    cta_label="Bekijk uitnodiging",
                    cta_target="/family",
                )
            )
            continue
        if link.status != Status.ACTIVE or link.ward_id is None:
            continue

        birth = circle.birth_date(link.ward_id)
        if birth is None:
            continue
        adult_on = eighteenth_birthday(birth)
        days_left = (adult_on - today).days

        if user_id == link.guardian_id and 0 < days_left <= GUARDIANSHIP_HEADS_UP_DAYS:
            result.append(
                Suggestion(
                    id=f"guardianship-ends-{link.id}",
                    kind="guardianship_ending",
                    title=f"{name} wordt over {days_left} dagen {ADULT_AGE}",
                    body=f"Dan stopt je wettelijke toegang tot de rekeningen van {name} "
                    f"automatisch. Daarna beslist {name} zelf wat jij nog ziet. Een goed moment "
                    "om er samen over te praten.",
                    reason=f"{name} is aan jou gekoppeld als minderjarig kind. Die voogdij loopt "
                    f"volgens de wet af op de {ADULT_AGE}de verjaardag.",
                    cta_label="Bekijk familiekring",
                    cta_target="/family",
                )
            )
        if (
            user_id == link.ward_id
            and not link.ward_decided
            and -JUST_TURNED_ADULT_DAYS <= days_left <= 0
        ):
            parent = _first_name(bank, link.guardian_id)
            result.append(
                Suggestion(
                    id=f"now-adult-{link.id}",
                    kind="now_adult",
                    title=f"Je bent {ADULT_AGE}: jij beslist nu",
                    body=f"{parent} ziet je saldo niet meer automatisch. Wil je iets blijven "
                    "delen, zoals een potje? Standaard zie je elkaar enkel nog in de kring.",
                    reason=f"Tot je {ADULT_AGE}de had {parent} als ouder wettelijke toegang. Die "
                    "stopte op je verjaardag; alleen jouw keuze telt nu.",
                    cta_label="Kies wat je deelt",
                    cta_target="/family",
                )
            )

    if minor:  # no nudges towards spending or giving for minors
        return result

    for pot, level in circle.pots_for(user_id, today):
        if pot.owner_id == user_id or pot.goal is None or pot.balance >= pot.goal:
            continue
        owner = _first_name(bank, pot.owner_id)
        percent = int(pot.balance * 100 / pot.goal)
        detail = (
            "Je ziet enkel de voortgang, niet wie wat gaf en niet de rekeningen van " + owner
            if level == Level.GIFT
            else "Je ziet de voortgang en de bijdragen, niet de rekeningen van " + owner
        )
        result.append(
            Suggestion(
                id=f"pot-{pot.id}",
                kind="pot_contribution",
                title=f"{owner} spaart voor '{pot.name}' ({percent}%)",
                body="Wil je iets bijdragen? Het gaat van je eigen rekening, je bevestigt zelf.",
                reason=f"{owner} deelde dit potje met jou en gaf je toestemming om bij te dragen. "
                f"{detail}.",
                cta_label="Bijdragen",
                cta_target=f"/family?pot={pot.id}",
            )
        )
    return result
