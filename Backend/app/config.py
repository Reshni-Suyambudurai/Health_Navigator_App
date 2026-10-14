"""
Configuration management for Patient AI Health Navigator
Uses pydantic-settings for type-safe environment variable management
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    
    # Database Configuration (REQUIRED - must be in .env)
    DATABASE_URL: str  # No default - must come from .env
    
    # Application Settings
    APP_NAME: str = "Patient AI Health Navigator"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )


# Global settings instance
settings = Settings()
