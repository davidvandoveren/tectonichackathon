"""Gemini wiring: provider selection, model fallback and answer parsing (no network)."""

import json
from datetime import date
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.kate.context import CustomerContext
from app.kate.llm import GeminiChat, KateUnavailableError, MockChat, _answer_text
from app.routers.kate import get_chat_model
from tests.conftest import DEMO_PASSWORD

CONTEXT = CustomerContext("Emma", "Student", date(2026, 9, 30), [], {}, [])


def _settings(**overrides: Any) -> Settings:
    return Settings(demo_password=DEMO_PASSWORD, **overrides)  # type: ignore[arg-type]


def test_auto_uses_gemini_as_soon_as_a_key_is_set() -> None:
    assert isinstance(get_chat_model(_settings(gemini_api_key="k")), GeminiChat)
    assert isinstance(get_chat_model(_settings(gemini_api_key=None)), MockChat)
    assert isinstance(
        get_chat_model(_settings(gemini_api_key="k", kate_llm_provider="mock")), MockChat
    )


def _response(status: int, payload: object) -> httpx.Response:
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com/x")
    return httpx.Response(status, request=request, json=payload)


ANSWER = {"reply": "Ik ben Kate (AI). Hallo!", "mode": "normal", "action": {"type": "none"}}


def test_falls_back_to_next_model_on_404(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_post(url: str, **_: Any) -> httpx.Response:
        calls.append(url)
        if "missing-model" in url:
            return _response(404, {"error": {"message": "not found"}})
        return _response(
            200, {"candidates": [{"content": {"parts": [{"text": json.dumps(ANSWER)}]}}]}
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    chat = GeminiChat("k", "missing-model", ["gemini-flash-latest"])
    assert json.loads(chat.complete("sys", [], CONTEXT))["reply"].startswith("Ik ben Kate")
    assert len(calls) == 2 and "gemini-flash-latest" in calls[1]


def test_invalid_key_is_unavailable_not_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx, "post", lambda url, **_: _response(400, {"error": {"message": "API key not valid"}})
    )
    with pytest.raises(KateUnavailableError):
        GeminiChat("bad", "gemini-2.5-flash").complete("sys", [], CONTEXT)


def test_answer_skips_thought_parts_and_rejects_empty() -> None:
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "thinking…", "thought": True}, {"text": '{"reply":"x"}'}]
                }
            }
        ]
    }
    assert _answer_text(payload) == '{"reply":"x"}'
    with pytest.raises(ValueError):
        _answer_text({"candidates": []})
    with pytest.raises(ValueError):
        _answer_text({"candidates": [{"content": {"parts": [{"text": "  "}]}}]})
