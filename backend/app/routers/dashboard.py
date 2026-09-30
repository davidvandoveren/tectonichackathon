"""Jury dashboard (demo only): Kate's decisions across a synthetic population + demo personas.

Behind the existing `AdminUser` gate, which answers 404 to everyone else. The population run is
cached per (size, day), so opening the dashboard twice does not redo the work.
"""

import threading
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict

from app.dependencies import AdminUser, BankDep, KateStateDep, TodayDep
from app.moments.arbitration import SILENCE_REASONS
from app.population.dashboard import (
    KBC_CUSTOMERS,
    PopulationSummary,
    archetype_rows,
    ordered,
    summarise,
    trace,
)

router = APIRouter(prefix="/admin", tags=["admin"])

MAX_SIZE = 10_000
CHANNELS = ("feed", "push", "sms", "call")
_lock = threading.Lock()


class _Out(BaseModel):
    model_config = ConfigDict(frozen=True)


class PopulationOut(_Out):
    size: int
    with_message: int
    interrupted: int
    silent: int
    nothing_at_all: int
    held_back: int
    by_moment: dict[str, int]
    by_channel: dict[str, int]
    silence_reasons: dict[str, int]
    silence_labels: dict[str, str]
    archetypes: list[dict[str, object]]
    p50_ms: float
    p95_ms: float
    p99_ms: float
    kbc_customers: int
    full_bank_cpu_minutes: float


class TraceOut(_Out):
    username: str
    display_name: str
    persona: str
    signals: list[dict[str, str]]
    moments: list[dict[str, str]]
    actions: list[dict[str, str]]
    silenced: list[dict[str, str]]


class DashboardOut(_Out):
    today: date
    population: PopulationOut
    personas: list[TraceOut]


def _cached_summary(request: Request, size: int, today: date) -> PopulationSummary:
    cache: dict[tuple[int, date], PopulationSummary] = request.app.state.__dict__.setdefault(
        "dashboard_cache", {}
    )
    key = (size, today)
    with _lock:  # one run at a time; a second request waits and then reuses the result
        if key not in cache:
            cache.clear()  # only the latest run is kept
            cache[key] = summarise(size, today)
        return cache[key]


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(
    request: Request,
    _: AdminUser,
    bank: BankDep,
    state: KateStateDep,
    today: TodayDep,
    size: Annotated[int, Query(ge=100, le=MAX_SIZE)] = MAX_SIZE,
) -> DashboardOut:
    # `today` already follows the time machine, so the dashboard matches the demo feed.
    shifted = today
    summary = _cached_summary(request, size, shifted)
    population = PopulationOut(
        size=summary.size,
        with_message=summary.with_message,
        interrupted=summary.interrupted,
        silent=summary.silent,
        nothing_at_all=summary.nothing_at_all,
        held_back=summary.held_back,
        by_moment=ordered(summary.by_moment),
        by_channel=ordered(summary.by_channel, CHANNELS),
        silence_reasons=ordered(summary.silence_reasons),
        silence_labels=dict(SILENCE_REASONS),
        archetypes=archetype_rows(summary),
        p50_ms=round(summary.percentile_ms(0.50), 3),
        p95_ms=round(summary.percentile_ms(0.95), 3),
        p99_ms=round(summary.percentile_ms(0.99), 3),
        kbc_customers=KBC_CUSTOMERS,
        full_bank_cpu_minutes=round(summary.full_bank_cpu_minutes, 1),
    )
    personas = [
        TraceOut(**trace(bank, user, shifted, state).__dict__) for user in bank.list_users()
    ]
    return DashboardOut(today=shifted, population=population, personas=personas)
