"""The single path every channel uses to let Kate do something: propose -> (approve) -> execute.

Chat, voice, proactive moments and the UI all call `SkillsService.propose`. Consent, risk ceilings,
mandates, eligibility and parameter validation are checked here and nowhere else, so adding a
channel adds a caller, not a new policy.
"""

import secrets
import threading
from collections import defaultdict, deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from pydantic import ValidationError

from app.domain.bank import Bank, TransferError
from app.skills.base import Action, Level, Mandate, Outcome, Params, SkillContext
from app.skills.consent import Consent, ConsentStore
from app.skills.holdings import Holdings
from app.skills.registry import Registry, tool_definition

PROPOSAL_TTL = timedelta(hours=24)
MAX_REASON = 400
# Resource limits per customer, so no caller can grow the in-memory stores without bound.
MAX_OPEN_PROPOSALS = 20
MAX_KEPT_PROPOSALS = 200
MAX_ACTIVITY = 500

Status = Literal["suggested", "pending", "executed", "failed", "declined", "expired"]
Source = Literal["moment", "chat", "voice", "ui"]
Final = Literal["executed", "failed", "declined", "expired"]
Event = Literal["proposed", "suggested", "consent_changed"] | Final
_OPEN: tuple[Status, ...] = ("pending", "suggested")


class UnknownActionError(LookupError):
    pass


class ProposalNotFoundError(LookupError):
    pass


class NotAllowedError(PermissionError):
    pass


class NotEligibleError(Exception):
    pass


class InvalidStateError(Exception):
    pass


@dataclass(frozen=True)
class Proposal:
    id: str
    owner_id: str
    action_id: str
    params: Params
    summary: str
    source: Source
    reason: str
    status: Status
    created_at: datetime
    outcome: Outcome | None = None


@dataclass(frozen=True)
class Preview:
    action: Action
    summary: str
    level: Level


@dataclass(frozen=True)
class ActivityEntry:
    at: datetime
    event: Event
    action_id: str
    summary: str
    source: Source | None = None
    reason: str | None = None


