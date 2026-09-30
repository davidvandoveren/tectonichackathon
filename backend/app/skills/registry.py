"""The catalogue of everything Kate can do. Adding a KBC function = one pack + one line here."""

from collections.abc import Iterator
from typing import Any

from app.skills.base import Action, Skill
from app.skills.packs import advisor, cards, deals, insurance, investing, loans, payments, savings


class Registry:
    def __init__(self, skills: tuple[Skill, ...]) -> None:
        self.skills = skills
        self._actions = {a.id: a for s in skills for a in s.actions}
        if len(self._actions) != sum(len(s.actions) for s in skills):
            raise ValueError("duplicate action id")
        for action_id in self._actions:
            skill_id = action_id.split(".", 1)[0]
            if not any(s.id == skill_id for s in skills):
                raise ValueError(f"action {action_id} does not belong to a skill")

    def actions(self) -> Iterator[Action]:
        yield from self._actions.values()

    def get(self, action_id: str) -> Action | None:
        return self._actions.get(action_id)


def tool_definition(action: Action) -> dict[str, Any]:
    """An action as a function/tool definition for an LLM (Gemini, Claude and OpenAI style)."""
    schema = action.params.model_json_schema()
    schema.pop("title", None)
    return {"name": action.id, "description": action.description, "parameters": schema}


def default_registry() -> Registry:
    return Registry(
        (
            payments.SKILL,
            savings.SKILL,
            cards.SKILL,
            deals.SKILL,
            insurance.SKILL,
            loans.SKILL,
            investing.SKILL,
            advisor.SKILL,
        )
    )
