"""Language-model backends for Kate.

`GeminiChat` calls Gemini over its REST API. `MockChat` gives canned, rule-based answers so the demo
and the tests work without any key or network. Both return the raw JSON text described in
`assistant.SYSTEM_PROMPT`; the assistant validates it before anything reaches the customer.
"""

import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal, Protocol

import httpx

from app.kate.context import CustomerContext

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RETRY_NEXT_MODEL = frozenset({404, 429, 500, 502, 503, 504})
TIMEOUT_SECONDS = 25.0

logger = logging.getLogger("kbc_poc.kate")


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

    def __init__(self, api_key: str, model: str, fallback_models: Sequence[str] = ()) -> None:
        self._api_key = api_key
        self._models = [model, *(m for m in fallback_models if m and m != model)]

    def complete(self, system: str, turns: list[ChatTurn], context: CustomerContext) -> str:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": _gemini_contents(turns),
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.4,
                "maxOutputTokens": 4096,
            },
        }
        last_error: Exception | None = None
        for model in self._models:
            try:
                response = httpx.post(
                    GEMINI_URL.format(model=model),
                    headers={"x-goog-api-key": self._api_key},
                    json=body,
                    timeout=TIMEOUT_SECONDS,
                )
                # Not available for this key (404), rate limited (429) or overloaded (5xx):
                # another model usually answers, so try the next one.
                if response.status_code in RETRY_NEXT_MODEL:
                    logger.warning(
                        "Gemini model %s unavailable (HTTP %s), trying next",
                        model,
                        response.status_code,
                    )
                    last_error = httpx.HTTPStatusError(
                        "model unavailable", request=response.request, response=response
                    )
                    continue
                response.raise_for_status()
                return _answer_text(response.json())
            except httpx.HTTPStatusError as exc:
                # Log the provider's reason (e.g. "API key not valid"), never the key.
                logger.warning(
                    "Gemini %s failed: HTTP %s %s",
                    model,
                    exc.response.status_code,
                    exc.response.text[:300],
                )
                raise KateUnavailableError("Gemini request failed") from exc
            except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as exc:
                logger.warning("Gemini %s failed: %s", model, type(exc).__name__)
                raise KateUnavailableError("Gemini request failed") from exc
        raise KateUnavailableError("No Gemini model available") from last_error


def _gemini_contents(turns: list[ChatTurn]) -> list[dict[str, object]]:
    """Turns as Gemini wants them: starting with the user and alternating user/model.

    The browser keeps the conversation, so after a failed request it can send two user turns in a
    row, and the history window can start on a Kate turn. Gemini rejects such a conversation, and
    then every next message fails too. Merge same-role neighbours and drop leading model turns.
    """
    merged: list[tuple[str, list[dict[str, str]]]] = []
    for turn in turns:
        role = "user" if turn.role == "user" else "model"
        if not merged and role == "model":
            continue
        if merged and merged[-1][0] == role:
            merged[-1][1].append({"text": turn.text})
        else:
            merged.append((role, [{"text": turn.text}]))
    return [{"role": role, "parts": parts} for role, parts in merged]


def _answer_text(payload: dict[str, object]) -> str:
    """The answer text, skipping the model's internal "thought" parts."""
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        raise ValueError("no candidates (blocked or empty answer)")
    content = candidates[0].get("content")
    parts = content.get("parts", []) if isinstance(content, dict) else []
    if not isinstance(parts, list):
        raise ValueError("malformed answer")
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought"))
    if not text.strip():
        raise ValueError("empty answer")
    return text


# Only ever matched against `_single_spaced` text: the name may contain spaces and is followed by
# whitespace, which on raw input with long whitespace runs backtracks quadratically (ReDoS).
_TRANSFER = re.compile(
    r"(?:stuur|betaal|schrijf)\s+(?P<name>[A-Za-zÀ-ÿ' -]{2,40}?)\s+"
    r"(?:€\s*)?(?P<amount>\d{1,5}(?:[.,]\d{1,2})?)\s*(?:euro|eur|€)?"
    r"(?:\s+(?:voor|van)\s+(?:de\s+|het\s+)?(?P<what>.{1,60}))?",
    re.IGNORECASE,
)
_GUIDANCE_WORDS = ("overleden", "overlijden", "erfenis", "gestorven", "begrafenis")
_OFFER = "Als je wil, kan ik je helpen met wat er financieel geregeld moet worden."
_YES_WORDS = ("ja", "graag", "oké", "oke", "ok", "yes", "goed", "doe maar", "alstublieft", "aub")
_SPEND_WORDS = ("uitgegeven", "uitgaven", "spend", "besteed")
_BALANCE_WORDS = ("saldo", "hoeveel staat", "hoeveel geld")


class MockChat:
    """Deterministic stand-in for the LLM (no key needed)."""

    name = "mock"

    def complete(self, system: str, turns: list[ChatTurn], context: CustomerContext) -> str:
        message = _single_spaced(turns[-1].text) if turns else ""
        lower = message.lower()
        is_first = not any(t.role == "kate" for t in turns)
        intro = "Hallo, ik ben Kate, je digitale assistent (AI). " if is_first else ""

        last_kate = next((t.text for t in reversed(turns[:-1]) if t.role == "kate"), "")
        if _OFFER in last_kate and _is_yes(lower):
            return _json(
                "Oké, stap voor stap en zonder haast: 1) de overlijdensakte, 2) een attest of "
                "akte van erfopvolging, 3) daarna overloopt een adviseur de rekeningen met je. "
                "Ik zet dat gesprek voor je klaar, dan hoef je je verhaal niet opnieuw te doen.",
                mode="guidance",
                action={
                    "type": "advisor_handoff",
                    "summary": "Klant meldt een overlijden in de familie en vraagt hulp bij de "
                    "erfenis. Begeleiding gewenst, geen commerciële voorstellen.",
                },
            )

        if any(word in lower for word in _GUIDANCE_WORDS):
            return _json(
                intro
                + "Wat verschrikkelijk, gecondoleerd. Neem gerust je tijd. "
                + _OFFER
                + " Zal ik dat rustig met je overlopen?",
                mode="guidance",
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

        if any(word in lower for word in _SPEND_WORDS + _BALANCE_WORDS) and context.withheld:
            asked = "uitgaven en transacties" if any(w in lower for w in _SPEND_WORDS) else "saldi"
            if asked in context.withheld:
                return _json(
                    intro + f"Daar heb ik geen toegang toe: je koos ervoor dat ik je {asked} niet "
                    "gebruik. Je kan dat altijd aanpassen in de app onder 'Wat weet Kate?'."
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


def _single_spaced(text: str) -> str:
    return " ".join(text.split())


def _nl(amount: Decimal) -> str:
    return f"{amount:,.2f}".replace(",", " ").replace(".", ",")


def _is_yes(text: str) -> bool:
    words = re.findall(r"[a-zà-ÿ]+", text)
    return any(w in _YES_WORDS for w in words) or "doe maar" in text


def _parse_amount(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", "."))
    except InvalidOperation:
        return None


def _json(reply: str, mode: str = "normal", action: dict[str, str] | None = None) -> str:
    return json.dumps(
        {"reply": reply, "mode": mode, "action": action or {"type": "none"}}, ensure_ascii=False
    )
