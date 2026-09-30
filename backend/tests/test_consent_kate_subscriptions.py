"""The customer's data consent (PUT /kate/consent) is respected by Kate's chat and subscriptions."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.domain.models import Category, Transaction
from app.kate.context import CustomerContext
from app.kate.llm import ChatTurn
from app.privacy.sensitive import is_sensitive, is_sensitive_text
from app.routers.kate import get_chat_model


class RecordingModel:
    name = "gemini"

    def __init__(self) -> None:
        self.context: CustomerContext | None = None
        self.system = ""

    def complete(self, system: str, turns: list[ChatTurn], context: CustomerContext) -> str:
        self.context, self.system = context, system
        return '{"reply": "AI: ok", "mode": "normal", "action": {"type": "none"}}'


def _consent(client: TestClient, domain: str, allowed: bool) -> None:
    response = client.put("/api/v1/kate/consent", json={"domain": domain, "allowed": allowed})
    assert response.status_code == 200, response.text


def test_kate_only_sees_allowed_data(emma: TestClient) -> None:
    model = RecordingModel()
    emma.app.dependency_overrides[get_chat_model] = lambda: model  # type: ignore[attr-defined]
    _consent(emma, "spending", False)
    _consent(emma, "balances", False)
    emma.post("/api/v1/kate/chat", json={"message": "hoeveel gaf ik uit?"})

    context = model.context
    assert context is not None
    assert context.spend_last_30_days == {}
    assert all(Decimal(t["amount"]) > 0 for t in context.recent_transactions)  # income only
    assert all("balance" not in a for a in context.accounts)
    assert context.withheld == ["saldi", "uitgaven en transacties"]
    assert '"withheld"' in model.system and "Colruyt" not in model.system


def test_all_data_by_default(emma: TestClient) -> None:
    model = RecordingModel()
    emma.app.dependency_overrides[get_chat_model] = lambda: model  # type: ignore[attr-defined]
    emma.post("/api/v1/kate/chat", json={"message": "hoi"})
    assert model.context is not None and model.context.withheld == []
    assert all("balance" in a for a in model.context.accounts)


def test_demo_mode_says_it_has_no_access(emma: TestClient) -> None:
    _consent(emma, "spending", False)
    reply = emma.post("/api/v1/kate/chat", json={"message": "hoeveel heb ik uitgegeven?"}).json()
    assert "geen toegang" in reply["reply"] and "Wat weet Kate" in reply["reply"]


def test_subscriptions_respect_spending_consent(emma: TestClient) -> None:
    assert emma.get("/api/v1/subscriptions").json()["subscriptions"]
    _consent(emma, "spending", False)
    body = emma.get("/api/v1/subscriptions").json()
    assert body["spending_consent"] is False
    assert body["subscriptions"] == [] and body["hidden_sensitive"] == 0

    # What the customer typed in themselves still works.
    added = emma.post("/api/v1/subscriptions", json={"name": "Streamz", "amount": "9.99"}).json()
    assert [s["name"] for s in added["subscriptions"]] == ["Streamz"]

    _consent(emma, "spending", True)
    assert {"Netflix", "Streamz"} <= {
        s["name"] for s in emma.get("/api/v1/subscriptions").json()["subscriptions"]
    }


def test_one_shared_sensitive_list() -> None:
    from app.kate.context import is_sensitive as kate_is_sensitive
    from app.subscriptions.detect import SENSITIVE_KEYWORDS

    assert kate_is_sensitive is is_sensitive
    assert "apotheek" in SENSITIVE_KEYWORDS
    assert is_sensitive_text("Lidgeld ACV Vakbond") and is_sensitive_text("ACV")
    assert is_sensitive_text("Huisarts Dr. Peeters")
    assert not is_sensitive_text("Vacvum cleaners NV")  # acronyms only as whole words
    assert not is_sensitive_text("Colruyt Leuven")
    t = Transaction(
        "t", "a", date(2026, 9, 1), "Medicatie", "Apotheek Centrum", Decimal("-9"), Category.OTHER
    )
    assert is_sensitive(t)
