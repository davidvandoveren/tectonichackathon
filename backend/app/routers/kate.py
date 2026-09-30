"""Kate endpoints: chat, text-to-speech and speech-to-text for the logged-in customer."""

import base64
import binascii
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import Field, field_validator

from app.dependencies import BankDep, CurrentUser, KateStateDep, SettingsDep, TodayDep
from app.domain.models import User
from app.kate import assistant
from app.kate.context import build_context
from app.kate.llm import ChatModel, ChatTurn, GeminiChat, KateUnavailableError, MockChat
from app.kate.proposals import propose_from_chat
from app.kate.voice import ElevenLabsVoice
from app.kate.voices import VoiceKind, VoicePreferences, default_voice
from app.routers.skills import SkillsDep
from app.schemas import ApiModel
from app.security.rate_limit import RequestLimiter

router = APIRouter(prefix="/kate", tags=["kate"])

MAX_AUDIO_BYTES = 2 * 1024 * 1024  # ~1 minute of compressed speech
_UNAVAILABLE = "Kate is even niet bereikbaar. Probeer het straks opnieuw."


# --- dependencies ------------------------------------------------------------------------------
def get_chat_model(settings: SettingsDep) -> ChatModel:
    if settings.kate_llm_provider != "mock" and settings.gemini_api_key:
        return GeminiChat(
            settings.gemini_api_key.get_secret_value(),
            settings.gemini_model,
            [m.strip() for m in settings.gemini_fallback_models.split(",")],
        )
    return MockChat()


def _mock_reason(settings: SettingsDep) -> str | None:
    if settings.kate_llm_provider == "mock":
        return "KATE_LLM_PROVIDER staat op mock"
    if not settings.gemini_api_key:
        return "GEMINI_API_KEY ontbreekt in .env (of de server werd niet herstart)"
    return None


def get_voice(settings: SettingsDep) -> ElevenLabsVoice | None:
    if not settings.elevenlabs_api_key:
        return None
    voice_ids: dict[VoiceKind, str] = {}
    female = settings.elevenlabs_voice_id_female or settings.elevenlabs_voice_id
    if female:
        voice_ids["female"] = female
    if settings.elevenlabs_voice_id_male:
        voice_ids["male"] = settings.elevenlabs_voice_id_male
    return ElevenLabsVoice(
        settings.elevenlabs_api_key.get_secret_value(),
        voice_ids,
        settings.elevenlabs_tts_model,
        settings.elevenlabs_stt_model,
    )


def rate_limited_user(request: Request, user: CurrentUser) -> User:
    limiter: RequestLimiter = request.app.state.kate_limiter
    if not limiter.allow(f"kate:{user.id}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Even rustig aan, probeer zo weer")
    return user


def get_voice_preferences(request: Request) -> VoicePreferences:
    prefs: VoicePreferences = request.app.state.kate_voice_preferences
    return prefs


ChatModelDep = Annotated[ChatModel, Depends(get_chat_model)]
VoicePrefsDep = Annotated[VoicePreferences, Depends(get_voice_preferences)]
VoiceDep = Annotated[ElevenLabsVoice | None, Depends(get_voice)]
LimitedUser = Annotated[User, Depends(rate_limited_user)]


# --- schemas -----------------------------------------------------------------------------------
# Hard caps against abuse; anything between the soft limit and the cap is trimmed, never refused,
# so a long earlier answer can never make the next question fail.
MAX_TURN_TEXT = assistant.MAX_REPLY
MAX_HISTORY = 10


class ChatTurnIn(ApiModel):
    role: Literal["user", "kate"]
    text: str = Field(min_length=1, max_length=8000)

    @field_validator("text")
    @classmethod
    def _trim(cls, value: str) -> str:
        return value[:MAX_TURN_TEXT]


class ChatIn(ApiModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurnIn] = Field(default_factory=list, max_length=100)

    @field_validator("history")
    @classmethod
    def _recent_only(cls, value: list[ChatTurnIn]) -> list[ChatTurnIn]:
        return value[-MAX_HISTORY:]


class ActionOut(ApiModel):
    type: Literal["none", "transfer", "advisor_handoff"]
    to_name: str | None = None
    amount: str | None = None
    description: str | None = None
    summary: str | None = None
    # The Kate Skills proposal behind this suggestion (confirm/decline via /proposals/{id}/…).
    proposal_id: str | None = None
    proposal_status: str | None = None


class ChatOut(ApiModel):
    reply: str
    mode: Literal["normal", "guidance"]
    action: ActionOut


class StatusOut(ApiModel):
    llm: Literal["mock", "gemini"]
    voice: bool
    speech_recognition: bool
    # Why Kate runs on canned demo replies (shown to the demo team), or null when Gemini is on.
    mock_reason: str | None = None


