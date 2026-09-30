"""Kate's proactive feed, plus the consent switches that decide what she may look at.

Separate from `routers/kate.py` (Kate's chat) on purpose: the proactive half of Kate is fully
deterministic and must keep working when no model is reachable.
"""

from fastapi import APIRouter, Response, status

from app.dependencies import BankDep, CurrentUser, KateStateDep, TodayDep
from app.moments import engine
from app.moments.schemas import ConsentIn, ConsentOut, FeedOut

router = APIRouter(tags=["kate"])


@router.get("/kate/feed", response_model=FeedOut)
def feed(user: CurrentUser, bank: BankDep, state: KateStateDep, today: TodayDep) -> FeedOut:
    """What Kate would say to this customer right now — and what she is holding back.

    A read never changes anything: the interruption quota is spent when a message is actually
    sent, not when the feed is looked at.
    """
    return FeedOut.of(
        engine.experience(
            bank,
            user,
            today,
            consent=state.consent_for(user.id),
            dismissed=state.dismissals_for(user.id),
            last_interruption=state.last_interruption_for(user.id),
        )
    )


@router.get("/kate/consent", response_model=ConsentOut)
def read_consent(user: CurrentUser, state: KateStateDep) -> ConsentOut:
    return ConsentOut.of(state.consent_for(user.id))


@router.put("/kate/consent", response_model=ConsentOut)
def update_consent(user: CurrentUser, state: KateStateDep, choice: ConsentIn) -> ConsentOut:
    """Switch a whole family of signals on or off.

    Consent is applied before extraction, so a domain the customer switched off is never even
    computed — not filtered out afterwards.
    """
    return ConsentOut.of(state.set_consent(user.id, choice.domain, choice.allowed))


@router.post("/kate/feed/{moment_type}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss(moment_type: str, user: CurrentUser, state: KateStateDep, today: TodayDep) -> Response:
    """ "Niet meer tonen". The suggestion returns as explained silence, not as nothing."""
    state.dismiss(user.id, moment_type, today)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
