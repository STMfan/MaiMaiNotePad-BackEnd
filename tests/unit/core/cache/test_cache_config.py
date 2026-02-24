"""
缓存配置模型测试

测试 CacheConfig 的验证规则和配置加载。
"""

import pytest
from pydantic import ValidationError

from app.core.cache.config import CacheConfig, create_cache_config_from_settings


class TestCacheConfig:
    """测试 CacheConfig 模型"""

    def test_default_config(self):
        """测试默认配置"""
        config = CacheConfig()

        assert config.enabled is True
        assert config.host == "localhost"
        assert config.port == 6379
        assert config.db == 0
        assert config.password is None
        assert config.key_prefix == "maimnp"
        assert config.default_ttl == 3600
        assert config.max_connections == 10
        assert config.socket_timeout == 5
        assert config.socket_connect_timeout == 5
        assert config.retry_on_timeout is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = CacheConfig(
            enabled=False,
            host="redis.example.com",
            port=6380,
            db=1,
            password="secret",
            key_prefix="test",
            default_ttl=1800,
            max_connections=20,
        )

        assert config.enabled is False
        assert config.host == "redis.example.com"
        assert config.port == 6380
        assert config.db == 1
        assert config.password == "secret"
        assert config.key_prefix == "test"
        assert config.default_ttl == 1800
        assert config.max_connections == 20

    def test_port_validation(self):
        """测试端口号验证"""
        # 有效端口
        config = CacheConfig(port=6379)
        assert config.port == 6379

        # 无效端口（小于 1）
        with pytest.raises(ValidationError) as exc_info:
            CacheConfig(port=0)
        assert "端口号必须在 1-65535 范围内" in str(exc_info.value)

        # 无效端口（大于 65535）
        with pytest.raises(ValidationError) as exc_info:
            CacheConfig(port=65536)
        assert "端口号必须在 1-65535 范围内" in str(exc_info.value)

    def test_db_validation(self):
        """测试数据库编号验证"""
        # 有效数据库编号
        config = CacheConfig(db=0)
        assert config.db == 0

        config = CacheConfig(db=15)
        assert config.db == 15

        # 无效数据库编号（负数）
        with pytest.raises(ValidationError) as exc_info:
            CacheConfig(db=-1)
        assert "数据库编号必须为非负整数" in str(exc_info.value)

    def test_ttl_validation(self):
        """测试 TTL 验证"""
        # 有效 TTL
        config = CacheConfig(default_ttl=3600)
        assert config.default_ttl == 3600

        # 无效 TTL（零）
        with pytest.raises(ValidationError) as exc_info:
            CacheConfig(default_ttl=0)
        assert "TTL 必须为正整数" in str(exc_info.value)

        # 无效 TTL（负数）
        with pytest.raises(ValidationError) as exc_info:
            CacheConfig(default_ttl=-1)
        assert "TTL 必须为正整数" in str(exc_info.value)

    def test_max_connections_validation(self):
        """测试最大连接数验证"""
        # 有效连接数
        config = CacheConfig(max_connections=10)
        assert config.max_connections == 10

        # 无效连接数（零）
        with pytest.raises(ValidationError) as exc_info:
            CacheConfig(max_connections=0)
        assert "最大连接数必须大于 0" in str(exc_info.value)

        # 无效连接数（负数）
        with pytest.raises(ValidationError) as exc_info:
            CacheConfig(max_connections=-1)
        assert "最大连接数必须大于 0" in str(exc_info.value)

    def test_disabled_cache_config(self):
        """测试缓存禁用配置"""
        config = CacheConfig(enabled=False)

        assert config.enabled is False
        # 其他配置仍然有效
        assert config.host == "localhost"
        assert config.port == 6379


class TestCreateCacheConfigFromSettings:
    """测试从应用配置创建缓存配置"""

    def test_create_from_settings(self):
        """测试从 settings 创建配置"""
        config = create_cache_config_from_settings()

        # 验证配置已加载
        assert isinstance(config, CacheConfig)
        assert isinstance(config.enabled, bool)
        assert isinstance(config.host, str)
        assert isinstance(config.port, int)
        assert isinstance(config.db, int)
        assert isinstance(config.key_prefix, str)
        assert isinstance(config.default_ttl, int)
        assert isinstance(config.max_connections, int)

        # 验证配置值合理
        assert 1 <= config.port <= 65535
        assert config.db >= 0
        assert config.default_ttl > 0
        assert config.max_connections > 0
