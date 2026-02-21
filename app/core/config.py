"""
应用配置管理模块

使用 Pydantic Settings 从环境变量和 TOML 文件加载配置项。
优先级：环境变量 > config.toml > 默认值
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

# 导入配置管理器
from app.core.config_manager import config_manager


class Settings(BaseSettings):
    """应用配置类，从环境变量和 TOML 文件加载配置"""
    
    # Pydantic V2 配置
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"  # 允许额外字段以提高灵活性
    )
    
    # 应用配置
    APP_NAME: str = config_manager.get("app.name", "MaiMNP Backend")
    APP_VERSION: str = config_manager.get("app.version", "1.0.0")
    HOST: str = config_manager.get("app.host", "0.0.0.0", env_var="HOST")
    PORT: int = config_manager.get_int("app.port", 9278, env_var="PORT")
    
    # 数据库配置
    DATABASE_URL: str = config_manager.get("database.url", "sqlite:///data/mainnp.db", env_var="DATABASE_URL")
    
    # JWT 配置
    JWT_SECRET_KEY: str  # 必须从环境变量读取
    JWT_ALGORITHM: str = config_manager.get("jwt.algorithm", "HS256", env_var="JWT_ALGORITHM")
    JWT_EXPIRATION_HOURS: int = config_manager.get_int("jwt.expiration_hours", 24, env_var="JWT_EXPIRATION_HOURS")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = config_manager.get_int("jwt.access_token_expire_minutes", 15, env_var="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = config_manager.get_int("jwt.refresh_token_expire_days", 7, env_var="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # 邮件配置
    MAIL_HOST: str = config_manager.get("email.host", "smtp.qq.com", env_var="MAIL_HOST")
    MAIL_PORT: int = config_manager.get_int("email.port", 465, env_var="MAIL_PORT")
    MAIL_USER: str  # 必须从环境变量读取
    MAIL_PWD: str  # 必须从环境变量读取
    MAIL_TIMEOUT: int = config_manager.get_int("email.timeout", 30, env_var="MAIL_TIMEOUT")
    
    # 管理员配置
    SUPERADMIN_USERNAME: str = config_manager.get("admin.superadmin_username", "superadmin", env_var="SUPERADMIN_USERNAME")
    SUPERADMIN_PWD: str  # 必须从环境变量读取
    HIGHEST_PASSWORD: str  # 必须从环境变量读取
    EXTERNAL_DOMAIN: str = config_manager.get("admin.external_domain", "example.com", env_var="EXTERNAL_DOMAIN")
    
    # 日志配置
    LOG_LEVEL: str = config_manager.get("logging.level", "INFO", env_var="LOG_LEVEL")
    LOG_FILE: str = config_manager.get("logging.file", "logs/app.log", env_var="LOG_FILE")
    
    # 上传配置
    MAX_FILE_SIZE_MB: int = config_manager.get_int("upload.max_file_size_mb", 100, env_var="MAX_FILE_SIZE_MB")
    UPLOAD_DIR: str = config_manager.get("upload.base_dir", "uploads", env_var="UPLOAD_DIR")
    
    # 安全配置
    BCRYPT_ROUNDS: int = config_manager.get_int("security.bcrypt_rounds", 12, env_var="PASSLIB_BCRYPT_ROUNDS")
    MAX_FAILED_LOGIN_ATTEMPTS: int = config_manager.get_int("security.max_failed_login_attempts", 5)
    ACCOUNT_LOCK_DURATION_MINUTES: int = config_manager.get_int("security.account_lock_duration_minutes", 30)
    
    # 邮箱验证配置
    EMAIL_CODE_EXPIRE_MINUTES: int = config_manager.get_int("email_verification.code_expire_minutes", 2)
    EMAIL_HOURLY_LIMIT: int = config_manager.get_int("email_verification.hourly_limit", 5)
    EMAIL_MINUTE_LIMIT: int = config_manager.get_int("email_verification.minute_limit", 1)
    
    # 分页配置
    DEFAULT_PAGE_SIZE: int = config_manager.get_int("pagination.default_page_size", 20)
    MAX_PAGE_SIZE: int = config_manager.get_int("pagination.max_page_size", 100)
    ADMIN_DEFAULT_PAGE_SIZE: int = config_manager.get_int("pagination.admin_default_page_size", 10)
    
    # 统计配置
    MIN_TREND_DAYS: int = config_manager.get_int("statistics.min_trend_days", 1)
    MAX_TREND_DAYS: int = config_manager.get_int("statistics.max_trend_days", 90)
    DEFAULT_TREND_DAYS: int = config_manager.get_int("statistics.default_trend_days", 30)
    
    # 测试配置（可选）
    MAIMNP_BASE_URL: Optional[str] = None
    MAIMNP_USERNAME: Optional[str] = None
    MAIMNP_PASSWORD: Optional[str] = None
    MAIMNP_EMAIL: Optional[str] = None


# 全局配置实例
settings = Settings()
