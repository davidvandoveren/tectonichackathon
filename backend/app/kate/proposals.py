"""Kate's chat proposes through Kate Skills: one proposal system for the chat and the feed.

A transfer or advisor hand-off suggested in the chat becomes a real Skills proposal, so it follows
the customer's action consent (off / suggest / prepare / auto), shows up in the activity log and
is confirmed or declined the same way as a feed card. Kate still never pays a third party:
`payments.transfer` only pre-fills the normal transfer screen.
"""

import logging
from dataclasses import dataclass
from datetime import date

from pydantic import ValidationError

from app.kate.assistant import AdvisorHandoffAction, NoAction, TransferAction
from app.skills.service import NotAllowedError, NotEligibleError, SkillsService

logger = logging.getLogger("kbc_poc.kate")

TRANSFER_ACTION = "payments.transfer"
ADVISOR_ACTION = "advisor.book_call"
MAX_TOPIC = 140


@dataclass(frozen=True)
class ChatProposal:
    """What became of Kate's suggestion in the Skills system."""

    proposal_id: str | None
    status: str | None  # suggested | pending | executed | failed ... (Skills statuses)
    allowed: bool  # False: the customer switched this action off for Kate


def propose_from_chat(
    skills: SkillsService,
    owner_id: str,
    action: NoAction | TransferAction | AdvisorHandoffAction,
    message: str,
    today: date,
) -> ChatProposal | None:
    if isinstance(action, TransferAction):
        action_id = TRANSFER_ACTION
        params: dict[str, object] = {
            "to_name": action.to_name,
            "amount": f"{action.amount:.2f}",
            "description": action.description,
        }
    elif isinstance(action, AdvisorHandoffAction):
        action_id = ADVISOR_ACTION
        params = {"topic": action.summary[:MAX_TOPIC]}
    else:
        return None

    reason = f'Je vroeg het in de chat: "{" ".join(message.split())[:120]}"'
    try:
        proposal = skills.propose(owner_id, action_id, params, "chat", reason, today)
    except NotAllowedError:
        return ChatProposal(None, None, allowed=False)
    except (NotEligibleError, ValidationError, ValueError, LookupError) as exc:
        # Still show the safe fallback (pre-filled screen / suggestion) without a proposal.
        logger.info("Chat proposal not created: %s", type(exc).__name__)
        return ChatProposal(None, None, allowed=True)
    return ChatProposal(proposal.id, proposal.status, allowed=True)
