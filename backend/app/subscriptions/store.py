"""What the customer told us about their subscriptions. In memory, always keyed by customer."""

import threading
from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.subscriptions.detect import Subscription

Status = Literal["unknown", "in_use", "cancel_reminder"]
MAX_MANUAL = 20


@dataclass(frozen=True)
class Feedback:
    status: Status
    remind_on: date | None = None


class FeedbackStore:
    def __init__(self) -> None:
        self._feedback: dict[tuple[str, str], Feedback] = {}
        self._dismissed: dict[str, set[str]] = {}
        self._manual: dict[str, dict[str, Subscription]] = {}
        self._lock = threading.Lock()

    # --- "Gebruik je dit nog?" -----------------------------------------------------------------
    def get(self, owner_id: str, subscription_id: str) -> Feedback:
        return self._feedback.get((owner_id, subscription_id), Feedback("unknown"))

    def set(self, owner_id: str, subscription_id: str, feedback: Feedback) -> None:
        with self._lock:
            self._feedback[(owner_id, subscription_id)] = feedback

    # --- "Klopt dit niet? Verwijder" -----------------------------------------------------------
    def dismissed(self, owner_id: str) -> frozenset[str]:
        with self._lock:
            return frozenset(self._dismissed.get(owner_id, set()))

    def dismiss(self, owner_id: str, subscription_id: str) -> None:
        with self._lock:
            self._dismissed.setdefault(owner_id, set()).add(subscription_id)

    def restore(self, owner_id: str, subscription_id: str) -> None:
        with self._lock:
            self._dismissed.get(owner_id, set()).discard(subscription_id)

    # --- added by the customer -----------------------------------------------------------------
    def manual(self, owner_id: str) -> list[Subscription]:
        with self._lock:
            return list(self._manual.get(owner_id, {}).values())

    def add_manual(self, owner_id: str, subscription: Subscription) -> bool:
        with self._lock:
            own = self._manual.setdefault(owner_id, {})
            if len(own) >= MAX_MANUAL:
                return False
            own[subscription.id] = subscription
            return True

    def remove_manual(self, owner_id: str, subscription_id: str) -> bool:
        with self._lock:
            return self._manual.get(owner_id, {}).pop(subscription_id, None) is not None
