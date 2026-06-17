"""
config.py
---------
Reads all environment variables from the .env file.
Uses pydantic-settings so every variable is validated on startup.
If a required variable is missing, the app will REFUSE to start — which
is exactly what you want so you catch config mistakes early.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── JWT / Auth ────────────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # default = 1 day

    # ── App Info ──────────────────────────────────────────────────────────
    APP_NAME: str = "Zoiko One Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_mode(cls, value):
        if isinstance(value, str) and value.lower() in {"release", "prod", "production"}:
            return False
        return value

    class Config:
        # Tell pydantic WHERE the .env file lives (same folder as this file's parent)
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create ONE global instance — import this everywhere you need settings
settings = Settings()
