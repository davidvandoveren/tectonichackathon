"""Demo-only admin endpoints.

Gated by `AdminUser`, which answers 404 for anyone else, so an ordinary customer cannot even
learn that these exist. Off entirely unless `ADMIN_USERNAMES` is configured.
"""

from datetime import timedelta

from fastapi import APIRouter, HTTPException, status

from app.dependencies import AdminUser, BankDep, KateStateDep, TodayDep
from app.moments import engine, timemachine
from app.moments.schemas import FeedOut, TimeMachineIn, TimeMachineOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/time-machine", response_model=TimeMachineOut)
def time_machine(
    request: TimeMachineIn,
    admin: AdminUser,
    bank: BankDep,
    state: KateStateDep,
    today: TodayDep,
) -> TimeMachineOut:
    """Move the demo clock forward and show what Kate does about it.

    The persona's own recurring income is projected into the window, so the app stays coherent:
    balances, transactions and the feed all move together. With `salary_missing` the projection
    is skipped, which is how the demo shows an escalation for money that never arrived.
    """
    target = admin
    if request.username is not None and request.username != admin.username:
        found = bank.find_user_by_username(request.username)
        if found is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
        target = found

    injected = timemachine.project(bank, target, today, request.days, request.scenario)
    offset = state.shift_clock(request.days)
    shifted_today = today + timedelta(days=request.days)

    result = engine.experience(
        bank,
        target,
        shifted_today,
        consent=state.consent_for(target.id),
        dismissed=state.dismissals_for(target.id),
        last_interruption=state.last_interruption_for(target.id),
    )
    return TimeMachineOut(
        days_shifted=request.days,
        clock_offset_days=offset,
        today=shifted_today,
        username=target.username,
        injected=injected,
        feed=FeedOut.of(result),
    )
