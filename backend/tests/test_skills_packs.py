from datetime import date
from decimal import Decimal

import pytest

from app.domain.bank import Bank
from app.domain.seed import seed_bank
from app.skills.base import Level, Mandate
from app.skills.moments import draft_for_moment
from app.skills.registry import default_registry
from app.skills.service import NotEligibleError, SkillsService

TODAY = date(2026, 9, 30)
WHY = "Test"


@pytest.fixture
def service() -> SkillsService:
    bank = Bank()
    seed_bank(bank, "pw", TODAY)
    return SkillsService(bank, default_registry())


def approve(service: SkillsService, owner: str, action: str, params: dict[str, object]) -> str:
    proposal = service.propose(owner, action, params, "ui", WHY, TODAY)
    done = service.approve(owner, proposal.id, TODAY)
    assert done.status == "executed", done.outcome
    assert done.outcome is not None
    return done.outcome.message


def test_card_packages_add_then_drop(service: SkillsService) -> None:
    assert "7,00" in approve(service, "u_jan", "cards.add_package", {"package": "reis"})
    with pytest.raises(NotEligibleError):
        service.propose("u_jan", "cards.add_package", {"package": "reis"}, "ui", WHY, TODAY)
    assert "84,00" in approve(service, "u_jan", "cards.drop_package", {"package": "reis"})
    with pytest.raises(NotEligibleError):
        service.propose("u_jan", "cards.drop_package", {"package": "reis"}, "ui", WHY, TODAY)


def test_adding_a_paid_package_can_never_be_automatic(service: SkillsService) -> None:
    assert default_registry().get("cards.add_package").ceiling == Level.PREPARE  # type: ignore[union-attr]
    assert default_registry().get("cards.drop_package").ceiling == Level.AUTO  # type: ignore[union-attr]


def test_deal_activation_can_run_automatically(service: SkillsService) -> None:
    service.set_consent("u_emma", "deals.activate", Level.AUTO, None)
    proposal = service.propose(
        "u_emma", "deals.activate", {"category": "fuel"}, "moment", WHY, TODAY
    )
    assert proposal.status == "executed"


def test_standing_order_and_goal(service: SkillsService) -> None:
    assert "5e" in approve(
        service, "u_emma", "payments.standing_order", {"amount": "200.00", "day": 5}
    )
    assert "Reis" in approve(
        service, "u_emma", "savings.create_goal", {"name": "Reis", "target": "1500.00"}
    )


@pytest.mark.parametrize(
    ("action", "params"),
    [
        ("insurance.home_quote", {"reason": "moving"}),
        ("insurance.travel_quote", {"trips_per_year": 3}),
        ("loans.explore", {"purpose": "home", "amount": "250000.00"}),
        ("investing.prepare_meeting", {}),
        ("advisor.book_call", {"topic": "Erfenis van mijn moeder"}),
    ],
)
def test_regulated_domains_hand_off_to_a_human(
    service: SkillsService, action: str, params: dict[str, object]
) -> None:
    proposal = service.propose("u_marie", action, params, "chat", WHY, TODAY)
    done = service.approve("u_marie", proposal.id, TODAY)
    assert done.outcome is not None
    assert done.outcome.kind == "advisor_handoff"
    assert done.outcome.handoff_summary


def test_free_text_is_cleaned(service: SkillsService) -> None:
    proposal = service.propose(
        "u_marie", "advisor.book_call", {"topic": "<script>x</script>\nhulp"}, "chat", WHY, TODAY
    )
    assert "<" not in proposal.summary and "\n" not in proposal.summary


def test_chat_tools_follow_consent(service: SkillsService) -> None:
    names = {t["name"] for t in service.tools_for("u_emma")}
    assert "cards.add_package" in names
    assert service.tools_for("u_emma")[0]["parameters"]["type"] == "object"
    service.set_consent("u_emma", "cards.add_package", Level.OFF, None)
    assert "cards.add_package" not in {t["name"] for t in service.tools_for("u_emma")}


