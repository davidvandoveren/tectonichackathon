"""Kate sends by herself.

The moments engine decides *what* is worth saying, *when* and *through which channel*, but it only
answers when asked. The dispatcher is the half that acts: on a schedule (and whenever a customer
opens their inbox) it runs the engine for each customer, puts what Kate decided to say into that
customer's inbox, and spends the interruption quota for push / sms / call. It also collects what
the other Kate features have to say (family circle, the investing plan she runs) so the customer
has one place for everything Kate told them.

Rules:
- Uses the engine unchanged (`moments.engine.experience`), with the customer's own consent and
  dismissals, so everything the engine promises (silence, quota, sensitive categories) holds.
- The same message is not sent again within `COOLDOWN_DAYS`.
- Only feed-level messages for things the customer did not ask for; the investing nudge is never
  sent to a minor, or to someone whose finances are tight, or when "balances" consent is off.
"""

import threading
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.bank import Bank
from app.domain.models import User
from app.family.circle import FamilyCircle
from app.family.suggestions import suggestions_for
from app.invest.guide import eur
from app.invest.service import Event, InvestService
from app.moments import engine
from app.moments.state import KateState
from app.notifications.store import Channel, NotificationStore

COOLDOWN_DAYS = 14
NUDGE_COOLDOWN_DAYS = 30
NUDGE_MIN_INVESTABLE = 5000
_INTERRUPTIVE = {"push", "sms", "call"}


@dataclass(frozen=True)
class Outgoing:
    key: str
    source: str
    title: str
    body: str
    reason: str
    channel: Channel
    cta_label: str
    cta_target: str
    cooldown_days: int = COOLDOWN_DAYS


class Dispatcher:
    def __init__(
        self,
        bank: Bank,
        kate: KateState,
        store: NotificationStore,
        family: FamilyCircle | None = None,
        invest: InvestService | None = None,
    ) -> None:
        self._bank = bank
        self._kate = kate
        self._store = store
        self._family = family
        self._invest = invest
        self._lock = threading.Lock()

    def today(self) -> date:
        return date.today() + timedelta(days=self._kate.time_offset_days)

    def sweep(self) -> int:
        """One round over every customer. Returns how many notifications were sent."""
        today = self.today()
        return sum(self.dispatch_for(user, today) for user in self._bank.list_users())

    def dispatch_for(self, user: User, today: date) -> int:
        with self._lock:
            outgoing = [
                *self._invest_events(user, today),
                *self._moments(user, today),
                *self._family_items(user, today),
                *self._invest_nudge(user, today),
            ]
            return self._send(user, outgoing, today)

    def deliver_events(self, user: User, events: Iterable[Event], today: date) -> int:
        """For events that happened in a request (e.g. the first step of a new plan)."""
        with self._lock:
            return self._send(user, [self._from_event(e) for e in events], today)

    # --- sources -------------------------------------------------------------------------------
    def _moments(self, user: User, today: date) -> list[Outgoing]:
        result = engine.experience(
            self._bank,
            user,
            today,
            consent=self._kate.consent_for(user.id),
            dismissed=self._kate.dismissals_for(user.id),
            last_interruption=self._kate.last_interruption_for(user.id),
        )
        return [
            Outgoing(
                key=f"moment:{item.id}",
                source="moment",
                title=item.title,
                body=item.body,
                reason=item.reason,
                channel=item.channel if item.channel != "none" else "feed",
                cta_label=item.cta_label,
                cta_target=item.cta_target,
            )
            for item in result.items
        ]

    def _family_items(self, user: User, today: date) -> list[Outgoing]:
        if self._family is None:
            return []
        return [
            Outgoing(
                key=f"family:{s.id}",
                source="family",
                title=s.title,
                body=s.body,
                reason=s.reason,
                channel="push" if s.kind in ("invite", "now_adult") else "feed",
                cta_label=s.cta_label,
                cta_target=s.cta_target,
                cooldown_days=365,
            )
            for s in suggestions_for(user.id, self._family, self._bank, today)
        ]

    def _invest_events(self, user: User, today: date) -> list[Outgoing]:
        if self._invest is None:
            return []
        return [self._from_event(e) for e in self._invest.run_due(user, today)]

    def _invest_nudge(self, user: User, today: date) -> list[Outgoing]:
        if self._invest is None or "balances" not in self._kate.consent_for(user.id):
            return []
        if self._family is not None and self._family.is_minor(user.id, today):
            return []
        if self._invest.state(user.id).plan is not None:
            return []
        health = self._invest.health(user.id, today)
        if health.status != "ready" or health.investable < NUDGE_MIN_INVESTABLE:
            return []
        return [
            Outgoing(
                key="invest:nudge",
                source="invest",
                title="Laat je spaargeld voor je werken?",
                body=f"Je buffer is in orde en er staat {eur(health.investable, 0)} extra op je "
                "spaarrekening. Kate legt je in 5 minuten uit hoe beleggen in ETF's werkt, stap "
                "voor stap en zonder verplichting.",
                reason=f"Je spaarrekening staat boven je buffer van {eur(health.buffer, 0)} "
                "(3 maanden van je eigen uitgaven). Spaargeld verliest door inflatie waarde; "
                "beleggen kan dat opvangen, maar houdt risico in. Jij beslist.",
                channel="feed",
                cta_label="Ontdek beleggen met Kate",
                cta_target="/invest",
                cooldown_days=NUDGE_COOLDOWN_DAYS,
            )
        ]

    @staticmethod
    def _from_event(event: Event) -> Outgoing:
        interrupt = event.kind in ("paused_buffer", "paused_error", "completed")
        return Outgoing(
            key=event.key,
            source="invest",
            title=event.title,
            body=event.body,
            reason=event.reason,
            channel="push" if interrupt else "feed",
            cta_label="Bekijk je beleggingen",
            cta_target="/invest",
            cooldown_days=10_000,  # a step is reported exactly once
        )

    # --- sending -------------------------------------------------------------------------------
    def _send(self, user: User, outgoing: list[Outgoing], today: date) -> int:
        sent = 0
        for item in outgoing:
            if self._store.sent_recently(user.id, item.key, today, item.cooldown_days):
                continue
            self._store.add(
                user.id,
                key=item.key,
                source=item.source,
                title=item.title,
                body=item.body,
                reason=item.reason,
                channel=item.channel,
                cta_label=item.cta_label,
                cta_target=item.cta_target,
                sent_on=today,
            )
            if item.channel in _INTERRUPTIVE and item.source == "moment":
                # The engine's quota: at most one interruption per window, spent when sent.
                self._kate.record_interruption(user.id, today)
            sent += 1
        return sent
