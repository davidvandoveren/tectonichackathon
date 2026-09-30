"""Per-customer investing state: answers, chosen mix, the step plan and the (simulated) portfolio.

Money moves only through the ordinary, server-validated transfer from the customer's own savings
account to their own (synthetic) Bolero account, and only in steps the customer confirmed. Before
every step the buffer is checked again: if the step would dig into it, the plan pauses and Kate
says why. The customer can pause, resume or stop at any time.

In memory, like `Bank`. Swap for a real store together with it.
"""

import threading
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_DOWN, Decimal
from typing import Literal

from app.domain.bank import Bank, TransferError, TransferRequest
from app.domain.iban import make_be_iban
from app.domain.models import AccountType, User
from app.invest.catalog import BY_ID, TOB_RATE, price_on
from app.invest.guide import (
    Answers,
    Direction,
    Health,
    check_mix,
    direction_for,
    eur,
    health_check,
)

MAX_MONTHS = 36
MIN_STEP = Decimal("50")
_BOLERO_IBAN_BASE = 9_200_000_000

PlanStatus = Literal["active", "paused", "stopped", "completed"]
EventKind = Literal["step_done", "paused_buffer", "paused_error", "completed"]


class InvestError(Exception):
    """Well-formed but not allowed (422)."""


@dataclass
class Holding:
    etf_id: str
    units: Decimal = Decimal("0")
    invested: Decimal = Decimal("0")


@dataclass(frozen=True)
class Step:
    number: int
    on: date
    amount: Decimal
    tax: Decimal


@dataclass
class Plan:
    weights: dict[str, int]
    from_account_id: str
    total: Decimal
    months: int
    monthly: Decimal
    day: int
    buffer: Decimal
    started_on: date
    next_on: date
    status: PlanStatus = "active"
    steps: list[Step] = field(default_factory=list)
    pause_reason: str | None = None

    @property
    def invested(self) -> Decimal:
        return sum((s.amount for s in self.steps), Decimal(0))

    def next_amount(self) -> Decimal:
        remaining = self.total - self.invested
        return remaining if len(self.steps) == self.months - 1 else min(self.monthly, remaining)


@dataclass(frozen=True)
class Event:
    kind: EventKind
    key: str
    title: str
    body: str
    reason: str


@dataclass
class Customer:
    answers: Answers | None = None
    direction: Direction | None = None
    plan: Plan | None = None
    holdings: dict[str, Holding] = field(default_factory=dict)
    bolero_iban: str = ""


