"""Language-model backends for Kate.

`GeminiChat` calls Gemini over its REST API. `MockChat` gives canned, rule-based answers so the demo
and the tests work without any key or network. Both return the raw JSON text described in
`assistant.SYSTEM_PROMPT`; the assistant validates it before anything reaches the customer.
"""

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal, Protocol

import httpx

from app.kate.context import CustomerContext

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT_SECONDS = 20.0


class KateUnavailableError(Exception):
    """The upstream model or voice service failed; the API answers 503."""


@dataclass(frozen=True)
class ChatTurn:
    role: Literal["user", "kate"]
    text: str


class ChatModel(Protocol):
    name: str

    def complete(self, system: str, turns: list[ChatTurn], context: CustomerContext) -> str: ...


class GeminiChat:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def complete(self, system: str, turns: list[ChatTurn], context: CustomerContext) -> str:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [
                {"role": "user" if t.role == "user" else "model", "parts": [{"text": t.text}]}
                for t in turns
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.4,
                "maxOutputTokens": 2048,
            },
        }
        try:
            response = httpx.post(
                GEMINI_URL.format(model=self._model),
                headers={"x-goog-api-key": self._api_key},
                json=body,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            text: str = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise KateUnavailableError("Gemini request failed") from exc
        return text


_TRANSFER = re.compile(
    r"(?:stuur|betaal|schrijf)\s+(?P<name>[A-Za-zÀ-ÿ' -]{2,40}?)\s+"
    r"(?:€\s*)?(?P<amount>\d{1,5}(?:[.,]\d{1,2})?)\s*(?:euro|eur|€)?"
    r"(?:\s+(?:voor|van)\s+(?:de\s+|het\s+)?(?P<what>.{1,60}))?",
    re.IGNORECASE,
)
_GUIDANCE_WORDS = ("overleden", "overlijden", "erfenis", "gestorven", "begrafenis")
_SPEND_WORDS = ("uitgegeven", "uitgaven", "spend", "besteed")
_BALANCE_WORDS = ("saldo", "hoeveel staat", "hoeveel geld")


class MockChat:
    """Deterministic stand-in for the LLM (no key needed)."""

    name = "mock"

    def complete(self, system: str, turns: list[ChatTurn], context: CustomerContext) -> str:
        message = turns[-1].text if turns else ""
        lower = message.lower()
        is_first = not any(t.role == "kate" for t in turns)
        intro = "Hallo, ik ben Kate, je digitale assistent (AI). " if is_first else ""

        if any(word in lower for word in _GUIDANCE_WORDS):
            return _json(
                intro + "Wat verdrietig, gecondoleerd. Ik help je stap voor stap, zonder haast: "
                "1) de overlijdensakte, 2) een attest of akte van erfopvolging, 3) daarna kan een "
                "adviseur de rekeningen met je overlopen. Zal ik een gesprek met een adviseur "
                "klaarzetten, zodat je je verhaal niet opnieuw hoeft te doen?",
                mode="guidance",
                action={
                    "type": "advisor_handoff",
                    "summary": "Klant meldt een overlijden in de familie en vraagt hulp bij de "
                    "erfenis. Begeleiding gewenst, geen commerciële voorstellen.",
                },
            )

        if match := _TRANSFER.search(message):
            amount = _parse_amount(match.group("amount"))
            if amount is not None:
                name = match.group("name").strip().title()
                what = (match.group("what") or "").strip()
                return _json(
                    intro + f"Ik heb een overschrijving van € {_nl(amount)} naar {name} "
                    "klaargezet. Controleer ze en bevestig zelf.",
                    action={
                        "type": "transfer",
                        "to_name": name,
                        "amount": f"{amount:.2f}",
                        "description": what.capitalize(),
                    },
                )

        if any(word in lower for word in _SPEND_WORDS):
            spend = context.spend_last_30_days
            total = sum((Decimal(v) for v in spend.values()), Decimal(0))
            top = sorted(spend.items(), key=lambda kv: Decimal(kv[1]), reverse=True)[:3]
            parts = ", ".join(f"{k} € {_nl(Decimal(v))}" for k, v in top)
            return _json(
                intro + f"De voorbije 30 dagen gaf je € {_nl(total)} uit. Grootste posten: {parts}."
            )

        if any(word in lower for word in _BALANCE_WORDS):
            parts = ", ".join(
                f"{a['name']}: € {_nl(Decimal(a['balance']))}" for a in context.accounts
            )
            return _json(intro + f"Je saldi: {parts}.")

        return _json(
            intro + f"Ik ben er voor je, {context.first_name}. Je kan me vragen stellen over je "
            "uitgaven of saldo, of zeggen: 'Stuur Lucas 25 euro voor de pizza'."
        )


def _nl(amount: Decimal) -> str:
    return f"{amount:,.2f}".replace(",", " ").replace(".", ",")


def _parse_amount(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", "."))
    except InvalidOperation:
        return None


def _json(reply: str, mode: str = "normal", action: dict[str, str] | None = None) -> str:
    return json.dumps(
        {"reply": reply, "mode": mode, "action": action or {"type": "none"}}, ensure_ascii=False
    )
