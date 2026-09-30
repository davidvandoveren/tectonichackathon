from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (and `.env` locally)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    # Password shared by the synthetic demo personas. Never commit a value for it.
    demo_password: SecretStr
    session_ttl_seconds: int = 60 * 60
    # Only disable for plain-http local development.
    cookie_secure: bool = True
    # Built frontend (Vite `dist`). Served same-origin when present.
    static_dir: Path | None = None
    login_max_failures: int = 5
    login_window_seconds: int = 5 * 60

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
