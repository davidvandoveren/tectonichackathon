"""Beleggen met Kate for the logged-in customer.

Every read and write is scoped to the authenticated user; the only money movement is a transfer
between the customer's own savings account and their own Bolero account, in steps they confirmed.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import Field

from app.dependencies import CurrentUser, TodayDep
from app.domain.models import User
from app.invest.catalog import CATALOG, TOB_RATE, price_on
from app.invest.guide import (
    Answers,
    Goal,
    Horizon,
    Knowledge,
    Reaction,
    check_mix,
    drop_example,
    fit_for,
)
from app.invest.service import InvestError, InvestService
from app.routers.notifications import DispatcherDep
from app.schemas import ApiModel, Money

router = APIRouter(prefix="/invest", tags=["invest"])

EtfId = Annotated[str, Field(pattern=r"^etf_[a-z]{2,12}$")]
Weights = Annotated[dict[EtfId, Annotated[int, Field(ge=1, le=100)]], Field(max_length=8)]


def get_invest(request: Request) -> InvestService:
    service: InvestService = request.app.state.invest
    return service


InvestDep = Annotated[InvestService, Depends(get_invest)]


# --- shapes --------------------------------------------------------------------------------------
class HealthOut(ApiModel):
    status: Literal["ready", "caution", "build_buffer"]
    savings: Money
    monthly_expenses: Money
    monthly_income: Money
    buffer: Money
    investable: Money
    notes: list[str]


class AnswersIn(ApiModel):
    goal: Goal
    horizon: Horizon
    knowledge: Knowledge
    drop_reaction: Reaction


class DirectionOut(ApiModel):
    profile: Literal["defensive", "neutral", "dynamic"]
    shares_percent: int
    bonds_percent: int
    headline: str
    explanation: str
    warnings: list[str]
    suitable: bool


class EtfOut(ApiModel):
    id: str
    name: str
    index: str
    asset_class: Literal["shares", "bonds"]
    role: Literal["core", "satellite", "niche", "complex"]
    region: str
    ter_percent: Decimal
    risk_class: int
    distributing: bool
    holdings: int
    explanation: str
    price: Money
    fit: Literal["fits", "addition", "caution", "not_for_you"] | None
    fit_note: str | None
    allowed: bool


class MixIn(ApiModel):
    weights: Weights


class MixOut(ApiModel):
    shares_percent: int
    yearly_cost_percent: Decimal
    warnings: list[str]
    blocked: list[str]
    needs_acknowledgement: bool


class PlanIn(ApiModel):
    weights: Weights
    total: Decimal = Field(gt=0, le=Decimal(1_000_000), max_digits=9, decimal_places=2)
    months: int = Field(ge=1, le=36)
    accept_risks: bool = False


class StepOut(ApiModel):
    number: int
    on: date
    amount: Money
    tax: Money


class PlanOut(ApiModel):
    status: Literal["active", "paused", "stopped", "completed"]
    weights: dict[str, int]
    total: Money
    months: int
    monthly: Money
    invested: Money
    next_on: date | None
    buffer: Money
    pause_reason: str | None
    steps: list[StepOut]


class HoldingOut(ApiModel):
    etf_id: str
    name: str
    units: Decimal
    invested: Money
    value: Money


class PortfolioOut(ApiModel):
    invested: Money
    value: Money
    holdings: list[HoldingOut]
    drop_20_example: Money


class OverviewOut(ApiModel):
    health: HealthOut
    answers: AnswersIn | None
    direction: DirectionOut | None
    catalog: list[EtfOut]
    plan: PlanOut | None
    portfolio: PortfolioOut
    tob_percent: Decimal
    simulated: bool = True


# --- mapping -------------------------------------------------------------------------------------
def _overview(user: User, service: InvestService, today: date) -> OverviewOut:
    customer = service.state(user.id)
    health = service.health(user.id, today)
    direction = customer.direction
    knowledge = customer.answers.knowledge if customer.answers else "none"
    catalog = []
    for etf in CATALOG:
        fit = fit_for(etf, direction, knowledge) if direction else None
        catalog.append(
            EtfOut(
                id=etf.id,
                name=etf.name,
                index=etf.index,
                asset_class=etf.asset_class,
                role=etf.role,
                region=etf.region,
                ter_percent=etf.ter_percent,
                risk_class=etf.risk_class,
                distributing=etf.distributing,
                holdings=etf.holdings,
                explanation=etf.explanation,
                price=price_on(etf, today),
                fit=fit.tag if fit else None,
                fit_note=fit.note if fit else None,
                allowed=fit.allowed if fit else etf.role != "complex",
            )
        )
    plan = customer.plan
    holdings = [
        HoldingOut(
            etf_id=h.etf_id,
            name=next(e.name for e in CATALOG if e.id == h.etf_id),
            units=h.units,
            invested=h.invested,
            value=(h.units * price_on(next(e for e in CATALOG if e.id == h.etf_id), today)),
        )
        for h in customer.holdings.values()
    ]
    invested = sum((h.invested for h in holdings), Decimal(0))
    value = sum((h.value for h in holdings), Decimal(0))
    shares = direction.shares_percent if direction else 60
    return OverviewOut(
        health=HealthOut(
            status=health.status,
            savings=health.savings,
            monthly_expenses=health.monthly_expenses,
            monthly_income=health.monthly_income,
            buffer=health.buffer,
            investable=health.investable,
            notes=list(health.notes),
        ),
        answers=AnswersIn(**vars(customer.answers)) if customer.answers else None,
        direction=DirectionOut(**{**vars(direction), "warnings": list(direction.warnings)})
        if direction
        else None,
        catalog=catalog,
        plan=PlanOut(
            status=plan.status,
            weights=plan.weights,
            total=plan.total,
            months=plan.months,
            monthly=plan.monthly,
            invested=plan.invested,
            next_on=plan.next_on if plan.status in ("active", "paused") else None,
            buffer=plan.buffer,
            pause_reason=plan.pause_reason,
            steps=[
                StepOut(number=s.number, on=s.on, amount=s.amount, tax=s.tax) for s in plan.steps
            ],
        )
        if plan
        else None,
        portfolio=PortfolioOut(
            invested=invested,
            value=value,
            holdings=holdings,
            drop_20_example=drop_example(value or health.investable, shares),
        ),
        tob_percent=TOB_RATE * 100,
    )


def _bad(exc: InvestError) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))


# --- endpoints -----------------------------------------------------------------------------------
@router.get("", response_model=OverviewOut)
def overview(
    user: CurrentUser, today: TodayDep, service: InvestDep, dispatcher: DispatcherDep
) -> OverviewOut:
    dispatcher.dispatch_for(user, today)  # run any due plan steps first, reported in the inbox
    return _overview(user, service, today)


@router.post("/answers", response_model=OverviewOut)
def answers(body: AnswersIn, user: CurrentUser, today: TodayDep, service: InvestDep) -> OverviewOut:
    service.answer(user.id, Answers(**body.model_dump()))
    return _overview(user, service, today)


@router.post("/check", response_model=MixOut)
def check(body: MixIn, user: CurrentUser, service: InvestDep) -> MixOut:
    """Preview of Kate's comments on a mix. Changes nothing."""
    customer = service.state(user.id)
    if customer.direction is None or customer.answers is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Beantwoord eerst de vragen")
    result = check_mix(body.weights, customer.direction, customer.answers.knowledge)
    return MixOut(
        shares_percent=result.shares_percent,
        yearly_cost_percent=result.yearly_cost_percent,
        warnings=list(result.warnings),
        blocked=list(result.blocked),
        needs_acknowledgement=result.needs_acknowledgement,
    )


@router.post("/plan", response_model=OverviewOut, status_code=status.HTTP_201_CREATED)
def start_plan(
    body: PlanIn,
    user: CurrentUser,
    today: TodayDep,
    service: InvestDep,
    dispatcher: DispatcherDep,
) -> OverviewOut:
    try:
        _, events = service.start_plan(
            user, dict(body.weights), body.total, body.months, body.accept_risks, today
        )
    except InvestError as exc:
        raise _bad(exc) from exc
    dispatcher.deliver_events(user, events, today)
    return _overview(user, service, today)


@router.post("/plan/{action}", response_model=OverviewOut)
def change_plan(
    action: Literal["pause", "resume", "stop"],
    user: CurrentUser,
    today: TodayDep,
    service: InvestDep,
    dispatcher: DispatcherDep,
) -> OverviewOut:
    try:
        if action == "resume":
            service.resume(user.id, today)
        else:
            {"pause": service.pause, "stop": service.stop}[action](user.id)
    except LookupError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Geen plan om dit op toe te passen") from exc
    if action == "resume":
        dispatcher.dispatch_for(user, today)  # a step that was due runs right away
    return _overview(user, service, today)
