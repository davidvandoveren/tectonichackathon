"""Abonnementenbeheer: what recurs, what got pricier, what overlaps (docs/plan.md section 5)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import BankDep, CurrentUser, TodayDep
from app.kate.subscriptions import (
    FeedbackStore,
    Subscription,
    SubscriptionFeedback,
    detect_subscriptions,
)
from app.schemas import SubscriptionFeedbackIn, SubscriptionFeedbackOut, SubscriptionOut
from app.services.insights import CustomerSignals

router = APIRouter(tags=["subscriptions"])

# Same message whether the subscription never existed or belongs to someone else (no enumeration).
_NOT_FOUND = "Subscription not found"


def get_feedback_store(request: Request) -> FeedbackStore:
    """Created on first use, so registering this router needs no change to the app lifespan."""
    store: FeedbackStore | None = getattr(request.app.state, "subscription_feedback", None)
    if store is None:
        store = FeedbackStore()
        request.app.state.subscription_feedback = store
    return store


StoreDep = Annotated[FeedbackStore, Depends(get_feedback_store)]


def _subscriptions_for(user_id: str, bank: BankDep, today: TodayDep) -> list[Subscription]:
    signals = CustomerSignals(
        user_id=user_id,
        accounts=bank.accounts_for(user_id),
        transactions=bank.all_transactions_for(user_id),
        today=today,
    )
    return detect_subscriptions(signals)


@router.get("/subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(
    user: CurrentUser, bank: BankDep, today: TodayDep, store: StoreDep
) -> list[SubscriptionOut]:
    return [
        SubscriptionOut(
            id=subscription.id,
            name=subscription.name,
            amount=subscription.amount,
            frequency=subscription.frequency,
            price_change=subscription.price_change,
            duplicate_of=subscription.duplicate_of,
            category=subscription.category,
            sensitive=False,
            still_used=(answer := store.get(user.id, subscription.id)).still_used,
            remind_to_cancel=answer.remind_to_cancel,
        )
        for subscription in _subscriptions_for(user.id, bank, today)
    ]


@router.post("/subscriptions/{subscription_id}/feedback", response_model=SubscriptionFeedbackOut)
def leave_feedback(
    subscription_id: str,
    body: SubscriptionFeedbackIn,
    user: CurrentUser,
    bank: BankDep,
    today: TodayDep,
    store: StoreDep,
) -> SubscriptionFeedbackOut:
    # Only ids we just derived from this customer's own bookings are acceptable, which rules out
    # writing feedback against someone else's subscription.
    own = {s.id for s in _subscriptions_for(user.id, bank, today)}
    if subscription_id not in own:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)

    feedback = SubscriptionFeedback(
        still_used=body.still_used, remind_to_cancel=body.remind_to_cancel
    )
    store.set(user.id, subscription_id, feedback)
    return SubscriptionFeedbackOut(
        id=subscription_id,
        still_used=feedback.still_used,
        remind_to_cancel=feedback.remind_to_cancel,
    )
