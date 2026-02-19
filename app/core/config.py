"""
Configuration management using Pydantic Settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Pydantic V2 configuration using ConfigDict
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"  # Allow extra fields for flexibility
    )
    
    # Application configuration
    APP_NAME: str = "MaiMNP Backend"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 9278
    
    # Database configuration
    DATABASE_URL: str = "sqlite:///data/mainnp.db"
    
    # JWT configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Email configuration
    MAIL_HOST: str = "smtp.qq.com"
    MAIL_PORT: int = 465
    MAIL_USER: str
    MAIL_PWD: str
    MAIL_TIMEOUT: int = 30
    
    # Admin configuration
    SUPERADMIN_USERNAME: str = "superadmin"
    SUPERADMIN_PWD: str
    HIGHEST_PASSWORD: str
    EXTERNAL_DOMAIN: str = "example.com"
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Upload configuration
    MAX_FILE_SIZE_MB: int = 100
    UPLOAD_DIR: str = "uploads"
    
    # Test configuration (optional)
    MAIMNP_BASE_URL: Optional[str] = None
    MAIMNP_USERNAME: Optional[str] = None
    MAIMNP_PASSWORD: Optional[str] = None
    MAIMNP_EMAIL: Optional[str] = None


# Global settings instance
settings = Settings()
