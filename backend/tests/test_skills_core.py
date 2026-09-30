from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.bank import Bank
from app.domain.models import AccountType
from app.domain.seed import seed_bank
from app.skills.base import Level, Mandate, Risk
from app.skills.consent import ConsentError
from app.skills.registry import default_registry
from app.skills.service import (
    InvalidStateError,
    NotAllowedError,
    NotEligibleError,
    ProposalNotFoundError,
    SkillsService,
    UnknownActionError,
)

TODAY = date(2026, 9, 30)
REASON = "Je zet al maanden met de hand geld opzij."


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def bank() -> Bank:
    bank = Bank()
    seed_bank(bank, "pw", TODAY)
    return bank


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def service(bank: Bank, clock: Clock) -> SkillsService:
    return SkillsService(bank, default_registry(), clock=clock)


def balance(bank: Bank, owner: str, kind: AccountType) -> Decimal:
    return next(a.balance for a in bank.accounts_for(owner) if a.type == kind)


# --- registry --------------------------------------------------------------------------------


def test_registry_covers_kbc_domains() -> None:
    skills = {s.id for s in default_registry().skills}
    assert {
        "payments",
        "savings",
        "cards",
        "deals",
        "insurance",
        "loans",
        "investing",
        "advisor",
    } <= skills


def test_every_action_has_a_description_and_a_ceiling_within_its_risk() -> None:
    for action in default_registry().actions():
        assert action.description
        assert action.ceiling <= action.risk.ceiling
        assert action.default_level <= action.ceiling


@pytest.mark.parametrize("risk", [Risk.EXTERNAL_MONEY, Risk.REGULATED])
def test_risky_classes_can_never_be_automatic(risk: Risk) -> None:
    assert risk.ceiling == Level.PREPARE


# --- consent ---------------------------------------------------------------------------------


def test_customer_cannot_raise_consent_above_the_ceiling(service: SkillsService) -> None:
    with pytest.raises(ConsentError):
        service.set_consent("u_emma", "payments.transfer", Level.AUTO, None)
    with pytest.raises(ConsentError):
        service.set_consent("u_emma", "loans.explore", Level.AUTO, None)


def test_auto_on_a_money_action_needs_a_mandate(service: SkillsService) -> None:
    with pytest.raises(ConsentError):
        service.set_consent("u_emma", "savings.move_to_savings", Level.AUTO, None)


def test_mandate_has_hard_ceilings() -> None:
    with pytest.raises(ValidationError):
        Mandate(max_per_execution=Decimal("5000.00"), max_per_month=Decimal("5000.00"))
    with pytest.raises(ValidationError):
        Mandate(max_per_execution=Decimal("300.00"), max_per_month=Decimal("100.00"))


def test_consent_is_per_customer(service: SkillsService) -> None:
    service.set_consent("u_emma", "cards.add_package", Level.OFF, None)
    assert service.consent_for("u_emma", "cards.add_package").level == Level.OFF
    assert service.consent_for("u_jan", "cards.add_package").level == Level.PREPARE


# --- proposal lifecycle ----------------------------------------------------------------------


def test_prepare_creates_a_pending_proposal_and_changes_nothing(
    service: SkillsService, bank: Bank
) -> None:
    before = balance(bank, "u_emma", AccountType.SAVINGS)
    proposal = service.propose(
        "u_emma", "savings.move_to_savings", {"amount": "50.00"}, "moment", REASON, TODAY
    )
    assert proposal.status == "pending"
    assert proposal.summary == "€ 50,00 naar je spaarrekening"
    assert balance(bank, "u_emma", AccountType.SAVINGS) == before


def test_approve_executes_once(service: SkillsService, bank: Bank) -> None:
    before = balance(bank, "u_emma", AccountType.SAVINGS)
    proposal = service.propose(
        "u_emma", "savings.move_to_savings", {"amount": "50.00"}, "chat", REASON, TODAY
    )
    done = service.approve("u_emma", proposal.id, TODAY)
    assert done.status == "executed"
    assert done.outcome is not None and done.outcome.kind == "done"
    assert balance(bank, "u_emma", AccountType.SAVINGS) == before + Decimal("50.00")
    with pytest.raises(InvalidStateError):
        service.approve("u_emma", proposal.id, TODAY)
    assert balance(bank, "u_emma", AccountType.SAVINGS) == before + Decimal("50.00")


def test_another_customer_cannot_see_or_approve_a_proposal(service: SkillsService) -> None:
    proposal = service.propose(
        "u_emma", "savings.move_to_savings", {"amount": "50.00"}, "chat", REASON, TODAY
    )
    with pytest.raises(ProposalNotFoundError):
        service.approve("u_jan", proposal.id, TODAY)
    assert service.proposals("u_jan") == []


def test_off_means_kate_cannot_even_propose(service: SkillsService) -> None:
    service.set_consent("u_emma", "savings.move_to_savings", Level.OFF, None)
    with pytest.raises(NotAllowedError):
        service.propose(
            "u_emma", "savings.move_to_savings", {"amount": "50.00"}, "chat", REASON, TODAY
        )
    assert service.proposals("u_emma") == []


