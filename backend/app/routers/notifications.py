"""Kate's inbox for the logged-in customer: what she sent, why, and read state."""

from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, status

from app.dependencies import CurrentUser, TodayDep
from app.notifications.dispatcher import Dispatcher
from app.notifications.store import Notification, NotificationStore
from app.schemas import ApiModel

router = APIRouter(prefix="/kate/notifications", tags=["kate"])


def get_dispatcher(request: Request) -> Dispatcher:
    dispatcher: Dispatcher = request.app.state.dispatcher
    return dispatcher


def get_store(request: Request) -> NotificationStore:
    store: NotificationStore = request.app.state.notifications
    return store


DispatcherDep = Annotated[Dispatcher, Depends(get_dispatcher)]
StoreDep = Annotated[NotificationStore, Depends(get_store)]


class NotificationOut(ApiModel):
    id: str
    source: str
    title: str
    body: str
    reason: str
    channel: Literal["feed", "push", "sms", "call"]
    cta_label: str
    cta_target: str
    sent_on: date
    created_at: datetime
    read: bool


class InboxOut(ApiModel):
    unread: int
    items: list[NotificationOut]


def _out(n: Notification) -> NotificationOut:
    return NotificationOut.model_validate(n, from_attributes=True)


@router.get("", response_model=InboxOut)
def inbox(
    user: CurrentUser, today: TodayDep, dispatcher: DispatcherDep, store: StoreDep
) -> InboxOut:
    """Opening the inbox also lets Kate catch up for this customer (the background sweep does
    the same for everyone), so nothing depends on timing in a demo."""
    dispatcher.dispatch_for(user, today)
    items = store.for_user(user.id)
    return InboxOut(unread=sum(1 for n in items if not n.read), items=[_out(n) for n in items])


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: Annotated[str, Path(pattern=r"^nt_[0-9a-f]{12}$")],
    user: CurrentUser,
    store: StoreDep,
) -> NotificationOut:
    found = store.mark_read(user.id, notification_id)
    if found is None:  # unknown or someone else's: same answer
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return _out(found)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(user: CurrentUser, store: StoreDep) -> Response:
    store.mark_all_read(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
