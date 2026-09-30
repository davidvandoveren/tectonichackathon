"""What the customer told us about a subscription ("Gebruik je dit nog?"), per customer."""

import threading
from dataclasses import dataclass
from datetime import date
from typing import Literal

Status = Literal["unknown", "in_use", "cancel_reminder"]


@dataclass(frozen=True)
class Feedback:
    status: Status
    remind_on: date | None = None


class FeedbackStore:
    def __init__(self) -> None:
        self._feedback: dict[tuple[str, str], Feedback] = {}
        self._lock = threading.Lock()

    def get(self, owner_id: str, subscription_id: str) -> Feedback:
        return self._feedback.get((owner_id, subscription_id), Feedback("unknown"))

    def set(self, owner_id: str, subscription_id: str, feedback: Feedback) -> None:
        with self._lock:
            self._feedback[(owner_id, subscription_id)] = feedback
