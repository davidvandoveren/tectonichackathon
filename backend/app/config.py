from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (and `.env` locally)."""

    # `.env` in the working directory, or one level up (the project root) when started from
    # `backend/`. Real environment variables always win.
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    # Password shared by the synthetic demo personas. Never commit a value for it.
    demo_password: SecretStr
    # Demo mode: log in as a synthetic persona with one click, no password. Off by default;
    # only turn on for a public demo of synthetic data (see README "Known limitations").
    passwordless_login: bool = False
    session_ttl_seconds: int = 60 * 60
    # Only disable for plain-http local development.
    cookie_secure: bool = True
    # Built frontend (Vite `dist`). Served same-origin when present.
    static_dir: Path | None = None
    login_max_failures: int = 5
    login_window_seconds: int = 5 * 60
    # Proxies in front of the app that append to X-Forwarded-For (Cloud Run: 1, Cloud Run behind
    # an external HTTPS load balancer: 2). 0 = use the socket peer. See security/client_ip.py.
    trusted_proxy_hops: int = Field(default=0, ge=0, le=5)
    # Usernames allowed to use the demo-only admin endpoints (time machine). Comma separated.
    # Empty means nobody, so the endpoints answer 404 for everyone until a demo is set up.
    admin_usernames: str = ""

    @property
    def admin_username_set(self) -> frozenset[str]:
        return frozenset(name.strip() for name in self.admin_usernames.split(",") if name.strip())

    # --- Kate assistant (chat, voice, speech recognition) --------------------------------------
    # "auto" uses Gemini as soon as GEMINI_API_KEY is set, else canned demo replies ("mock").
    kate_llm_provider: Literal["auto", "mock", "gemini"] = "auto"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    # Tried in order when the configured model is not available for this key (404).
    gemini_fallback_models: str = "gemini-flash-latest,gemini-2.0-flash"
    elevenlabs_api_key: SecretStr | None = None
    # Two Kate voices. The default per customer follows the gender registered on the customer
    # record (see app/kate/voices.py); the customer can always switch.
    elevenlabs_voice_id_female: str | None = None
    elevenlabs_voice_id_male: str | None = None
    # Deprecated single voice; used as the female voice when the specific one is not set.
    elevenlabs_voice_id: str | None = None
    elevenlabs_tts_model: str = "eleven_multilingual_v2"
    elevenlabs_stt_model: str = "scribe_v1"
    # Per customer, per minute, across all Kate endpoints (LLM/voice calls cost money).
    kate_max_requests_per_minute: int = 20

    @field_validator("demo_password")
    @classmethod
    def _password_strength(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 8:
            raise ValueError("DEMO_PASSWORD must be at least 8 characters")
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