class SkillsService:
    def __init__(
        self,
        bank: Bank,
        registry: Registry,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.registry = registry
        self._bank = bank
        self._clock = clock
        self._consent = ConsentStore()
        self._holdings = Holdings()
        self._proposals: dict[str, Proposal] = {}
        self._activity: defaultdict[str, deque[ActivityEntry]] = defaultdict(
            lambda: deque(maxlen=MAX_ACTIVITY)
        )
        self._lock = threading.RLock()

    # --- consent -------------------------------------------------------------------------------
    def consent_for(self, owner_id: str, action_id: str) -> Consent:
        return self._consent.get(owner_id, self._action(action_id))

    def set_consent(
        self, owner_id: str, action_id: str, level: Level, mandate: Mandate | None
    ) -> Consent:
        action = self._action(action_id)
        consent = self._consent.set(owner_id, action, level, mandate)
        self._log(owner_id, "consent_changed", action, f"{action.title}: {level.label}")
        return consent

    def tools_for(self, owner_id: str) -> list[dict[str, Any]]:
        """Tool definitions for Kate's chat: only what this customer allows (level >= suggest)."""
        return [
            tool_definition(a)
            for a in self.registry.actions()
            if self._consent.get(owner_id, a).level >= Level.SUGGEST
        ]

    # --- proposals -----------------------------------------------------------------------------
    def preview(
        self, owner_id: str, action_id: str, raw_params: Mapping[str, Any], today: date
    ) -> Preview | None:
        """What a proposal would look like, without storing anything.

        None when Kate may not use the action (`off`), the params do not validate, or the
        customer cannot do it right now: then there is simply nothing to offer.
        """
        action = self._action(action_id)
        level = self._consent.get(owner_id, action).level
        if level == Level.OFF:
            return None
        try:
            params = action.params.model_validate(dict(raw_params))
        except ValidationError:
            return None
        if action.eligible(self._context(owner_id, today), params) is not None:
            return None
        return Preview(action, action.summary(params), level)

    def propose(
        self,
        owner_id: str,
        action_id: str,
        raw_params: Mapping[str, Any],
        source: Source,
        reason: str,
        today: date,
    ) -> Proposal:
        action = self._action(action_id)
        reason = reason.strip()
        if not reason:
            raise ValueError("a reason ('Waarom zie ik dit?') is required")
        params = action.params.model_validate(dict(raw_params))  # raises ValidationError
        level = self._consent.get(owner_id, action).level
        if level == Level.OFF:
            raise NotAllowedError(f"Kate mag '{action.title}' niet gebruiken")
        ctx = self._context(owner_id, today)
        if (why_not := action.eligible(ctx, params)) is not None:
            raise NotEligibleError(why_not)

        status: Status = "suggested" if level == Level.SUGGEST else "pending"
        proposal = Proposal(
            id=f"p_{secrets.token_hex(8)}",
            owner_id=owner_id,
            action_id=action.id,
            params=params,
            summary=action.summary(params),
            source=source,
            reason=reason[:MAX_REASON],
            status=status,
            created_at=self._clock(),
        )
        with self._lock:
            if self._open_count(owner_id) >= MAX_OPEN_PROPOSALS:
                raise NotEligibleError(
                    "Er staan al te veel voorstellen open. Keur er eerst enkele goed of af."
                )
            self._proposals[proposal.id] = proposal
            self._prune(owner_id)
            self._log(
                owner_id,
                "suggested" if status == "suggested" else "proposed",
                action,
                proposal.summary,
                source,
                proposal.reason,
            )
            if level == Level.AUTO and self._within_mandate(owner_id, action, params, today):
                done = self._execute(proposal, action, ctx)
                if done.status == "failed" and (amount := action.amount_of(params)) is not None:
                    self._consent.refund(owner_id, action, amount, f"{today:%Y-%m}")
                return done
        return proposal

    def approve(self, owner_id: str, proposal_id: str, today: date) -> Proposal:
        with self._lock:
            proposal = self._pending(owner_id, proposal_id)
            action = self._action(proposal.action_id)
            if self._consent.get(owner_id, action).level < Level.PREPARE:
                raise NotAllowedError(f"Kate mag '{action.title}' niet meer voorbereiden")
            ctx = self._context(owner_id, today)
            if (why_not := action.eligible(ctx, proposal.params)) is not None:
                raise NotEligibleError(why_not)
            return self._execute(proposal, action, ctx)

    def decline(self, owner_id: str, proposal_id: str) -> Proposal:
        with self._lock:
            proposal = self._pending(owner_id, proposal_id, allow_suggested=True)
            action = self._action(proposal.action_id)
            return self._transition(proposal, action, "declined")

    def proposals(self, owner_id: str, status: Status | None = None) -> list[Proposal]:
        with self._lock:
            own = [
                self._expire_if_due(p) for p in self._proposals.values() if p.owner_id == owner_id
            ]
        own = [p for p in own if status is None or p.status == status]
        return sorted(own, key=lambda p: p.created_at, reverse=True)

    def activity(self, owner_id: str) -> list[ActivityEntry]:
        with self._lock:
            return list(reversed(self._activity.get(owner_id, [])))

    # --- internals -----------------------------------------------------------------------------
    def _action(self, action_id: str) -> Action:
        action = self.registry.get(action_id)
        if action is None:
            raise UnknownActionError(action_id)
        return action

    def _context(self, owner_id: str, today: date) -> SkillContext:
        return SkillContext(owner_id, self._bank, self._holdings, today)

    def _pending(self, owner_id: str, proposal_id: str, allow_suggested: bool = False) -> Proposal:
        proposal = self._proposals.get(proposal_id)
        if proposal is None or proposal.owner_id != owner_id:
            raise ProposalNotFoundError(proposal_id)
        proposal = self._expire_if_due(proposal)
        allowed = ("pending", "suggested") if allow_suggested else ("pending",)
        if proposal.status not in allowed:
            raise InvalidStateError(f"proposal is {proposal.status}")
        return proposal

    def _open_count(self, owner_id: str) -> int:
        own = [p for p in list(self._proposals.values()) if p.owner_id == owner_id]
        return sum(1 for p in own if self._expire_if_due(p).status in _OPEN)

    def _prune(self, owner_id: str) -> None:
        """Forget the oldest finished proposals beyond MAX_KEPT_PROPOSALS; open ones always stay."""
        own = [p for p in self._proposals.values() if p.owner_id == owner_id]
        excess = len(own) - MAX_KEPT_PROPOSALS
        if excess <= 0:
            return
        finished = sorted((p for p in own if p.status not in _OPEN), key=lambda p: p.created_at)
        for proposal in finished[:excess]:
            del self._proposals[proposal.id]

    def _expire_if_due(self, proposal: Proposal) -> Proposal:
        due = self._clock() - proposal.created_at > PROPOSAL_TTL
        if proposal.status in ("pending", "suggested") and due:
            return self._transition(proposal, self._action(proposal.action_id), "expired")
        return proposal

    def _within_mandate(self, owner_id: str, action: Action, params: Params, today: date) -> bool:
        amount = action.amount_of(params)
        if amount is None:
            return True
        return self._consent.try_spend(owner_id, action, amount, f"{today:%Y-%m}")

    def _execute(self, proposal: Proposal, action: Action, ctx: SkillContext) -> Proposal:
        try:
            outcome = action.execute(ctx, proposal.params)
        except (TransferError, LookupError) as exc:
            failed = replace(proposal, outcome=Outcome("done", f"Dat lukte niet: {exc}"))
            return self._transition(failed, action, "failed")
        return self._transition(replace(proposal, outcome=outcome), action, "executed")

    def _transition(self, proposal: Proposal, action: Action, status: Final) -> Proposal:
        updated = replace(proposal, status=status)
        self._proposals[proposal.id] = updated
        self._log(
            proposal.owner_id, status, action, proposal.summary, proposal.source, proposal.reason
        )
        return updated

    def _log(
        self,
        owner_id: str,
        event: Event,
        action: Action,
        summary: str,
        source: Source | None = None,
        reason: str | None = None,
    ) -> None:
        with self._lock:
            self._activity[owner_id].append(
                ActivityEntry(self._clock(), event, action.id, summary, source, reason)
            )