class SpeechIn(ApiModel):
    text: str = Field(min_length=1, max_length=8000)

    @field_validator("text")
    @classmethod
    def _trim(cls, value: str) -> str:
        return value[: assistant.MAX_REPLY]


class TranscribeIn(ApiModel):
    audio_base64: str = Field(min_length=1, max_length=(MAX_AUDIO_BYTES * 4) // 3 + 4)
    mime_type: Literal["audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav"]


class TranscribeOut(ApiModel):
    text: str


class VoiceOut(ApiModel):
    voice: VoiceKind
    default_voice: VoiceKind
    # Which voices ElevenLabs is configured for (empty: the browser's own voice is used).
    available: list[VoiceKind]


class VoiceIn(ApiModel):
    voice: VoiceKind


# --- endpoints ---------------------------------------------------------------------------------
@router.get("/status", response_model=StatusOut)
def kate_status(
    _: CurrentUser, settings: SettingsDep, model: ChatModelDep, voice: VoiceDep
) -> StatusOut:
    """Tells the frontend which features are live (it falls back to the browser otherwise)."""
    is_gemini = model.name == "gemini"
    return StatusOut(
        llm="gemini" if is_gemini else "mock",
        voice=voice is not None and voice.can_speak,
        speech_recognition=voice is not None,
        mock_reason=None if is_gemini else _mock_reason(settings),
    )


@router.post("/chat", response_model=ChatOut)
def kate_chat(
    body: ChatIn,
    user: LimitedUser,
    bank: BankDep,
    today: TodayDep,
    model: ChatModelDep,
    state: KateStateDep,
    skills: SkillsDep,
) -> ChatOut:
    # Only this customer's own data, and only the kinds they allowed (PUT /kate/consent).
    context = build_context(bank, user, today, state.consent_for(user.id))
    history = [ChatTurn(role=t.role, text=t.text) for t in body.history]
    try:
        result = assistant.chat(model, context, history, body.message)
    except KateUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _UNAVAILABLE) from exc
    action = result.action
    reply = result.reply
    proposal = propose_from_chat(skills, user.id, action, body.message, today)
    if proposal is not None and not proposal.allowed:
        # The customer switched this action off for Kate: no card, and she says so.
        reply = f"{reply} (Dit mag ik niet voor je klaarzetten, zo koos je het in 'Wat mag Kate?'.)"
        action = assistant.NoAction(type="none")
    return ChatOut(
        reply=reply[: assistant.MAX_REPLY],
        mode=result.mode,
        action=ActionOut(
            type=action.type,
            to_name=getattr(action, "to_name", None),
            amount=f"{action.amount:.2f}" if isinstance(action, assistant.TransferAction) else None,
            description=getattr(action, "description", None),
            summary=getattr(action, "summary", None),
            proposal_id=proposal.proposal_id if proposal else None,
            proposal_status=proposal.status if proposal else None,
        ),
    )


@router.get("/voice", response_model=VoiceOut)
def get_kate_voice(user: CurrentUser, voice: VoiceDep, prefs: VoicePrefsDep) -> VoiceOut:
    return VoiceOut(
        voice=prefs.voice_for(user.id),
        default_voice=default_voice(user.id),
        available=voice.available() if voice else [],
    )


@router.post("/voice", response_model=VoiceOut)
def set_kate_voice(
    body: VoiceIn, user: CurrentUser, voice: VoiceDep, prefs: VoicePrefsDep
) -> VoiceOut:
    prefs.choose(user.id, body.voice)
    return get_kate_voice(user, voice, prefs)


@router.post("/speech", response_class=Response)
def kate_speech(
    body: SpeechIn, user: LimitedUser, voice: VoiceDep, prefs: VoicePrefsDep
) -> Response:
    if voice is None or not voice.can_speak:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Stem is niet geconfigureerd")
    try:
        audio = voice.speak(body.text, prefs.voice_for(user.id))
    except KateUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _UNAVAILABLE) from exc
    return Response(content=audio, media_type="audio/mpeg")


@router.post("/transcribe", response_model=TranscribeOut)
def kate_transcribe(body: TranscribeIn, _: LimitedUser, voice: VoiceDep) -> TranscribeOut:
    if voice is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Spraakherkenning is niet geconfigureerd"
        )
    try:
        audio = base64.b64decode(body.audio_base64, validate=True)
    except binascii.Error as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid audio") from exc
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Audio too large or empty")
    try:
        text = voice.transcribe(audio, body.mime_type)
    except KateUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _UNAVAILABLE) from exc
    return TranscribeOut(text=text.strip()[:1000])
