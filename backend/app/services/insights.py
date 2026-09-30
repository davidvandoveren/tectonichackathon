""" "Voor jou" insights: the carousel on home, fed by the moments engine.

Home shows exactly what Kate would say in her feed (`GET /kate/feed`): the same ranking, the same
deliberate silence, the same consent switches and dismissals. Only the shape differs, because the
frontend already renders `Insight`; the engine's extra facts ride along as optional fields.
"""

from collections.abc import Mapping
from datetime import date

from app.domain.bank import Bank
from app.domain.models import Insight, User
from app.moments import engine
from app.moments.arbitration import Decision
from app.moments.composition import compose
from app.moments.state import KateState

#: Ids the pre-engine rules used, kept so links and tests built on them keep working.
LEGACY_IDS: Mapping[str, str] = {"cashflow_risk": "low_buffer", "moving_house": "moving"}


def _kind(decision: Decision, requires_advisor: bool) -> str:
    if decision.moment.urgency == "risk":
        return "alert"
    return "guidance" if requires_advisor else "moment"


def _insight(decision: Decision, user_id: str) -> Insight:
    item = compose(decision)
    moment = decision.moment.type
    return Insight(
        id=f"i_{LEGACY_IDS.get(moment, moment)}_{user_id}",
        kind=_kind(decision, item.requires_advisor),
        title=item.title,
        body=item.body,
        cta_label=item.cta_label,
        cta_target=item.cta_target,
        reason=item.reason,
        moment=moment,
        urgency=item.urgency,
        channel=item.channel,
        confidence=round(decision.moment.confidence, 2),
    )


def insights_for(bank: Bank, user: User, today: date, state: KateState) -> list[Insight]:
    """Ranked, highest urgency first. Silence (an empty list) is a valid, respectful answer."""
    verdict = engine.run(
        bank,
        user,
        today,
        consent=state.consent_for(user.id),
        dismissed=state.dismissals_for(user.id),
        last_interruption=state.last_interruption_for(user.id),
    )
    return [_insight(decision, user.id) for decision in verdict.decisions]