def test_suggest_stores_a_card_without_an_action(service: SkillsService) -> None:
    service.set_consent("u_emma", "savings.move_to_savings", Level.SUGGEST, None)
    proposal = service.propose(
        "u_emma", "savings.move_to_savings", {"amount": "50.00"}, "moment", REASON, TODAY
    )
    assert proposal.status == "suggested"
    with pytest.raises(InvalidStateError):
        service.approve("u_emma", proposal.id, TODAY)


def test_consent_is_rechecked_at_approval(service: SkillsService) -> None:
    proposal = service.propose(
        "u_emma", "savings.move_to_savings", {"amount": "50.00"}, "chat", REASON, TODAY
    )
    service.set_consent("u_emma", "savings.move_to_savings", Level.OFF, None)
    with pytest.raises(NotAllowedError):
        service.approve("u_emma", proposal.id, TODAY)


def test_eligibility_is_rechecked_at_approval(service: SkillsService, bank: Bank) -> None:
    current = balance(bank, "u_emma", AccountType.CURRENT)
    proposal = service.propose(
        "u_emma", "savings.move_to_savings", {"amount": f"{current:.2f}"}, "chat", REASON, TODAY
    )
    service.approve(
        "u_emma",
        service.propose(
            "u_emma", "savings.move_to_savings", {"amount": "1.00"}, "chat", REASON, TODAY
        ).id,
        TODAY,
    )
    with pytest.raises(NotEligibleError):
        service.approve("u_emma", proposal.id, TODAY)


def test_proposals_expire_after_a_day(service: SkillsService, clock: Clock) -> None:
    proposal = service.propose(
        "u_emma", "savings.move_to_savings", {"amount": "50.00"}, "chat", REASON, TODAY
    )
    clock.now += timedelta(hours=25)
    with pytest.raises(InvalidStateError):
        service.approve("u_emma", proposal.id, TODAY)
    assert service.proposals("u_emma")[0].status == "expired"


def test_decline(service: SkillsService) -> None:
    proposal = service.propose(
        "u_emma", "savings.move_to_savings", {"amount": "50.00"}, "chat", REASON, TODAY
    )
    assert service.decline("u_emma", proposal.id).status == "declined"


def test_unknown_action_and_bad_params(service: SkillsService) -> None:
    with pytest.raises(UnknownActionError):
        service.propose("u_emma", "casino.bet", {}, "chat", REASON, TODAY)
    with pytest.raises(ValidationError):
        service.propose(
            "u_emma", "savings.move_to_savings", {"amount": "-5"}, "chat", REASON, TODAY
        )


def test_a_reason_is_required(service: SkillsService) -> None:
    with pytest.raises(ValueError, match="reason"):
        service.propose("u_emma", "savings.move_to_savings", {"amount": "5.00"}, "chat", " ", TODAY)


# --- mandates (auto) -------------------------------------------------------------------------


def test_auto_within_mandate_executes_immediately(service: SkillsService, bank: Bank) -> None:
    mandate = Mandate(max_per_execution=Decimal("100.00"), max_per_month=Decimal("150.00"))
    service.set_consent("u_emma", "savings.move_to_savings", Level.AUTO, mandate)
    before = balance(bank, "u_emma", AccountType.SAVINGS)

    first = service.propose(
        "u_emma", "savings.move_to_savings", {"amount": "100.00"}, "moment", REASON, TODAY
    )
    assert first.status == "executed"
    assert balance(bank, "u_emma", AccountType.SAVINGS) == before + Decimal("100.00")

    # Over the monthly limit: falls back to asking the customer.
    second = service.propose(
        "u_emma", "savings.move_to_savings", {"amount": "60.00"}, "moment", REASON, TODAY
    )
    assert second.status == "pending"

    # Over the per-execution limit: also asks.
    service.set_consent("u_jan", "savings.move_to_savings", Level.AUTO, mandate)
    big = service.propose(
        "u_jan", "savings.move_to_savings", {"amount": "120.00"}, "moment", REASON, TODAY
    )
    assert big.status == "pending"


def test_external_transfer_is_only_ever_a_prefill(service: SkillsService) -> None:
    proposal = service.propose(
        "u_emma",
        "payments.transfer",
        {"to_name": "Lucas", "amount": "25.00", "description": "Pizza"},
        "chat",
        "Je vroeg om Lucas 25 euro te sturen.",
        TODAY,
    )
    done = service.approve("u_emma", proposal.id, TODAY)
    assert done.outcome is not None
    assert done.outcome.kind == "navigate"
    assert done.outcome.navigate_to == "/transfer?to_name=Lucas&amount=25.00&description=Pizza"


# --- activity log ----------------------------------------------------------------------------


def test_activity_log_records_everything(service: SkillsService) -> None:
    service.set_consent("u_emma", "cards.add_package", Level.OFF, None)
    proposal = service.propose(
        "u_emma", "savings.move_to_savings", {"amount": "10.00"}, "chat", REASON, TODAY
    )
    service.approve("u_emma", proposal.id, TODAY)
    events = [e.event for e in service.activity("u_emma")]
    assert events == ["executed", "proposed", "consent_changed"]  # newest first
    assert service.activity("u_jan") == []