def test_mandate_is_scoped_to_one_action(service: SkillsService) -> None:
    mandate = Mandate(max_per_execution=Decimal("50.00"), max_per_month=Decimal("100.00"))
    service.set_consent("u_emma", "savings.move_to_savings", Level.AUTO, mandate)
    other = service.propose(
        "u_emma", "savings.move_to_current", {"amount": "10.00"}, "moment", WHY, TODAY
    )
    assert other.status == "pending"


# --- moments engine -> concrete actions ------------------------------------------------------


@pytest.mark.parametrize(
    ("moment", "meta", "action"),
    [
        # meta exactly as the Moments Engine (PR #15) emits it
        (
            "savings_habit_automatable",
            {"amount": "150.00", "median_amount": "150.00", "day_of_month": "30.5"},
            "payments.standing_order",
        ),
        ("first_salary", {"amount": "1985.00", "baseline": "310.00"}, "savings.create_goal"),
        ("idle_savings", {"savings": "64250.00", "months": "24"}, "investing.prepare_meeting"),
        (
            "cashflow_risk",
            {"balance": "212.40", "obligation": "420.00"},
            "savings.move_to_current",
        ),
        (
            "income_missing",
            {"counterparty": "Acme Logistics BV", "days_overdue": "9", "amount": "3120.00"},
            "advisor.book_call",
        ),
        ("card_package_gap", {}, "cards.add_package"),
        ("card_package_waste", {}, "cards.drop_package"),
        (
            "deal_match",
            {"counterparty": "Q8 Leuven", "category": "transport", "yearly_spend": "1820.00"},
            "deals.activate",
        ),
        ("moving_house", {}, "insurance.home_quote"),
    ],
)
def test_every_engine_moment_maps_to_a_valid_action(
    moment: str, meta: dict[str, str], action: str
) -> None:
    draft = draft_for_moment(moment, meta)
    assert draft is not None
    assert draft.action_id == action
    registered = default_registry().get(action)
    assert registered is not None
    registered.params.model_validate(draft.params)


def test_engine_meta_becomes_the_right_params() -> None:
    habit = draft_for_moment(
        "savings_habit_automatable", {"amount": "150.00", "day_of_month": "30.5"}
    )
    assert habit is not None and habit.params == {"amount": "150.00", "day": 28}
    risk = draft_for_moment("cashflow_risk", {"balance": "212.40", "obligation": "420.00"})
    assert risk is not None and risk.params == {"amount": "207.60"}
    deal = draft_for_moment("deal_match", {"category": "groceries"})
    assert deal is not None and deal.params == {"category": "groceries"}


def test_public_transport_is_not_a_fuel_deal() -> None:
    assert (
        draft_for_moment("deal_match", {"counterparty": "De Lijn", "category": "transport"}) is None
    )
    assert draft_for_moment("deal_match", {"counterparty": "NMBS", "category": "transport"}) is None
    fuel = draft_for_moment(
        "deal_match", {"counterparty": "TotalEnergies", "category": "transport"}
    )
    assert fuel is not None and fuel.params == {"category": "fuel"}


def test_sensitive_merchants_never_get_an_action() -> None:
    # Health, religion, politics, trade union: never profiled, never offered anything.
    for merchant, category in (("Apotheek", "other"), ("Apotheek Leuven", "groceries")):
        assert (
            draft_for_moment("deal_match", {"counterparty": merchant, "category": category}) is None
        )


def test_unknown_or_incomplete_moments_give_no_action() -> None:
    assert draft_for_moment("something_new", {}) is None
    assert draft_for_moment("deal_match", {"category": "housing"}) is None
    assert draft_for_moment("cashflow_risk", {}) is None
    # Balance already covers the obligation: nothing to top up.
    assert draft_for_moment("cashflow_risk", {"balance": "500.00", "obligation": "420.00"}) is None
