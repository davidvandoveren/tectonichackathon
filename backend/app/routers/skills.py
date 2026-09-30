"""Kate Skills API: the catalogue, consent per action, proposals and the activity log.

Every route is owner-scoped through `CurrentUser`; another customer's proposal id is a 404, exactly
like accounts. All policy lives in `SkillsService`, so this file only translates HTTP.
"""

from datetime import datetime
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.dependencies import BankDep, CurrentUser, KateStateDep, TodayDep
from app.skills.base import Action, Level, Mandate, Outcome
from app.skills.consent import Consent, ConsentError
from app.skills.feed import feed_drafts
from app.skills.service import (
    ActivityEntry,
    InvalidStateError,
    NotAllowedError,
    NotEligibleError,
    Proposal,
    ProposalNotFoundError,
    SkillsService,
    Source,
    Status,
    UnknownActionError,
)

router = APIRouter(tags=["skills"])

LevelName = Literal["off", "suggest", "prepare", "auto"]


def get_skills(request: Request) -> SkillsService:
    skills: SkillsService = request.app.state.skills
    return skills


SkillsDep = Annotated[SkillsService, Depends(get_skills)]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MandateIO(ApiModel):
    max_per_execution: str
    max_per_month: str


class ActionOut(ApiModel):
    id: str
    title: str
    description: str
    risk: str
    level: LevelName
    max_level: LevelName
    mandate: MandateIO | None


class SkillOut(ApiModel):
    id: str
    title: str
    description: str
    actions: list[ActionOut]


class ConsentIn(ApiModel):
    level: LevelName
    mandate: MandateIO | None = None


class ProposalIn(ApiModel):
    action: str = Field(min_length=1, max_length=64)
    params: dict[str, Any] = Field(default_factory=dict)
    source: Source
    reason: str = Field(min_length=1, max_length=400)


class FeedActionOut(ApiModel):
    moment: str
    action: str
    title: str
    summary: str
    level: LevelName
    can_confirm: bool


class FromMomentIn(ApiModel):
    moment: str = Field(min_length=1, max_length=64)


class OutcomeOut(ApiModel):
    kind: str
    message: str
    navigate_to: str | None
    handoff_summary: str | None


class ProposalOut(ApiModel):
    id: str
    action: str
    params: dict[str, Any]
    summary: str
    source: str
    reason: str
    status: str
    created_at: datetime
    outcome: OutcomeOut | None


class ActivityOut(ApiModel):
    at: datetime
    event: str
    action: str
    summary: str
    source: str | None
    reason: str | None


def _mandate_out(mandate: Mandate | None) -> MandateIO | None:
    if mandate is None:
        return None
    dumped = mandate.model_dump(mode="json")
    return MandateIO(**dumped)


def _action_out(action: Action, consent: Consent) -> ActionOut:
    return ActionOut(
        id=action.id,
        title=action.title,
        description=action.description,
        risk=action.risk.value,
        level=cast(LevelName, consent.level.label),
        max_level=cast(LevelName, action.ceiling.label),
        mandate=_mandate_out(consent.mandate),
    )


def _outcome(outcome: Outcome | None) -> OutcomeOut | None:
    if outcome is None:
        return None
    return OutcomeOut(
        kind=outcome.kind,
        message=outcome.message,
        navigate_to=outcome.navigate_to,
        handoff_summary=outcome.handoff_summary,
    )


def _proposal(p: Proposal) -> ProposalOut:
    return ProposalOut(
        id=p.id,
        action=p.action_id,
        params=p.params.model_dump(mode="json"),
        summary=p.summary,
        source=p.source,
        reason=p.reason,
        status=p.status,
        created_at=p.created_at,
        outcome=_outcome(p.outcome),
    )


def _activity(e: ActivityEntry) -> ActivityOut:
    return ActivityOut(
        at=e.at,
        event=e.event,
        action=e.action_id,
        summary=e.summary,
        source=e.source,
        reason=e.reason,
    )


