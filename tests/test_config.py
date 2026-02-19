"""
Unit tests for configuration module
"""

import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError
from app.core.config import Settings


class TestConfigurationLoading:
    """测试配置加载"""
    
    def test_config_loads_from_env_file(self):
        """测试从 .env 文件加载配置"""
        # 配置应该从 .env 文件加载
        settings = Settings()
        assert settings.APP_NAME is not None
        assert settings.JWT_SECRET_KEY is not None
    
    def test_config_requires_jwt_secret_key(self):
        """测试 JWT_SECRET_KEY 是必需的"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            
            # 验证错误信息包含 JWT_SECRET_KEY
            errors = exc_info.value.errors()
            field_names = [error['loc'][0] for error in errors]
            assert 'JWT_SECRET_KEY' in field_names
    
    def test_config_requires_mail_credentials(self):
        """测试邮件凭证是必需的"""
        with patch.dict(os.environ, {'JWT_SECRET_KEY': 'test_key'}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            
            errors = exc_info.value.errors()
            field_names = [error['loc'][0] for error in errors]
            assert 'MAIL_USER' in field_names
            assert 'MAIL_PWD' in field_names
    
    def test_config_requires_admin_credentials(self):
        """测试管理员凭证是必需的"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd'
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            
            errors = exc_info.value.errors()
            field_names = [error['loc'][0] for error in errors]
            assert 'SUPERADMIN_PWD' in field_names
            assert 'HIGHEST_PASSWORD' in field_names


class TestConfigurationDefaults:
    """测试默认值"""
    
    def test_app_name_default(self):
        """测试应用名称默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.APP_NAME == "MaiMNP Backend"
    
    def test_app_version_default(self):
        """测试应用版本默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.APP_VERSION == "1.0.0"
    
    def test_host_default(self):
        """测试主机地址默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.HOST == "0.0.0.0"
    
    def test_port_default(self):
        """测试端口默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.PORT == 9278
    
    def test_database_url_default(self):
        """测试数据库 URL 默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.DATABASE_URL == "sqlite:///data/mainnp.db"
    
    def test_jwt_algorithm_default(self):
        """测试 JWT 算法默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.JWT_ALGORITHM == "HS256"
    
    def test_jwt_expiration_defaults(self):
        """测试 JWT 过期时间默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.JWT_EXPIRATION_HOURS == 24
            assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 15
            assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7
    
    def test_mail_defaults(self):
        """测试邮件配置默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.MAIL_HOST == "smtp.qq.com"
            assert settings.MAIL_PORT == 465
            assert settings.MAIL_TIMEOUT == 30
    
    def test_admin_username_default(self):
        """测试管理员用户名默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.SUPERADMIN_USERNAME == "superadmin"
    
    def test_external_domain_default(self):
        """测试外部域名默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.EXTERNAL_DOMAIN == "example.com"
    
    def test_log_defaults(self):
        """测试日志配置默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.LOG_LEVEL == "INFO"
            assert settings.LOG_FILE == "logs/app.log"
    
    def test_upload_defaults(self):
        """测试上传配置默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.MAX_FILE_SIZE_MB == 100
            assert settings.UPLOAD_DIR == "uploads"
    
    def test_optional_test_config_defaults(self):
        """测试可选测试配置默认值"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.MAIMNP_BASE_URL is None
            assert settings.MAIMNP_USERNAME is None
            assert settings.MAIMNP_PASSWORD is None
            assert settings.MAIMNP_EMAIL is None


class TestEnvironmentVariableOverride:
    """测试环境变量覆盖"""
    
    def test_override_app_name(self):
        """测试覆盖应用名称"""
        with patch.dict(os.environ, {
            'APP_NAME': 'Custom App Name',
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.APP_NAME == "Custom App Name"
    
    def test_override_port(self):
        """测试覆盖端口"""
        with patch.dict(os.environ, {
            'PORT': '8080',
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.PORT == 8080
    
    def test_override_database_url(self):
        """测试覆盖数据库 URL"""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://localhost/testdb',
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.DATABASE_URL == "postgresql://localhost/testdb"
    
    def test_override_jwt_settings(self):
        """测试覆盖 JWT 设置"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'custom_secret_key',
            'JWT_ALGORITHM': 'HS512',
            'JWT_ACCESS_TOKEN_EXPIRE_MINUTES': '30',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.JWT_SECRET_KEY == "custom_secret_key"
            assert settings.JWT_ALGORITHM == "HS512"
            assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30
    
    def test_override_mail_settings(self):
        """测试覆盖邮件设置"""
        with patch.dict(os.environ, {
            'MAIL_HOST': 'smtp.gmail.com',
            'MAIL_PORT': '587',
            'MAIL_USER': 'custom@gmail.com',
            'MAIL_PWD': 'custom_pwd',
            'MAIL_TIMEOUT': '60',
            'JWT_SECRET_KEY': 'test_key',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.MAIL_HOST == "smtp.gmail.com"
            assert settings.MAIL_PORT == 587
            assert settings.MAIL_USER == "custom@gmail.com"
            assert settings.MAIL_PWD == "custom_pwd"
            assert settings.MAIL_TIMEOUT == 60
    
    def test_override_admin_settings(self):
        """测试覆盖管理员设置"""
        with patch.dict(os.environ, {
            'SUPERADMIN_USERNAME': 'customadmin',
            'SUPERADMIN_PWD': 'custom_admin_pwd',
            'HIGHEST_PASSWORD': 'custom_highest_pwd',
            'EXTERNAL_DOMAIN': 'custom.com',
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.SUPERADMIN_USERNAME == "customadmin"
            assert settings.SUPERADMIN_PWD == "custom_admin_pwd"
            assert settings.HIGHEST_PASSWORD == "custom_highest_pwd"
            assert settings.EXTERNAL_DOMAIN == "custom.com"
    
    def test_override_log_settings(self):
        """测试覆盖日志设置"""
        with patch.dict(os.environ, {
            'LOG_LEVEL': 'DEBUG',
            'LOG_FILE': 'custom/path/app.log',
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.LOG_LEVEL == "DEBUG"
            assert settings.LOG_FILE == "custom/path/app.log"
    
    def test_override_upload_settings(self):
        """测试覆盖上传设置"""
        with patch.dict(os.environ, {
            'MAX_FILE_SIZE_MB': '200',
            'UPLOAD_DIR': 'custom_uploads',
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.MAX_FILE_SIZE_MB == 200
            assert settings.UPLOAD_DIR == "custom_uploads"
    
    def test_override_optional_test_config(self):
        """测试覆盖可选测试配置"""
        with patch.dict(os.environ, {
            'MAIMNP_BASE_URL': 'http://test.example.com',
            'MAIMNP_USERNAME': 'testuser',
            'MAIMNP_PASSWORD': 'testpass',
            'MAIMNP_EMAIL': 'test@test.com',
            'JWT_SECRET_KEY': 'test_key',
            'MAIL_USER': 'test@example.com',
            'MAIL_PWD': 'test_pwd',
            'SUPERADMIN_PWD': 'admin_pwd',
            'HIGHEST_PASSWORD': 'highest_pwd'
        }, clear=True):
            settings = Settings(_env_file=None)
            assert settings.MAIMNP_BASE_URL == "http://test.example.com"
            assert settings.MAIMNP_USERNAME == "testuser"
            assert settings.MAIMNP_PASSWORD == "testpass"
            assert settings.MAIMNP_EMAIL == "test@test.com"
