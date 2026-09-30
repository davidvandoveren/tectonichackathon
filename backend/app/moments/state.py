"""Per-customer engine state: consent, dismissals and the demo clock.

In memory, like `Bank`, and keyed by the authenticated user's id so one customer's choices can
never influence another's feed. Swap for a real store together with `Bank`.
"""

import threading
from collections.abc import Mapping
from datetime import date

from app.moments.signals import ALL_DOMAINS, Domain


class KateState:
    def __init__(self) -> None:
        self._consent: dict[str, set[Domain]] = {}
        self._dismissals: dict[str, dict[str, date]] = {}
        self._last_interruption: dict[str, date] = {}
        self._lock = threading.Lock()
        #: Days the demo clock is shifted by. Only the admin time machine changes this.
        self.time_offset_days = 0

    # --- consent -------------------------------------------------------------------------------
    def consent_for(self, user_id: str) -> set[Domain]:
        """Everything is allowed until the customer says otherwise."""
        return set(self._consent.get(user_id, set(ALL_DOMAINS)))

    def set_consent(self, user_id: str, domain: Domain, allowed: bool) -> set[Domain]:
        with self._lock:
            current = self._consent.setdefault(user_id, set(ALL_DOMAINS))
            if allowed:
                current.add(domain)
            else:
                current.discard(domain)
            return set(current)

    # --- dismissals ----------------------------------------------------------------------------
    def dismissals_for(self, user_id: str) -> Mapping[str, date]:
        return dict(self._dismissals.get(user_id, {}))

    def dismiss(self, user_id: str, moment_type: str, on: date) -> None:
        with self._lock:
            self._dismissals.setdefault(user_id, {})[moment_type] = on

    # --- interruption quota --------------------------------------------------------------------
    def last_interruption_for(self, user_id: str) -> date | None:
        return self._last_interruption.get(user_id)

    def record_interruption(self, user_id: str, on: date) -> None:
        """Called when a message is actually sent, never when the feed is merely read."""
        with self._lock:
            self._last_interruption[user_id] = on

    def shift_clock(self, days: int) -> int:
        with self._lock:
            self.time_offset_days += days
            return self.time_offset_days
