"""Kate endpoints: chat, text-to-speech and speech-to-text for the logged-in customer."""

import base64
import binascii
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import Field

from app.dependencies import BankDep, CurrentUser, SettingsDep, TodayDep
from app.domain.models import User
from app.kate import assistant
from app.kate.context import build_context
from app.kate.llm import ChatModel, ChatTurn, GeminiChat, KateUnavailableError, MockChat
from app.kate.voice import ElevenLabsVoice
from app.schemas import ApiModel
from app.security.rate_limit import RequestLimiter

router = APIRouter(prefix="/kate", tags=["kate"])

MAX_AUDIO_BYTES = 2 * 1024 * 1024  # ~1 minute of compressed speech
_UNAVAILABLE = "Kate is even niet bereikbaar. Probeer het straks opnieuw."


# --- dependencies ------------------------------------------------------------------------------
def get_chat_model(settings: SettingsDep) -> ChatModel:
    if settings.kate_llm_provider == "gemini" and settings.gemini_api_key:
        return GeminiChat(settings.gemini_api_key.get_secret_value(), settings.gemini_model)
    return MockChat()


def get_voice(settings: SettingsDep) -> ElevenLabsVoice | None:
    if not settings.elevenlabs_api_key:
        return None
    return ElevenLabsVoice(
        settings.elevenlabs_api_key.get_secret_value(),
        settings.elevenlabs_voice_id,
        settings.elevenlabs_tts_model,
        settings.elevenlabs_stt_model,
    )


def rate_limited_user(request: Request, user: CurrentUser) -> User:
    limiter: RequestLimiter = request.app.state.kate_limiter
    if not limiter.allow(f"kate:{user.id}"):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Even rustig aan, probeer zo weer")
    return user


ChatModelDep = Annotated[ChatModel, Depends(get_chat_model)]
VoiceDep = Annotated[ElevenLabsVoice | None, Depends(get_voice)]
LimitedUser = Annotated[User, Depends(rate_limited_user)]


# --- schemas -----------------------------------------------------------------------------------
class ChatTurnIn(ApiModel):
    role: Literal["user", "kate"]
    text: str = Field(min_length=1, max_length=1200)


class ChatIn(ApiModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurnIn] = Field(default_factory=list, max_length=10)


class ActionOut(ApiModel):
    type: Literal["none", "transfer", "advisor_handoff"]
    to_name: str | None = None
    amount: str | None = None
    description: str | None = None
    summary: str | None = None


class ChatOut(ApiModel):
    reply: str
    mode: Literal["normal", "guidance"]
    action: ActionOut


class StatusOut(ApiModel):
    llm: Literal["mock", "gemini"]
    voice: bool
    speech_recognition: bool


class SpeechIn(ApiModel):
    text: str = Field(min_length=1, max_length=assistant.MAX_REPLY)


class TranscribeIn(ApiModel):
    audio_base64: str = Field(min_length=1, max_length=(MAX_AUDIO_BYTES * 4) // 3 + 4)
    mime_type: Literal["audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav"]


class TranscribeOut(ApiModel):
    text: str


# --- endpoints ---------------------------------------------------------------------------------
@router.get("/status", response_model=StatusOut)
def kate_status(_: CurrentUser, model: ChatModelDep, voice: VoiceDep) -> StatusOut:
    """Tells the frontend which features are live (it falls back to the browser otherwise)."""
    return StatusOut(
        llm="gemini" if model.name == "gemini" else "mock",
        voice=voice is not None and voice.can_speak,
        speech_recognition=voice is not None,
    )


@router.post("/chat", response_model=ChatOut)
def kate_chat(
    body: ChatIn, user: LimitedUser, bank: BankDep, today: TodayDep, model: ChatModelDep
) -> ChatOut:
    context = build_context(bank, user, today)  # only this customer's own data
    history = [ChatTurn(role=t.role, text=t.text) for t in body.history]
    try:
        result = assistant.chat(model, context, history, body.message)
    except KateUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _UNAVAILABLE) from exc
    action = result.action
    return ChatOut(
        reply=result.reply,
        mode=result.mode,
        action=ActionOut(
            type=action.type,
            to_name=getattr(action, "to_name", None),
            amount=f"{action.amount:.2f}" if isinstance(action, assistant.TransferAction) else None,
            description=getattr(action, "description", None),
            summary=getattr(action, "summary", None),
        ),
    )


@router.post("/speech", response_class=Response)
def kate_speech(body: SpeechIn, _: LimitedUser, voice: VoiceDep) -> Response:
    if voice is None or not voice.can_speak:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Stem is niet geconfigureerd")
    try:
        audio = voice.speak(body.text)
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
