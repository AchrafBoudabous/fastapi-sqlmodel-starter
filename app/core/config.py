from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_KEY = "change-me-in-production-use-secrets-token-hex-32"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "FastAPI SQLModel Starter"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app"

    # ── Auth / JWT ────────────────────────────────────────────────────────────
    SECRET_KEY: str = _INSECURE_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Set as a JSON array in .env: CORS_ORIGINS='["https://app.example.com"]'
    # Defaults to localhost origins for local development only.
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    @model_validator(mode="after")
    def _reject_insecure_key_in_production(self) -> "Settings":
        if not self.DEBUG and self.SECRET_KEY == _INSECURE_KEY:
            raise ValueError(
                "SECRET_KEY must be changed before running in production (DEBUG=false). "
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        return self


settings = Settings()
