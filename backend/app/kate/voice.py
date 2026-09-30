"""ElevenLabs text-to-speech (Kate's voice) and speech-to-text (Scribe)."""

import httpx

from app.kate.llm import KateUnavailableError
from app.kate.voices import VoiceKind

ELEVENLABS_API = "https://api.elevenlabs.io/v1"
TIMEOUT_SECONDS = 30.0


class ElevenLabsVoice:
    def __init__(
        self, api_key: str, voice_ids: dict[VoiceKind, str], tts_model: str, stt_model: str
    ) -> None:
        self._headers = {"xi-api-key": api_key}
        self._voice_ids = voice_ids
        self._tts_model = tts_model
        self._stt_model = stt_model

    @property
    def can_speak(self) -> bool:
        return bool(self._voice_ids)

    def available(self) -> list[VoiceKind]:
        return [kind for kind in ("female", "male") if kind in self._voice_ids]

    def speak(self, text: str, kind: VoiceKind = "female") -> bytes:
        """Text → MP3 bytes, in the requested voice (or the other one if only that is set)."""
        voice_id = self._voice_ids.get(kind) or next(iter(self._voice_ids.values()), None)
        if not voice_id:
            raise KateUnavailableError("No ElevenLabs voice configured")
        try:
            response = httpx.post(
                f"{ELEVENLABS_API}/text-to-speech/{voice_id}",
                params={"output_format": "mp3_44100_128"},
                headers=self._headers,
                json={"text": text, "model_id": self._tts_model},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise KateUnavailableError("ElevenLabs text-to-speech failed") from exc
        return response.content

    def transcribe(self, audio: bytes, mime_type: str, language: str | None = "nl") -> str:
        """Audio → text."""
        data = {"model_id": self._stt_model}
        if language:
            data["language_code"] = language
        try:
            response = httpx.post(
                f"{ELEVENLABS_API}/speech-to-text",
                headers=self._headers,
                data=data,
                files={"file": ("speech", audio, mime_type)},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            text = response.json().get("text", "")
        except (httpx.HTTPError, ValueError) as exc:
            raise KateUnavailableError("ElevenLabs speech-to-text failed") from exc
        return text if isinstance(text, str) else ""
