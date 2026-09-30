"""Kate's feed (Moments Engine) -> concrete, confirmable actions.

Uses only the engine's public entry point with the customer's own feed state, so the actions
line up one-to-one with the cards `GET /kate/feed` returns. The engine decides *why now*; this
module attaches *what exactly*, with the customer's real numbers.
"""

from dataclasses import dataclass
from datetime import date

from app.domain.bank import Bank
from app.domain.models import User
from app.moments import engine
from app.moments.state import KateState
from app.skills.moments import Draft, draft_for_moment


@dataclass(frozen=True)
class FeedDraft:
    moment: str
    draft: Draft
    reason: str


def feed_drafts(bank: Bank, user: User, today: date, state: KateState) -> list[FeedDraft]:
    """One draft per feed card that maps to an action, in feed order."""
    verdict = engine.run(
        bank,
        user,
        today,
        consent=state.consent_for(user.id),
        dismissed=state.dismissals_for(user.id),
        last_interruption=state.last_interruption_for(user.id),
    )
    out = []
    for decision in verdict.decisions:
        moment = decision.moment
        draft = draft_for_moment(moment.type, moment.meta)
        if draft is not None:
            out.append(FeedDraft(moment.type, draft, moment.reason))
    return out
