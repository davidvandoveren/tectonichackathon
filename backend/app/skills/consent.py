"""Per-customer, per-action consent: the ladder level and, for `auto`, a mandate."""

import threading
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from app.skills.base import Action, Level, Mandate


class ConsentError(ValueError):
    """A consent setting the action does not allow (above its ceiling, or auto without mandate)."""


@dataclass(frozen=True)
class Consent:
    level: Level
    mandate: Mandate | None = None


class ConsentStore:
    def __init__(self) -> None:
        self._settings: dict[tuple[str, str], Consent] = {}
        # (owner, action, "YYYY-MM") -> amount executed automatically that month
        self._spent: defaultdict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
        self._lock = threading.Lock()

    def get(self, owner_id: str, action: Action) -> Consent:
        return self._settings.get((owner_id, action.id), Consent(action.default_level))

    def set(self, owner_id: str, action: Action, level: Level, mandate: Mandate | None) -> Consent:
        if level > action.ceiling:
            raise ConsentError(f"'{action.id}' kan maximaal op '{action.ceiling.label}' staan")
        if level == Level.AUTO and action.moves_money and mandate is None:
            raise ConsentError("Automatisch uitvoeren van een geldbeweging vraagt een mandaat")
        consent = Consent(level, mandate if level == Level.AUTO else None)
        with self._lock:
            self._settings[(owner_id, action.id)] = consent
        return consent

    def try_spend(self, owner_id: str, action: Action, amount: Decimal, month: str) -> bool:
        """Reserve `amount` under the customer's mandate; False if it would exceed a limit."""
        mandate = self.get(owner_id, action).mandate
        if mandate is None or amount > mandate.max_per_execution:
            return False
        key = (owner_id, action.id, month)
        with self._lock:
            if self._spent[key] + amount > mandate.max_per_month:
                return False
            self._spent[key] += amount
            return True

    def refund(self, owner_id: str, action: Action, amount: Decimal, month: str) -> None:
        with self._lock:
            self._spent[(owner_id, action.id, month)] -= amount
