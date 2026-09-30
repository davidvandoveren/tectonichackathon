"""Layer 4 - composition.

Turns a routing decision into something a customer can read. Copy comes from a fixed table and
is filled only with numbers the engine actually observed: no model writes text here, so a
suggestion can never invent an amount, a product or a promise.

A template is used only when every placeholder it needs is present; otherwise the neutral body
is shown. A customer never sees a half-filled sentence.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from app.moments.arbitration import Channel, Decision


@dataclass(frozen=True)
class Copy:
    title: str
    body: str
    cta_label: str
    cta_target: str
    requires_advisor: bool = False
    body_template: str | None = None
    template_keys: tuple[str, ...] = ()


COPY: Mapping[str, Copy] = {
    "cashflow_risk": Copy(
        title="Let op je saldo",
        body=(
            "Je zichtrekening staat lager dan je grootste woonkost van de afgelopen twee "
            "maanden. Zet tijdig geld klaar, dan kan er niets mislopen."
        ),
        cta_label="Geld overschrijven",
        cta_target="/transfer",
    ),
    "income_missing": Copy(
        title="Je loon is nog niet gestort",
        body="Een storting die je elke maand krijgt, is er deze keer nog niet. Bekijk je rekening.",
        body_template=(
            "{counterparty} betaalde je elke maand, maar de storting is nu {days_overdue} dagen "
            "te laat. Wil je dat we er samen naar kijken?"
        ),
        template_keys=("counterparty", "days_overdue"),
        cta_label="Bekijk mijn rekening",
        cta_target="/",
        requires_advisor=True,
    ),
    "first_salary": Copy(
        title="Proficiat met je eerste loon!",
        body=(
            "Zet elke maand automatisch een klein deel opzij, dan groeit je buffer zonder dat "
            "je eraan moet denken."
        ),
        cta_label="Start met sparen",
        cta_target="/transfer",
    ),
    "moving_house": Copy(
        title="Ga je verhuizen?",
        body=(
            "Denk aan je woonverzekering, je adreswijziging en je energiecontract. "
            "We zetten het voor je op een rij."
        ),
        cta_label="Mijn gegevens",
        cta_target="/profile",
    ),
    "idle_savings": Copy(
        title="Je spaargeld kan meer voor je doen",
        body=(
            "Een groot deel van je spaargeld staat stil. Bespreek vrijblijvend wat past bij "
            "jouw plannen en risicoprofiel."
        ),
        cta_label="Bekijk mijn rekeningen",
        cta_target="/",
        requires_advisor=True,
    ),
    "savings_habit_automatable": Copy(
        title="Wil je dit automatisch laten doen?",
        body=(
            "Je zet elke maand zelf geld op je spaarrekening. Daar kunnen we een bestendige "
            "opdracht van maken."
        ),
        body_template=(
            "Je zet al {months} maanden zelf geld opzij, meestal € {amount}. We kunnen daar een "
            "bestendige opdracht van maken — stopzetten kan altijd."
        ),
        template_keys=("months", "amount"),
        cta_label="Zet het automatisch",
        cta_target="/transfer",
    ),
    "deal_match": Copy(
        title="Er is een deal die bij jou past",
        body=(
            "Je komt vaak bij dezelfde zaak. Met Kate Deals krijg je een deel van je uitgave terug."
        ),
        body_template=(
            "Je betaalde {bookings} keer bij {counterparty} in de laatste drie maanden. "
            "Met Kate Deals krijg je een deel daarvan terug."
        ),
        template_keys=("bookings", "counterparty"),
        cta_label="Bekijk de deal",
        cta_target="/",
    ),
    "card_package_waste": Copy(
        title="Betaal je voor iets dat je niet gebruikt?",
        body=(
            "Je betaalt elke maand voor een kaartpakket met reisvoordelen, maar we zien geen "
            "reizen. Opzeggen kan altijd, en je krijgt het terug als je het nodig hebt."
        ),
        body_template=(
            "Het {package_name} kost je {yearly_cost_label} per jaar, maar we zien geen reizen. "
            "Zeg je het op, dan hou je dat bedrag zelf. Terugnemen kan altijd."
        ),
        template_keys=("package_name", "yearly_cost_label"),
        cta_label="Pakket opzeggen",
        cta_target="/",
    ),
    "card_package_gap": Copy(
        title="Reis je verzekerd?",
        body=(
            "Je reist, maar je hebt geen Reispakket. Dat dekt annulering, de franchise van een "
            "huurwagen en vertraagde bagage."
        ),
        body_template=(
            "We zagen {trips} reisuitgave(n), de laatste bij {last_merchant}. Het Reispakket "
            "({reis_monthly_label} per maand) dekt annulering, de franchise van een huurwagen "
            "en vertraagde bagage."
        ),
        template_keys=("trips", "last_merchant", "reis_monthly_label"),
        cta_label="Bekijk het Reispakket",
        cta_target="/",
    ),
}

FALLBACK = Copy(
    title="Kate zag iets dat je kan helpen",
    body="Bekijk je rekeningen voor de details.",
    cta_label="Bekijk mijn rekeningen",
    cta_target="/",
)


@dataclass(frozen=True)
class ComposedItem:
    id: str
    title: str
    body: str
    urgency: int
    channel: Channel
    reason: str
    cta_label: str
    cta_target: str
    requires_advisor: bool


def _body(copy: Copy, meta: Mapping[str, str]) -> str:
    if copy.body_template and all(key in meta for key in copy.template_keys):
        return copy.body_template.format(**{key: meta[key] for key in copy.template_keys})
    return copy.body


def compose(decision: Decision) -> ComposedItem:
    copy = COPY.get(decision.moment.type, FALLBACK)
    return ComposedItem(
        id=decision.moment.type,
        title=copy.title,
        body=_body(copy, decision.moment.meta),
        urgency=decision.urgency,
        channel=decision.channel,
        reason=decision.moment.reason,
        cta_label=copy.cta_label,
        cta_target=copy.cta_target,
        requires_advisor=copy.requires_advisor,
    )
