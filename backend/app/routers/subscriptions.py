"""Subscription manager for the logged-in customer."""

import secrets
from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import Field, field_validator

from app.dependencies import BankDep, CurrentUser, TodayDep
from app.domain.models import User
from app.schemas import ApiModel, Money
from app.subscriptions.detect import Subscription, detect, manual_subscription, subscription_id
from app.subscriptions.store import Feedback, FeedbackStore

router = APIRouter(tags=["subscriptions"])

REMIND_DAYS_BEFORE = 3
_NOT_FOUND = "Subscription not found"
ID_PATTERN = r"^sub_[0-9a-f]{12}$"


def get_feedback_store(request: Request) -> FeedbackStore:
    store: FeedbackStore = request.app.state.subscription_feedback
    return store


StoreDep = Annotated[FeedbackStore, Depends(get_feedback_store)]


class SubscriptionOut(ApiModel):
    id: str
    name: str
    group: str | None
    amount: Money
    previous_amount: Money | None
    yearly_cost: Money
    frequency: Literal["monthly"]
    first_seen: date
    last_charged: date
    next_expected: date
    flags: list[Literal["price_increase", "duplicate", "trial_converted"]]
    duplicate_of: list[str]
    reason: str
    status: Literal["unknown", "in_use", "cancel_reminder"]
    remind_on: date | None
    source: Literal["detected", "manual"]
    # Detected recently: shown with "Nieuw gedetecteerd · Klopt dit niet? Verwijder".
    is_new: bool


class SubscriptionsOut(ApiModel):
    subscriptions: list[SubscriptionOut]
    monthly_total: Money
    yearly_total: Money
    # Yearly cost of the ones the customer said they no longer use.
    yearly_savings: Money
    # Sensitive subscriptions we saw but deliberately do not analyse or show.
    hidden_sensitive: int
    # Removed by the customer ("Klopt dit niet?"); can be restored.
    dismissed: int


class FeedbackIn(ApiModel):
    still_used: bool
    remind_to_cancel: bool = False


class DismissIn(ApiModel):
    dismissed: bool


class ManualIn(ApiModel):
    name: str = Field(min_length=1, max_length=60)
    amount: Decimal = Field(gt=0, le=Decimal("1000.00"), max_digits=6, decimal_places=2)
    next_charge: date | None = None

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned or any(not char.isprintable() for char in cleaned):
            raise ValueError("Invalid name")
        return cleaned


def _own_subscriptions(
    user: User, bank: BankDep, today: date, store: FeedbackStore, *, include_dismissed: bool = False
) -> tuple[list[Subscription], int]:
    result = detect(
        user.id,
        bank.all_transactions_for(user.id),  # own data only
        today,
        dismissed=frozenset() if include_dismissed else store.dismissed(user.id),
        manual=store.manual(user.id),
    )
    return result.subscriptions, result.hidden_sensitive


def _overview(user: User, bank: BankDep, today: date, store: FeedbackStore) -> "SubscriptionsOut":
    subs, hidden = _own_subscriptions(user, bank, today, store)
    items = [_out(sub, store.get(user.id, sub.id)) for sub in subs]
    return SubscriptionsOut(
        subscriptions=items,
        monthly_total=sum((s.amount for s in subs), Decimal(0)),
        yearly_total=sum((s.yearly_cost for s in subs), Decimal(0)),
        yearly_savings=sum(
            (i.yearly_cost for i in items if i.status == "cancel_reminder"), Decimal(0)
        ),
        hidden_sensitive=hidden,
        dismissed=len(store.dismissed(user.id)),
    )


def _out(sub: Subscription, feedback: Feedback) -> SubscriptionOut:
    return SubscriptionOut(
        id=sub.id,
        name=sub.name,
        group=sub.group,
        amount=sub.amount,
        previous_amount=sub.previous_amount,
        yearly_cost=sub.yearly_cost,
        frequency=sub.frequency,
        first_seen=sub.first_seen,
        last_charged=sub.last_charged,
        next_expected=sub.next_expected,
        flags=sub.flags,
        duplicate_of=sub.duplicate_of,
        reason=sub.reason,
        status=feedback.status,
        remind_on=feedback.remind_on,
        source=sub.source,
        is_new=sub.is_new,
    )


@router.get("/subscriptions", response_model=SubscriptionsOut)
def list_subscriptions(
    user: CurrentUser, bank: BankDep, today: TodayDep, store: StoreDep
) -> SubscriptionsOut:
    return _overview(user, bank, today, store)


@router.post("/subscriptions", response_model=SubscriptionsOut, status_code=status.HTTP_201_CREATED)
def add_subscription(
    body: ManualIn, user: CurrentUser, bank: BankDep, today: TodayDep, store: StoreDep
) -> SubscriptionsOut:
    next_charge = body.next_charge or today + timedelta(days=30)
    if not today <= next_charge <= today + timedelta(days=366):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "next_charge out of range")
    sub = manual_subscription(
        subscription_id(user.id, f"manual:{secrets.token_hex(8)}"),
        body.name,
        body.amount,
        next_charge,
        today,
    )
    if not store.add_manual(user.id, sub):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Too many subscriptions")
    return _overview(user, bank, today, store)


@router.post("/subscriptions/{subscription_id}/dismiss", response_model=SubscriptionsOut)
def dismiss_subscription(
    subscription_id: Annotated[str, Path(pattern=ID_PATTERN)],
    body: DismissIn,
    user: CurrentUser,
    bank: BankDep,
    today: TodayDep,
    store: StoreDep,
) -> SubscriptionsOut:
    """ "Klopt dit niet? Verwijder" with one click, and undo (`dismissed: false`)."""
    all_own, _ = _own_subscriptions(user, bank, today, store, include_dismissed=True)
    if not any(s.id == subscription_id for s in all_own):
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
    if body.dismissed:
        store.dismiss(user.id, subscription_id)
    else:
        store.restore(user.id, subscription_id)
    return _overview(user, bank, today, store)


@router.post("/subscriptions/{subscription_id}/feedback", response_model=SubscriptionOut)
def subscription_feedback(
    subscription_id: Annotated[str, Path(pattern=ID_PATTERN)],
    body: FeedbackIn,
    user: CurrentUser,
    bank: BankDep,
    today: TodayDep,
    store: StoreDep,
) -> SubscriptionOut:
    subs, _ = _own_subscriptions(user, bank, today, store)
    sub = next((s for s in subs if s.id == subscription_id), None)
    if sub is None:  # unknown or someone else's: same answer, no enumeration
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
    if body.still_used:
        feedback = Feedback("in_use")
    elif body.remind_to_cancel:
        remind_on = max(today, sub.next_expected - timedelta(days=REMIND_DAYS_BEFORE))
        feedback = Feedback("cancel_reminder", remind_on)
    else:
        feedback = Feedback("unknown")
    store.set(user.id, sub.id, feedback)
    return _out(sub, feedback)
