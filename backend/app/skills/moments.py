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


# The engine reports the spending category it saw; Kate Deals has its own categories.
DEAL_FOR_CATEGORY = {
    "transport": "fuel",
    "groceries": "groceries",
    "leisure": "dining",
    "fuel": "fuel",
    "travel": "travel",
    "dining": "dining",
}


class _NoAction(ValueError):
    """The moment is real, but there is nothing concrete for Kate to offer."""


def _standing_order(meta: Meta) -> dict[str, Any]:
    # Standing orders run on day 1-28 so they exist in every month.
    day = int(Decimal(meta.get("day_of_month") or meta["day"]))
    return {"amount": meta["amount"], "day": max(1, min(day, 28))}


def _buffer_goal(meta: Meta) -> dict[str, Any]:
    salary = Decimal(meta["amount"])
    monthly = (salary * Decimal("0.10")).quantize(Decimal("1"), ROUND_DOWN)
    return {"name": "Buffer", "target": f"{salary * 3:.2f}", "monthly": f"{monthly:.2f}"}


def _top_up(meta: Meta) -> dict[str, Any]:
    shortfall = Decimal(meta["obligation"]) - Decimal(meta["balance"])
    if shortfall <= 0:
        raise _NoAction
    return {"amount": f"{shortfall:.2f}"}


def _deal(meta: Meta) -> dict[str, Any]:
    category = DEAL_FOR_CATEGORY.get(meta["category"])
    if category is None:
        raise _NoAction
    return {"category": category}


def _missing_income(meta: Meta) -> dict[str, Any]:
    return {
        "topic": f"Mijn inkomen van {meta['counterparty']} is {meta['days_overdue']} dagen te laat"
    }


MAPPING: dict[str, tuple[str, Callable[[Meta], dict[str, Any]]]] = {
    "savings_habit_automatable": ("payments.standing_order", _standing_order),
    "first_salary": ("savings.create_goal", _buffer_goal),
    "idle_savings": ("investing.prepare_meeting", lambda _: {}),
    "cashflow_risk": ("savings.move_to_current", _top_up),
    "income_missing": ("advisor.book_call", _missing_income),
    "card_package_gap": ("cards.add_package", lambda _: {"package": "reis"}),
    "card_package_waste": ("cards.drop_package", lambda m: {"package": m.get("package", "luxe")}),
    "deal_match": ("deals.activate", _deal),
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
