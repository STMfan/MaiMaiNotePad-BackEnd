"""
缓存模块

提供 Redis 缓存功能，支持自动降级机制。
当缓存禁用或 Redis 不可用时，自动降级到数据库访问。
"""

from app.core.cache.config import CacheConfig, create_cache_config_from_settings
from app.core.cache.decorators import cache_invalidate, cached
from app.core.cache.factory import create_cache_manager, create_redis_client, get_cache_manager, reset_cache_manager
from app.core.cache.logger import CacheLogger, get_cache_logger
from app.core.cache.manager import CacheManager
from app.core.cache.metrics import (
    CacheMetrics,
    cache_degradation_total,
    cache_enabled_status,
    cache_hits_total,
    cache_misses_total,
    cache_operation_duration,
    get_cache_metrics,
)
from app.core.cache.middleware import CacheMiddleware
from app.core.cache.redis_client import RedisClient

__all__ = [
    "CacheConfig",
    "CacheManager",
    "RedisClient",
    "create_cache_config_from_settings",
    "create_redis_client",
    "create_cache_manager",
    "get_cache_manager",
    "reset_cache_manager",
    "cached",
    "cache_invalidate",
    "CacheMiddleware",
    "CacheLogger",
    "get_cache_logger",
    "CacheMetrics",
    "get_cache_metrics",
    "cache_hits_total",
    "cache_misses_total",
    "cache_degradation_total",
    "cache_enabled_status",
    "cache_operation_duration",
]
