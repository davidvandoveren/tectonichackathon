"""Per-customer inbox of what Kate actually sent. Keyed by the authenticated user's id."""

import secrets
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

Channel = Literal["feed", "push", "sms", "call"]
MAX_PER_CUSTOMER = 100


@dataclass
class Notification:
    id: str
    key: str
    source: str
    title: str
    body: str
    reason: str
    channel: Channel
    cta_label: str
    cta_target: str
    sent_on: date
    created_at: datetime
    read: bool = False


class NotificationStore:
    def __init__(self) -> None:
        self._items: dict[str, list[Notification]] = {}
        self._last_sent: dict[tuple[str, str], date] = {}
        self._lock = threading.Lock()

    def for_user(self, user_id: str) -> list[Notification]:
        return sorted(self._items.get(user_id, []), key=lambda n: n.created_at, reverse=True)

    def sent_recently(self, user_id: str, key: str, today: date, cooldown_days: int) -> bool:
        last = self._last_sent.get((user_id, key))
        return last is not None and today - last < timedelta(days=cooldown_days)

    def add(
        self,
        user_id: str,
        *,
        key: str,
        source: str,
        title: str,
        body: str,
        reason: str,
        channel: Channel,
        cta_label: str,
        cta_target: str,
        sent_on: date,
    ) -> Notification:
        notification = Notification(
            id=f"nt_{secrets.token_hex(6)}",
            key=key,
            source=source,
            title=title,
            body=body,
            reason=reason,
            channel=channel,
            cta_label=cta_label,
            cta_target=cta_target,
            sent_on=sent_on,
            created_at=datetime.now(),
        )
        with self._lock:
            items = self._items.setdefault(user_id, [])
            items.append(notification)
            del items[:-MAX_PER_CUSTOMER]
            self._last_sent[(user_id, key)] = sent_on
        return notification

    def mark_read(self, user_id: str, notification_id: str) -> Notification | None:
        """Only ever looks in this user's own inbox (another id simply is not found)."""
        with self._lock:
            found = next((n for n in self._items.get(user_id, []) if n.id == notification_id), None)
            if found is not None:
                found.read = True
            return found

    def mark_all_read(self, user_id: str) -> None:
        with self._lock:
            for n in self._items.get(user_id, []):
                n.read = True