def _first_error(exc: ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "params: invalid"
    field = ".".join(str(part) for part in errors[0]["loc"]) or "params"
    return f"{field}: {errors[0]['msg'].removeprefix('Value error, ')}"


@router.get("/skills", response_model=list[SkillOut])
def list_skills(user: CurrentUser, skills: SkillsDep) -> list[SkillOut]:
    return [
        SkillOut(
            id=skill.id,
            title=skill.title,
            description=skill.description,
            actions=[_action_out(a, skills.consent_for(user.id, a.id)) for a in skill.actions],
        )
        for skill in skills.registry.skills
    ]


@router.put("/skills/consent/{action_id}", response_model=ActionOut)
def set_consent(action_id: str, body: ConsentIn, user: CurrentUser, skills: SkillsDep) -> ActionOut:
    try:
        mandate = Mandate.model_validate(body.mandate.model_dump()) if body.mandate else None
        consent = skills.set_consent(user.id, action_id, Level.parse(body.level), mandate)
    except UnknownActionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Action not found") from exc
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, _first_error(exc)) from exc
    except ConsentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    action = skills.registry.get(action_id)
    if action is None:  # unreachable: set_consent already resolved it
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Action not found")
    return _action_out(action, consent)


@router.post("/proposals", response_model=ProposalOut, status_code=status.HTTP_201_CREATED)
def create_proposal(
    body: ProposalIn, user: CurrentUser, skills: SkillsDep, today: TodayDep
) -> ProposalOut:
    try:
        proposal = skills.propose(
            user.id, body.action, body.params, body.source, body.reason, today
        )
    except UnknownActionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Action not found") from exc
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, _first_error(exc)) from exc
    except NotAllowedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except NotEligibleError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return _proposal(proposal)


@router.get("/skills/feed-actions", response_model=list[FeedActionOut])
def feed_actions(
    user: CurrentUser, bank: BankDep, state: KateStateDep, skills: SkillsDep, today: TodayDep
) -> list[FeedActionOut]:
    """For each card in `/kate/feed` that Kate can act on: what exactly, and whether to show a
    confirm button. A card without an entry gets no button."""
    out = []
    for item in feed_drafts(bank, user, today, state):
        preview = skills.preview(user.id, item.draft.action_id, item.draft.params, today)
        if preview is None:
            continue
        out.append(
            FeedActionOut(
                moment=item.moment,
                action=preview.action.id,
                title=preview.action.title,
                summary=preview.summary,
                level=cast(LevelName, preview.level.label),
                can_confirm=preview.level >= Level.PREPARE,
            )
        )
    return out


@router.post(
    "/proposals/from-moment", response_model=ProposalOut, status_code=status.HTTP_201_CREATED
)
def proposal_from_moment(
    body: FromMomentIn,
    user: CurrentUser,
    bank: BankDep,
    state: KateStateDep,
    skills: SkillsDep,
    today: TodayDep,
) -> ProposalOut:
    """Confirm a feed card. The server recomputes the moment, so amounts cannot be forged and a
    moment that is not in this customer's feed right now does not exist (404)."""
    item = next((d for d in feed_drafts(bank, user, today, state) if d.moment == body.moment), None)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Moment not found")
    return create_proposal(
        ProposalIn(
            action=item.draft.action_id,
            params=item.draft.params,
            source="moment",
            reason=item.reason[:400],
        ),
        user,
        skills,
        today,
    )


@router.get("/proposals", response_model=list[ProposalOut])
def list_proposals(
    user: CurrentUser,
    skills: SkillsDep,
    status_: Annotated[Status | None, Query(alias="status")] = None,
) -> list[ProposalOut]:
    return [_proposal(p) for p in skills.proposals(user.id, status_)]


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalOut)
def approve_proposal(
    proposal_id: str, user: CurrentUser, skills: SkillsDep, today: TodayDep
) -> ProposalOut:
    try:
        return _proposal(skills.approve(user.id, proposal_id, today))
    except ProposalNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposal not found") from exc
    except NotAllowedError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc
    except (NotEligibleError, InvalidStateError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/proposals/{proposal_id}/decline", response_model=ProposalOut)
def decline_proposal(proposal_id: str, user: CurrentUser, skills: SkillsDep) -> ProposalOut:
    try:
        return _proposal(skills.decline(user.id, proposal_id))
    except ProposalNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposal not found") from exc
    except InvalidStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/activity", response_model=list[ActivityOut])
def list_activity(user: CurrentUser, skills: SkillsDep) -> list[ActivityOut]:
    return [_activity(e) for e in skills.activity(user.id)]
