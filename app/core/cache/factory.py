"""
缓存工厂函数

提供创建和初始化缓存组件的工厂函数。
"""

import logging

from app.core.cache.config import CacheConfig, create_cache_config_from_settings
from app.core.cache.manager import CacheManager
from app.core.cache.redis_client import RedisClient

logger = logging.getLogger(__name__)


def create_redis_client(config: CacheConfig) -> RedisClient | None:
    """根据配置创建 Redis 客户端

    Args:
        config: 缓存配置

    Returns:
        RedisClient 实例，如果缓存禁用则返回 None
    """
    if not config.enabled:
        logger.info("缓存已禁用，跳过 Redis 客户端创建")
        return None

    try:
        redis_client = RedisClient(
            host=config.host,
            port=config.port,
            db=config.db,
            password=config.password,
            max_connections=config.max_connections,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout,
            retry_on_timeout=config.retry_on_timeout,
        )
        logger.info("Redis 客户端创建成功")
        return redis_client
    except Exception as e:
        logger.error(f"Redis 客户端创建失败: {e}")
        return None


def create_cache_manager(config: CacheConfig | None = None, redis_client: RedisClient | None = None) -> CacheManager:
    """创建缓存管理器

    Args:
        config: 缓存配置（可选，默认从应用配置加载）
        redis_client: Redis 客户端实例（可选，如果不提供则根据配置创建）

    Returns:
        CacheManager 实例
    """
    # 如果未提供配置，从应用配置加载
    if config is None:
        config = create_cache_config_from_settings()

    # 如果未提供 Redis 客户端，根据配置创建
    if redis_client is None and config.enabled:
        redis_client = create_redis_client(config)

    # 创建缓存管理器
    cache_manager = CacheManager(redis_client=redis_client, key_prefix=config.key_prefix, enabled=config.enabled)

    logger.info(f"缓存管理器创建成功 (enabled={config.enabled}, " f"prefix={config.key_prefix})")

    return cache_manager


# 全局缓存管理器实例（延迟初始化）
_global_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例

    使用单例模式，确保整个应用使用同一个缓存管理器实例。

    Returns:
        CacheManager 实例
    """
    global _global_cache_manager

    if _global_cache_manager is None:
        _global_cache_manager = create_cache_manager()

    return _global_cache_manager


def reset_cache_manager() -> None:
    """重置全局缓存管理器

    用于测试或重新加载配置时重置缓存管理器。
    """
    global _global_cache_manager
    _global_cache_manager = None
    logger.info("全局缓存管理器已重置")
