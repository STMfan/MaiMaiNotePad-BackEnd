"""
应用配置管理模块

使用 Pydantic Settings 从环境变量加载配置项。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置类，从环境变量加载配置"""
    
    # Pydantic V2 配置
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"  # 允许额外字段以提高灵活性
    )
    
    # 应用配置
    APP_NAME: str = "MaiMNP Backend"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 9278
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///data/mainnp.db"
    
    # JWT 配置
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 邮件配置
    MAIL_HOST: str = "smtp.qq.com"
    MAIL_PORT: int = 465
    MAIL_USER: str
    MAIL_PWD: str
    MAIL_TIMEOUT: int = 30
    
    # 管理员配置
    SUPERADMIN_USERNAME: str = "superadmin"
    SUPERADMIN_PWD: str
    HIGHEST_PASSWORD: str
    EXTERNAL_DOMAIN: str = "example.com"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # 上传配置
    MAX_FILE_SIZE_MB: int = 100
    UPLOAD_DIR: str = "uploads"
    
    # 测试配置（可选）
    MAIMNP_BASE_URL: Optional[str] = None
    MAIMNP_USERNAME: Optional[str] = None
    MAIMNP_PASSWORD: Optional[str] = None
    MAIMNP_EMAIL: Optional[str] = None


# 全局配置实例
settings = Settings()