class InvestService:
    def __init__(self, bank: Bank) -> None:
        self._bank = bank
        self._customers: dict[str, Customer] = {}
        self._lock = threading.RLock()

    def _customer(self, user_id: str) -> Customer:
        with self._lock:
            if user_id not in self._customers:
                number = _BOLERO_IBAN_BASE + len(self._customers) + 1
                self._customers[user_id] = Customer(bolero_iban=make_be_iban(number))
            return self._customers[user_id]

    # --- reads ---------------------------------------------------------------------------------
    def health(self, user_id: str, today: date) -> Health:
        return health_check(
            self._bank.accounts_for(user_id), self._bank.all_transactions_for(user_id), today
        )

    def state(self, user_id: str) -> Customer:
        return self._customer(user_id)

    def portfolio_value(self, user_id: str, today: date) -> Decimal:
        holdings = self._customer(user_id).holdings.values()
        return sum((h.units * price_on(BY_ID[h.etf_id], today) for h in holdings), Decimal(0))

    # --- the guided steps ----------------------------------------------------------------------
    def answer(self, user_id: str, answers: Answers) -> Direction:
        customer = self._customer(user_id)
        with self._lock:
            customer.answers = answers
            customer.direction = direction_for(answers)
            return customer.direction

    def start_plan(
        self,
        user: User,
        weights: dict[str, int],
        total: Decimal,
        months: int,
        accept_risks: bool,
        today: date,
    ) -> tuple[Plan, list[Event]]:
        customer = self._customer(user.id)
        if customer.answers is None or customer.direction is None:
            raise InvestError("Beantwoord eerst de vragen, zodat Kate een richting kan tonen")
        if customer.plan is not None and customer.plan.status in ("active", "paused"):
            raise InvestError("Je hebt al een lopend plan. Stop het eerst als je opnieuw wil")
        check = check_mix(weights, customer.direction, customer.answers.knowledge)
        if check.blocked:
            raise InvestError(" ".join(check.blocked))
        if check.needs_acknowledgement and not accept_risks:
            raise InvestError("Bevestig eerst dat je de waarschuwingen bij je keuze begrijpt")
        if not customer.direction.suitable and not accept_risks:
            raise InvestError("Bevestig eerst dat je de waarschuwing bij je horizon begrijpt")

        health = self.health(user.id, today)
        if health.savings_account_id is None:
            raise InvestError("Je hebt geen spaarrekening om vanuit te beleggen")
        if total > health.investable:
            raise InvestError(
                f"Je kan hooguit {eur(health.investable)} beleggen: je buffer van "
                f"{eur(health.buffer)} blijft altijd op je spaarrekening"
            )
        if not 1 <= months <= MAX_MONTHS:
            raise InvestError(f"Kies tussen 1 en {MAX_MONTHS} maanden")
        monthly = (total / months).quantize(Decimal("0.01"), ROUND_DOWN)
        if monthly < MIN_STEP:
            raise InvestError(f"Een stap moet minstens {eur(MIN_STEP, 0)} zijn")

        with self._lock:
            customer.plan = Plan(
                weights=dict(weights),
                from_account_id=health.savings_account_id,
                total=total,
                months=months,
                monthly=monthly,
                day=min(today.day, 28),
                buffer=health.buffer,
                started_on=today,
                next_on=today,  # the first step happens right away, the rest monthly
            )
        return customer.plan, self.run_due(user, today)

    def pause(self, user_id: str) -> Plan:
        return self._set_status(user_id, "paused", ("active",))

    def resume(self, user_id: str, today: date) -> Plan:
        """Carries on from today: months that passed while paused are not caught up at once."""
        plan = self._set_status(user_id, "active", ("paused",))
        plan.pause_reason = None
        plan.next_on = max(plan.next_on, today)
        return plan

    def stop(self, user_id: str) -> Plan:
        """Stops future steps. What is already invested stays yours; nothing is sold."""
        return self._set_status(user_id, "stopped", ("active", "paused"))

    def _set_status(self, user_id: str, status: PlanStatus, allowed: tuple[str, ...]) -> Plan:
        with self._lock:
            plan = self._customer(user_id).plan
            if plan is None or plan.status not in allowed:
                raise LookupError("no such plan")
            plan.status = status
            return plan

    # --- automation: Kate executes the confirmed steps ------------------------------------------
    def run_due(self, user: User, today: date) -> list[Event]:
        """Execute every step that is due by `today` (the time machine can skip months)."""
        events: list[Event] = []
        customer = self._customer(user.id)
        with self._lock:
            plan = customer.plan
            while plan is not None and plan.status == "active" and plan.next_on <= today:
                event = self._execute_step(user, customer, plan, plan.next_on)
                events.append(event)
                if event.kind != "step_done":
                    break
                if len(plan.steps) >= plan.months:
                    plan.status = "completed"
                    events.append(
                        Event(
                            "completed",
                            f"invest:completed:{plan.started_on}",
                            "Je beleggingsplan is afgerond",
                            f"Alle {plan.months} stappen zijn uitgevoerd: {eur(plan.invested)} "
                            "staat nu in je ETF's.",
                            "Je koos zelf dit plan. Kate voerde elke maand de stap uit die je "
                            "bevestigde.",
                        )
                    )
                    break
                plan.next_on = _add_month(plan.next_on, plan.day)
        return events

    def _execute_step(self, user: User, customer: Customer, plan: Plan, on: date) -> Event:
        number = len(plan.steps) + 1
        amount = plan.next_amount()
        source = self._bank.account_for(user.id, plan.from_account_id)
        if source is None or source.type != AccountType.SAVINGS:
            return self._pause(plan, number, "paused_error", "Je spaarrekening is niet gevonden.")
        if source.balance - amount < plan.buffer:
            return self._pause(
                plan,
                number,
                "paused_buffer",
                f"Stap {number} zou je buffer van {eur(plan.buffer)} aanspreken. Kate zette het "
                "plan daarom op pauze. Je kan het hervatten wanneer je wil.",
            )
        try:
            self._bank.transfer(
                user.id,
                TransferRequest(
                    from_account_id=source.id,
                    to_iban=customer.bolero_iban,
                    to_name="Bolero · ETF-plan",
                    amount=amount,
                    description=f"Beleggingsplan stap {number}/{plan.months}",
                ),
                on,
            )
        except (LookupError, TransferError) as exc:
            return self._pause(
                plan, number, "paused_error", f"De overschrijving lukte niet: {exc}."
            )

        tax = (amount * TOB_RATE).quantize(Decimal("0.01"))
        net = amount - tax
        bought: list[str] = []
        for etf_id, weight in plan.weights.items():
            part = net * weight / 100
            holding = customer.holdings.setdefault(etf_id, Holding(etf_id))
            holding.units += (part / price_on(BY_ID[etf_id], on)).quantize(Decimal("0.0001"))
            holding.invested += part.quantize(Decimal("0.01"))
            bought.append(f"{weight}% {BY_ID[etf_id].index}")
        plan.steps.append(Step(number, on, amount, tax))
        return Event(
            "step_done",
            f"invest:step:{plan.started_on}:{number}",
            f"Stap {number} van {plan.months} uitgevoerd",
            f"{eur(amount)} van je spaarrekening belegd ({', '.join(bought)}). "
            f"Beurstaks: {eur(tax)}.",
            "Je bevestigde zelf dit stappenplan. Je buffer bleef onaangeroerd. Pauzeren of "
            "stoppen kan altijd onder Beleggen.",
        )

    @staticmethod
    def _pause(plan: Plan, number: int, kind: EventKind, why: str) -> Event:
        plan.status = "paused"
        plan.pause_reason = why
        return Event(
            kind,
            f"invest:pause:{plan.started_on}:{number}",
            "Kate zette je beleggingsplan op pauze",
            why,
            "Kate belegt nooit geld uit je buffer en voert geen stap uit die niet lukt.",
        )


def _add_month(day: date, preferred_day: int) -> date:
    year, month = (day.year + 1, 1) if day.month == 12 else (day.year, day.month + 1)
    return date(year, month, preferred_day)
