"""Shared shape for regulated domains: Kate prepares, a human advisor decides.

Kate collects what the customer already told her so they never repeat their story, and hands off.
No product advice, no pricing, no marketing (MiFID / consumer-credit rules).
"""

from collections.abc import Callable
from typing import Any

from app.skills.base import Action, Level, Outcome, Params, Risk, SkillContext


def handoff_action(
    *,
    id: str,
    title: str,
    description: str,
    params: type[Params],
    summary: Callable[[Any], str],
    risk: Risk = Risk.REGULATED,
) -> Action:
    def execute(_: SkillContext, p: Any) -> Outcome:
        brief = summary(p)
        return Outcome(
            "advisor_handoff",
            "Een adviseur neemt contact met je op. Je hoeft je verhaal niet opnieuw te doen.",
            handoff_summary=brief,
        )

    return Action(
        id=id,
        title=title,
        description=description,
        risk=risk,
        params=params,
        summary=summary,
        execute=execute,
        max_level=Level.PREPARE,
    )
