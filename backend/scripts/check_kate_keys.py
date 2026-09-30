"""Check that Kate's real AI services work with the keys in your local `.env`.

Run from `backend/`:  python -m scripts.check_kate_keys

It goes through our own code paths (the same ones the app uses), never prints a key, and writes
the two voice samples to `kate-voice-female.mp3` / `kate-voice-male.mp3` so you can listen.
Exit code 0 = everything that is configured works.
"""

import sys
from datetime import date
from pathlib import Path

import httpx

from app.config import Settings
from app.domain.bank import Bank
from app.domain.seed import seed_bank
from app.kate import assistant
from app.kate.context import build_context
from app.kate.llm import GeminiChat, KateUnavailableError
from app.kate.voice import ElevenLabsVoice
from app.kate.voices import VoiceKind

OK, FAIL, SKIP = "✅", "❌", "⏭️ "


def why(exc: Exception) -> str:
    """The provider's own explanation (e.g. 'API key not valid'), never the key itself."""
    cause = exc.__cause__
    if isinstance(cause, httpx.HTTPStatusError):
        return f"HTTP {cause.response.status_code}: {cause.response.text[:300]}"
    return str(cause or exc)


def main() -> int:
    settings = Settings()  # reads .env
    failures = 0

    # --- Gemini ---------------------------------------------------------------------------------
    if settings.kate_llm_provider != "gemini":
        provider = settings.kate_llm_provider
        print(f"{SKIP} Gemini: KATE_LLM_PROVIDER is '{provider}' (set it to gemini)")
    elif not settings.gemini_api_key:
        print(f"{FAIL} Gemini: GEMINI_API_KEY is empty")
        failures += 1
    else:
        bank = Bank()
        seed_bank(bank, settings.demo_password.get_secret_value(), date.today())
        emma = bank.find_user_by_username("emma")
        if emma is None:
            raise SystemExit("demo persona 'emma' missing")
        model = GeminiChat(settings.gemini_api_key.get_secret_value(), settings.gemini_model)
        try:
            reply = assistant.chat(
                model,
                build_context(bank, emma, date.today()),
                [],
                "Stuur Lucas 25 euro voor de pizza",
            )
            print(f"{OK} Gemini ({settings.gemini_model}): {reply.reply[:120]!r}")
            print(f"   action: {reply.action.type}  (expected: transfer)")
        except KateUnavailableError as exc:
            print(f"{FAIL} Gemini: {why(exc)}")
            failures += 1

    # --- ElevenLabs -----------------------------------------------------------------------------
    if not settings.elevenlabs_api_key:
        print(f"{SKIP} ElevenLabs: ELEVENLABS_API_KEY is empty (browser voice will be used)")
        return 1 if failures else 0
    voice_ids: dict[VoiceKind, str] = {}
    female = settings.elevenlabs_voice_id_female or settings.elevenlabs_voice_id
    if female:
        voice_ids["female"] = female
    if settings.elevenlabs_voice_id_male:
        voice_ids["male"] = settings.elevenlabs_voice_id_male
    voice = ElevenLabsVoice(
        settings.elevenlabs_api_key.get_secret_value(),
        voice_ids,
        settings.elevenlabs_tts_model,
        settings.elevenlabs_stt_model,
    )
    sample = "Hallo, ik ben Kate, je digitale assistent. Ik ben een AI."
    last_audio = b""
    kinds: tuple[VoiceKind, ...] = ("female", "male")
    for kind in kinds:
        if kind not in voice_ids:
            print(f"{SKIP} ElevenLabs {kind} voice: ELEVENLABS_VOICE_ID_{kind.upper()} is empty")
            continue
        try:
            last_audio = voice.speak(sample, kind)
            path = Path(f"kate-voice-{kind}.mp3")
            path.write_bytes(last_audio)
            print(f"{OK} ElevenLabs {kind} voice: {len(last_audio) // 1024} KB -> {path}")
        except KateUnavailableError as exc:
            print(f"{FAIL} ElevenLabs {kind} voice: {why(exc)}")
            failures += 1

    if last_audio:
        try:
            text = voice.transcribe(last_audio, "audio/mpeg")
            print(f"{OK} ElevenLabs speech recognition: {text!r}")
        except KateUnavailableError as exc:
            print(f"{FAIL} ElevenLabs speech recognition: {why(exc)}")
            failures += 1

    print("\nAll configured services work." if not failures else f"\n{failures} check(s) failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
