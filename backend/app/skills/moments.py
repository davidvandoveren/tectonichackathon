"""Moments Engine -> concrete actions (docs/design/kate-skills.md §3.1).

The engine decides *why now* and *how sure*; this table decides *what exactly Kate offers*. It only
knows moment types and their `meta` strings, not the engine's code, so both evolve independently.
A moment that maps to nothing, or whose meta does not validate, simply gets no action.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from app.skills.registry import Registry, default_registry

Meta = Mapping[str, str]


@dataclass(frozen=True)
class Draft:
    action_id: str
    params: dict[str, Any]


def _buffer_goal(meta: Meta) -> dict[str, Any]:
    salary = Decimal(meta["amount"])
    monthly = (salary * Decimal("0.10")).quantize(Decimal("1"), ROUND_DOWN)
    return {"name": "Buffer", "target": f"{salary * 3:.2f}", "monthly": f"{monthly:.2f}"}


MAPPING: dict[str, tuple[str, Callable[[Meta], dict[str, Any]]]] = {
    "savings_habit_automatable": (
        "payments.standing_order",
        lambda m: {"amount": m["amount"], "day": min(int(m["day"]), 28)},
    ),
    "first_salary": ("savings.create_goal", _buffer_goal),
    "idle_savings": ("investing.prepare_meeting", lambda _: {}),
    "cashflow_risk": ("savings.move_to_current", lambda m: {"amount": m["shortfall"]}),
    "card_package_gap": ("cards.add_package", lambda _: {"package": "reis"}),
    "card_package_waste": ("cards.drop_package", lambda m: {"package": m.get("package", "luxe")}),
    "deal_match": ("deals.activate", lambda m: {"category": m["category"]}),
    "moving_house": ("insurance.home_quote", lambda _: {"reason": "moving"}),
}


def draft_for_moment(
    moment_type: str, meta: Meta, registry: Registry | None = None
) -> Draft | None:
    entry = MAPPING.get(moment_type)
    if entry is None:
        return None
    action_id, build = entry
    action = (registry or default_registry()).get(action_id)
    if action is None:
        return None
    try:
        params = build(meta)
        action.params.model_validate(params)
    except (KeyError, ValueError, InvalidOperation, ValidationError):
        return None
    return Draft(action_id, params)
