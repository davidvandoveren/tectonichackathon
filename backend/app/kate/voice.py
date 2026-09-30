"""ElevenLabs text-to-speech (Kate's voice) and speech-to-text (Scribe)."""

import httpx

from app.kate.llm import KateUnavailableError

ELEVENLABS_API = "https://api.elevenlabs.io/v1"
TIMEOUT_SECONDS = 30.0


class ElevenLabsVoice:
    def __init__(self, api_key: str, voice_id: str | None, tts_model: str, stt_model: str) -> None:
        self._headers = {"xi-api-key": api_key}
        self._voice_id = voice_id
        self._tts_model = tts_model
        self._stt_model = stt_model

    @property
    def can_speak(self) -> bool:
        return bool(self._voice_id)

    def speak(self, text: str) -> bytes:
        """Text → MP3 bytes."""
        if not self._voice_id:
            raise KateUnavailableError("No ElevenLabs voice configured")
        try:
            response = httpx.post(
                f"{ELEVENLABS_API}/text-to-speech/{self._voice_id}",
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
