"""
Configuration management for Patient AI Health Navigator
Uses pydantic-settings for type-safe environment variable management
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from urllib.parse import quote_plus
from pathlib import Path
from pydantic import field_validator


BACKEND_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # Database Configuration (REQUIRED - must be in .env)
    DATABASE_URL: str  # No default - must come from .env

    # Monster PatientFHIR Database Configuration (read-only source)
    MONSTER_DATABASE_URL: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: int = 5432
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_SSLMODE: str = "prefer"
    
    # Application Settings
    APP_NAME: str = "Patient AI Health Navigator"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    APP_TIMEZONE: str = "Asia/Kolkata"

    # Automatic outreach scheduler
    AUTO_OUTREACH_SCHEDULER_ENABLED: bool = True
    AUTO_OUTREACH_INTERVAL_SECONDS: int = 60

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:4200", "http://127.0.0.1:4200"]
    CORS_ALLOWED_ORIGIN_REGEX: Optional[str] = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # OpenAI-compatible LLM provider. Credentials belong in Backend/.env only.
    LLM_ENABLED: bool = False
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_TOKENS: int = 350

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value
    
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    @property
    def resolved_monster_database_url(self) -> Optional[str]:
        """
        Build Monster DB URL from either MONSTER_DATABASE_URL or DB_* fields.
        Password is URL-encoded to support special characters.
        """
        if self.MONSTER_DATABASE_URL:
            return self.MONSTER_DATABASE_URL

        if not all([self.DB_HOST, self.DB_NAME, self.DB_USER, self.DB_PASSWORD]):
            return None

        return (
            f"postgresql://{self.DB_USER}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?sslmode={self.DB_SSLMODE}"
        )


# Global settings instance
settings = Settings()
