"""
Configuration management for Patient AI Health Navigator
Uses pydantic-settings for type-safe environment variable management
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from urllib.parse import quote_plus
from pathlib import Path


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
