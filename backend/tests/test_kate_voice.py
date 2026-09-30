"""Kate's ElevenLabs voice: works with just a key, and says *why* when it does not."""

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.kate import voice as voice_module
from app.kate.llm import KateUnavailableError
from app.kate.voice import DEFAULT_VOICE_IDS, ElevenLabsVoice, voice_ids_from
from app.main import create_app
from tests.conftest import DEMO_PASSWORD, login


def _fake_post(status: int, body: str, calls: list[dict[str, Any]]) -> Any:
    def post(url: str, **kwargs: Any) -> httpx.Response:
        calls.append({"url": url, **kwargs})
        return httpx.Response(status, text=body, request=httpx.Request("POST", url))

    return post


def test_key_alone_is_enough_default_voices_are_used() -> None:
    assert voice_ids_from(None, None) == DEFAULT_VOICE_IDS
    assert voice_ids_from("  my-f  ", "", None) == {
        "female": "my-f",
        "male": DEFAULT_VOICE_IDS["male"],
    }
    assert voice_ids_from(None, None, "legacy")["female"] == "legacy"


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (401, '{"detail":{"status":"invalid_api_key"}}', "ELEVENLABS_API_KEY is ongeldig"),
        (402, '{"detail":{"status":"paid_plan_required"}}', "betaald ElevenLabs-abonnement"),
        (404, '{"detail":{"status":"voice_not_found"}}', "stem-ID bestaat niet"),
        (401, '{"detail":{"status":"quota_exceeded"}}', "tegoed is op"),
    ],
)
def test_errors_are_explained(
    monkeypatch: pytest.MonkeyPatch, status: int, body: str, expected: str
) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(voice_module.httpx, "post", _fake_post(status, body, calls))
    voice = ElevenLabsVoice(" key\n", voice_ids_from(None, None), "tts", "stt")
    with pytest.raises(KateUnavailableError, match=expected):
        voice.speak("hallo")
    assert calls[0]["headers"]["xi-api-key"] == "key"  # stray whitespace from .env is ignored
    assert "key" not in str(expected)


def test_speech_endpoint_returns_audio_and_readable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="test",
        demo_password=DEMO_PASSWORD,  # type: ignore[arg-type]
        cookie_secure=False,
        elevenlabs_api_key="secret-key",  # type: ignore[arg-type]
    )
    calls: list[dict[str, Any]] = []
    with TestClient(create_app(settings)) as client:
        login(client, "emma")
        status_body = client.get("/api/v1/kate/status").json()
        assert status_body["voice"] is True and status_body["voice_reason"] is None

        monkeypatch.setattr(voice_module.httpx, "post", _fake_post(200, "MP3", calls))
        ok = client.post("/api/v1/kate/speech", json={"text": "Hallo"})
        assert ok.status_code == 200 and ok.content == b"MP3"
        assert DEFAULT_VOICE_IDS["female"] in calls[-1]["url"]

        monkeypatch.setattr(
            voice_module.httpx, "post", _fake_post(401, '{"detail":"invalid_api_key"}', calls)
        )
        failed = client.post("/api/v1/kate/speech", json={"text": "Hallo"})
        assert failed.status_code == 503
        assert "ELEVENLABS_API_KEY is ongeldig" in failed.json()["detail"]
        assert "secret-key" not in failed.text


def test_status_says_why_there_is_no_voice(emma: TestClient) -> None:
    body = emma.get("/api/v1/kate/status").json()
    assert body["voice"] is False
    assert "ELEVENLABS_API_KEY" in body["voice_reason"]
