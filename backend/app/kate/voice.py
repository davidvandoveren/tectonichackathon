"""ElevenLabs text-to-speech (Kate's voice) and speech-to-text (Scribe)."""

import logging

import httpx

from app.kate.llm import KateUnavailableError
from app.kate.voices import VoiceKind

ELEVENLABS_API = "https://api.elevenlabs.io/v1"
TIMEOUT_SECONDS = 30.0

logger = logging.getLogger("kbc_poc.kate.voice")

#: ElevenLabs' own default voices ("Sarah" and "George"), available on every account including
#: the free tier. Used when a key is set but no voice id, so the key alone is enough.
DEFAULT_VOICE_IDS: dict[VoiceKind, str] = {
    "female": "EXAVITQu4vr4xnSDxMaL",
    "male": "JBFqnCBsd6RMkjVDRZzb",
}


def voice_ids_from(
    female: str | None, male: str | None, legacy: str | None = None
) -> dict[VoiceKind, str]:
    """Configured voice ids, falling back to the default voices for any that is not set."""
    chosen: dict[VoiceKind, str] = {
        "female": (female or legacy or "").strip() or DEFAULT_VOICE_IDS["female"],
        "male": (male or "").strip() or DEFAULT_VOICE_IDS["male"],
    }
    return chosen


def explain(exc: httpx.HTTPError) -> str:
    """A reason a person can act on. Never contains the key; logged in full server-side."""
    if isinstance(exc, httpx.TimeoutException):
        return "ElevenLabs antwoordde niet op tijd"
    if not isinstance(exc, httpx.HTTPStatusError):
        return "ElevenLabs is niet bereikbaar vanaf de server"
    code = exc.response.status_code
    text = exc.response.text.lower()
    logger.warning("ElevenLabs HTTP %s: %s", code, exc.response.text[:300])
    if "paid_plan_required" in text or "payment" in text or code == 402:
        return (
            "deze stem vraagt een betaald ElevenLabs-abonnement; laat de stem-ID leeg voor een "
            "standaardstem of kies een eigen stem"
        )
    if "quota" in text or "credits" in text:
        return "het ElevenLabs-tegoed is op"
    if code == 401:
        return (
            "ELEVENLABS_API_KEY is ongeldig of mist de toestemming 'Text to Speech' "
            "(controleer de sleutel in je ElevenLabs-account)"
        )
    if code == 403:
        return "deze ElevenLabs-sleutel mag deze stem of dit model niet gebruiken"
    if code == 404 or "voice_not_found" in text:
        return "de stem-ID bestaat niet in je ElevenLabs-account"
    if code == 429:
        return "te veel verzoeken naar ElevenLabs; probeer zo opnieuw"
    return f"ElevenLabs gaf een fout ({code})"


class ElevenLabsVoice:
    def __init__(
        self, api_key: str, voice_ids: dict[VoiceKind, str], tts_model: str, stt_model: str
    ) -> None:
        self._headers = {"xi-api-key": api_key.strip()}
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
            raise KateUnavailableError(explain(exc)) from exc
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
        except httpx.HTTPError as exc:
            raise KateUnavailableError(explain(exc)) from exc
        except ValueError as exc:
            raise KateUnavailableError("ElevenLabs gaf een onleesbaar antwoord") from exc
        return text if isinstance(text, str) else ""
