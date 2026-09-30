"""Jury dashboard: what Kate decides across a whole population, and why.

Runs the real Moments Engine (`app.moments.engine.run`, unchanged) once per synthetic customer
and aggregates the verdicts. Nothing on the dashboard is typed in by hand: every number is counted
from engine output, including how many customers Kate deliberately left alone.
"""

import statistics
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date

from app.domain.bank import Bank
from app.domain.models import User
from app.moments import engine
from app.moments.arbitration import INTERRUPTIVE_CHANNELS
from app.moments.signals import extract_signals
from app.moments.state import KateState
from app.population.generator import ARCHETYPE_LABELS, generate

KBC_CUSTOMERS = 2_300_000


@dataclass
class PopulationSummary:
    size: int
    today: date
    with_message: int = 0
    interrupted: int = 0
    nothing_at_all: int = 0
    held_back: int = 0
    by_moment: Counter[str] = field(default_factory=Counter)
    by_channel: Counter[str] = field(default_factory=Counter)
    silence_reasons: Counter[str] = field(default_factory=Counter)
    by_archetype: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    timings_ms: list[float] = field(default_factory=list)

    @property
    def silent(self) -> int:
        return self.nothing_at_all + self.held_back

    def percentile_ms(self, fraction: float) -> float:
        if not self.timings_ms:
            return 0.0
        ordered = sorted(self.timings_ms)
        return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]

    @property
    def mean_ms(self) -> float:
        return statistics.fmean(self.timings_ms) if self.timings_ms else 0.0

    @property
    def full_bank_cpu_minutes(self) -> float:
        """Engine time for all KBC customers on one CPU core (no LLM involved)."""
        return self.mean_ms * KBC_CUSTOMERS / 1000 / 60


def summarise(size: int, today: date, seed: int = 42) -> PopulationSummary:
    summary = PopulationSummary(size=size, today=today)
    for customer in generate(size, today, seed):
        started = time.perf_counter()
        verdict = engine.run(customer.bank, customer.user, today)
        summary.timings_ms.append((time.perf_counter() - started) * 1000)

        archetype = summary.by_archetype[customer.archetype]
        archetype["customers"] += 1
        for silence in verdict.silenced:
            summary.silence_reasons[silence.reason_code] += 1
        if not verdict.decisions:
            if verdict.silenced:
                summary.held_back += 1
                archetype["held_back"] += 1
            else:
                summary.nothing_at_all += 1
                archetype["nothing"] += 1
            continue
        summary.with_message += 1
        archetype["with_message"] += 1
        if any(d.channel in INTERRUPTIVE_CHANNELS for d in verdict.decisions):
            summary.interrupted += 1
            archetype["interrupted"] += 1
        for decision in verdict.decisions:
            summary.by_moment[decision.moment.type] += 1
            summary.by_channel[decision.channel] += 1
            archetype[f"moment:{decision.moment.type}"] += 1
    return summary


@dataclass(frozen=True)
class Trace:
    """Signal → situation → action → reason, for one real demo persona."""

    username: str
    display_name: str
    persona: str
    signals: list[dict[str, str]]
    moments: list[dict[str, str]]
    actions: list[dict[str, str]]
    silenced: list[dict[str, str]]


def trace(bank: Bank, user: User, today: date, state: KateState) -> Trace:
    consent = state.consent_for(user.id)
    led = engine.build_ledger(bank, user, today)
    signals = extract_signals(led, consent=consent)
    verdict = engine.run(
        bank,
        user,
        today,
        consent=consent,
        dismissed=state.dismissals_for(user.id),
        last_interruption=state.last_interruption_for(user.id),
    )
    result = engine.experience(
        bank,
        user,
        today,
        consent=consent,
        dismissed=state.dismissals_for(user.id),
        last_interruption=state.last_interruption_for(user.id),
    )
    return Trace(
        username=user.username,
        display_name=f"{user.first_name} {user.last_name}",
        persona=user.persona,
        signals=[{"type": s.type, "evidence": s.evidence} for s in signals],
        moments=[
            {
                "type": d.moment.type,
                "urgency": d.moment.urgency,
                "confidence": f"{d.moment.confidence:.2f}",
            }
            for d in verdict.decisions
        ],
        actions=[
            {
                "title": item.title,
                "channel": item.channel,
                "urgency": str(item.urgency),
                "reason": item.reason,
            }
            for item in result.items
        ],
        silenced=[
            {"moment": s.moment_type, "reason_code": s.reason_code, "reason": s.reason}
            for s in verdict.silenced
        ],
    )


def archetype_rows(summary: PopulationSummary) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for name, counts in sorted(summary.by_archetype.items(), key=lambda kv: -kv[1]["customers"]):
        top = _top_moments(counts)
        rows.append(
            {
                "archetype": name,
                "label": ARCHETYPE_LABELS.get(name, name),
                "customers": counts["customers"],
                "with_message": counts["with_message"],
                "interrupted": counts["interrupted"],
                "silent": counts["nothing"] + counts["held_back"],
                "top_moments": top,
            }
        )
    return rows


def _top_moments(counts: Mapping[str, int], limit: int = 2) -> list[str]:
    moments = [(k.removeprefix("moment:"), v) for k, v in counts.items() if k.startswith("moment:")]
    return [name for name, _ in sorted(moments, key=lambda kv: -kv[1])[:limit]]


def ordered(counter: Counter[str], keys: Iterable[str] = ()) -> dict[str, int]:
    """Stable order: known keys first (so the UI can rely on it), then the rest by count."""
    result = {key: counter.get(key, 0) for key in keys}
    for key, value in counter.most_common():
        result.setdefault(key, value)
    return result
