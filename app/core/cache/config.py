"""
缓存配置模型

定义缓存系统的配置参数，支持缓存启用/禁用开关。
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CacheConfig(BaseModel):
    """缓存配置模型

    支持缓存启用/禁用开关，禁用时自动降级到数据库访问。
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "enabled": True,
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "password": None,
                "key_prefix": "maimnp",
                "default_ttl": 3600,
                "max_connections": 10,
                "socket_timeout": 5,
                "socket_connect_timeout": 5,
                "retry_on_timeout": True,
            }
        }
    )

    enabled: bool = Field(default=True, description="缓存开关，False 时自动降级到数据库")
    host: str = Field(default="localhost", description="Redis 服务器地址")
    port: int = Field(default=6379, description="Redis 服务器端口")
    db: int = Field(default=0, description="Redis 数据库编号")
    password: str | None = Field(default=None, description="Redis 密码（可选）")
    key_prefix: str = Field(default="maimnp", description="缓存键前缀")
    default_ttl: int = Field(default=3600, description="默认过期时间（秒），默认 1 小时")
    max_connections: int = Field(default=10, description="最大连接数")
    socket_timeout: int = Field(default=5, description="Socket 超时时间（秒）")
    socket_connect_timeout: int = Field(default=5, description="连接超时时间（秒）")
    retry_on_timeout: bool = Field(default=True, description="超时时是否重试")

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """验证端口号范围"""
        if not 1 <= v <= 65535:
            raise ValueError("端口号必须在 1-65535 范围内")
        return v

    @field_validator("db")
    @classmethod
    def validate_db(cls, v: int) -> int:
        """验证数据库编号"""
        if v < 0:
            raise ValueError("数据库编号必须为非负整数")
        return v

    @field_validator("default_ttl")
    @classmethod
    def validate_ttl(cls, v: int) -> int:
        """验证 TTL"""
        if v <= 0:
            raise ValueError("TTL 必须为正整数")
        return v

    @field_validator("max_connections")
    @classmethod
    def validate_max_connections(cls, v: int) -> int:
        """验证最大连接数"""
        if v <= 0:
            raise ValueError("最大连接数必须大于 0")
        return v


def validate_cache_config(config: CacheConfig) -> tuple[bool, list[str]]:
    """验证缓存配置的完整性和合理性

    Args:
        config: 缓存配置实例

    Returns:
        tuple[bool, list[str]]: (是否有效, 警告信息列表)
    """
    warnings = []

    # 如果缓存禁用，跳过大部分验证
    if not config.enabled:
        warnings.append("缓存已禁用，系统将使用降级模式（直接访问数据库）")
        return True, warnings

    # 验证各项配置
    warnings.extend(_validate_connection_settings(config))
    warnings.extend(_validate_ttl_settings(config))
    warnings.extend(_validate_pool_settings(config))
    warnings.extend(_validate_timeout_settings(config))
    warnings.extend(_validate_key_prefix(config))
    warnings.extend(_validate_production_settings(config))

    return True, warnings


def _validate_connection_settings(config: CacheConfig) -> list[str]:
    """验证连接设置"""
    warnings = []

    if not config.host:
        warnings.append("Redis 主机地址为空，可能导致连接失败")

    if config.port != 6379 and config.port < 1024:
        warnings.append(f"Redis 端口 {config.port} 小于 1024，可能需要管理员权限")

    return warnings


def _validate_ttl_settings(config: CacheConfig) -> list[str]:
    """验证 TTL 设置"""
    warnings = []

    if config.default_ttl < 60:
        warnings.append(f"默认 TTL ({config.default_ttl}秒) 过短，可能导致频繁的缓存失效")
    elif config.default_ttl > 86400:
        warnings.append(f"默认 TTL ({config.default_ttl}秒) 过长，可能导致数据不一致")

    return warnings


def _validate_pool_settings(config: CacheConfig) -> list[str]:
    """验证连接池设置"""
    warnings = []

    if config.max_connections < 5:
        warnings.append(f"最大连接数 ({config.max_connections}) 较少，可能影响并发性能")
    elif config.max_connections > 50:
        warnings.append(f"最大连接数 ({config.max_connections}) 较多，可能占用过多资源")

    return warnings


def _validate_timeout_settings(config: CacheConfig) -> list[str]:
    """验证超时设置"""
    warnings = []

    if config.socket_timeout < 1:
        warnings.append(f"Socket 超时 ({config.socket_timeout}秒) 过短，可能导致频繁超时")
    elif config.socket_timeout > 30:
        warnings.append(f"Socket 超时 ({config.socket_timeout}秒) 过长，可能影响响应速度")

    if config.socket_connect_timeout < 1:
        warnings.append(f"连接超时 ({config.socket_connect_timeout}秒) 过短，可能导致连接失败")

    return warnings


def _validate_key_prefix(config: CacheConfig) -> list[str]:
    """验证键前缀"""
    warnings = []

    if not config.key_prefix:
        warnings.append("缓存键前缀为空，可能导致键冲突")
    elif len(config.key_prefix) > 50:
        warnings.append(f"缓存键前缀过长 ({len(config.key_prefix)} 字符)，可能影响性能")

    return warnings


def _validate_production_settings(config: CacheConfig) -> list[str]:
    """验证生产环境设置"""
    warnings = []

    if config.key_prefix.endswith(":prod") or "production" in config.key_prefix.lower():
        if not config.password:
            warnings.append("生产环境建议设置 Redis 密码以提高安全性")

    return warnings


def validate_and_log_config(config: CacheConfig) -> CacheConfig:
    """验证缓存配置并记录警告信息

    Args:
        config: 缓存配置实例

    Returns:
        CacheConfig: 验证后的配置实例

    Raises:
        ValueError: 配置验证失败时抛出
    """
    import logging

    logger = logging.getLogger("app.core.cache.config")

    try:
        # 执行验证
        is_valid, warnings = validate_cache_config(config)

        if not is_valid:
            raise ValueError("缓存配置验证失败")

        # 记录配置信息
        if config.enabled:
            logger.info(
                f"缓存配置已加载: host={config.host}, port={config.port}, "
                f"db={config.db}, prefix={config.key_prefix}, ttl={config.default_ttl}s"
            )
        else:
            logger.info("缓存已禁用，系统将使用降级模式")

        # 记录警告信息
        for warning in warnings:
            logger.warning(f"缓存配置警告: {warning}")

        return config

    except Exception as e:
        logger.error(f"缓存配置验证失败: {e}")
        raise


def create_cache_config_from_settings() -> CacheConfig:
    """从应用配置创建缓存配置实例

    从环境变量和配置文件加载缓存配置，并执行验证。

    Returns:
        CacheConfig: 缓存配置实例

    Raises:
        ValueError: 配置验证失败时抛出
    """
    from app.core.config import settings

    config = CacheConfig(
        enabled=settings.CACHE_ENABLED,
        host=settings.CACHE_HOST,
        port=settings.CACHE_PORT,
        db=settings.CACHE_DB,
        password=settings.CACHE_PASSWORD,
        key_prefix=settings.CACHE_KEY_PREFIX,
        default_ttl=settings.CACHE_DEFAULT_TTL,
        max_connections=settings.CACHE_MAX_CONNECTIONS,
        socket_timeout=settings.CACHE_SOCKET_TIMEOUT,
        socket_connect_timeout=settings.CACHE_SOCKET_CONNECT_TIMEOUT,
        retry_on_timeout=settings.CACHE_RETRY_ON_TIMEOUT,
    )

    # 验证并记录配置
    return validate_and_log_config(config)
