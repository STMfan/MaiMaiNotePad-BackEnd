"""
缓存管理器

提供高级缓存操作，支持序列化、键命名规范、缓存策略、自动降级。
"""

from typing import Optional, Any, Callable, Type
from pydantic import BaseModel
import json
import logging
import inspect
import time
from datetime import datetime
import uuid

from app.core.cache.config import CacheConfig
from app.core.cache.logger import get_cache_logger
from app.core.cache.metrics import get_cache_metrics

logger = logging.getLogger(__name__)


def _is_sqlalchemy_model(obj: Any) -> bool:
    """检查对象是否为 SQLAlchemy 模型实例
    
    Args:
        obj: 要检查的对象
        
    Returns:
        bool: 是否为 SQLAlchemy 模型实例
    """
    try:
        from sqlalchemy.inspection import inspect as sqlalchemy_inspect
        from sqlalchemy.orm.state import InstanceState
        return isinstance(sqlalchemy_inspect(obj), InstanceState)
    except:
        return False


def _serialize_sqlalchemy_object(obj: Any) -> dict:
    """将 SQLAlchemy 对象序列化为字典
    
    只序列化列属性，排除关系属性，以避免循环引用和复杂性。
    
    Args:
        obj: SQLAlchemy 模型实例
        
    Returns:
        dict: 序列化后的字典
    """
    from sqlalchemy.inspection import inspect as sqlalchemy_inspect
    
    result = {}
    inspector = sqlalchemy_inspect(obj)
    
    for column in inspector.mapper.column_attrs:
        value = getattr(obj, column.key)
        
        # 处理特殊类型
        if isinstance(value, datetime):
            result[column.key] = value.isoformat()
        elif isinstance(value, uuid.UUID):
            result[column.key] = str(value)
        else:
            result[column.key] = value
    
    return result


class CacheManager:
    """缓存管理器
    
    提供统一的缓存操作接口，支持自动降级机制。
    当缓存禁用或 Redis 不可用时，自动降级到数据源。
    """
    
    def __init__(
        self,
        redis_client: Optional[Any] = None,
        key_prefix: str = "maimnp",
        enabled: bool = True
    ):
        """初始化缓存管理器
        
        Args:
            redis_client: Redis 客户端实例（可选）
            key_prefix: 缓存键前缀
            enabled: 缓存开关，False 时自动降级
        """
        self.redis_client = redis_client
        self.key_prefix = key_prefix
        self.enabled = enabled
        self.cache_logger = get_cache_logger()
        self.metrics = get_cache_metrics()
        
        # 设置缓存启用状态指标
        self.metrics.set_cache_enabled(enabled)
        
        if not enabled:
            logger.info("缓存已禁用，所有操作将自动降级")
            self.cache_logger.log_cache_disabled()
    
    def is_enabled(self) -> bool:
        """检查缓存是否启用
        
        Returns:
            bool: 缓存是否启用
        """
        return self.enabled and self.redis_client is not None
    
    def build_key(self, resource: str, identifier: str) -> str:
        """构建标准化缓存键
        
        Args:
            resource: 资源类型（如 "user", "knowledge"）
            identifier: 资源标识符（如用户 ID）
            
        Returns:
            str: 标准化的缓存键（格式：prefix:resource:identifier）
        """
        return f"{self.key_prefix}:{resource}:{identifier}"
    
    async def get_cached(
        self,
        key: str,
        fetch_func: Optional[Callable] = None,
        ttl: Optional[int] = None,
        model: Optional[Type[BaseModel]] = None
    ) -> Optional[Any]:
        """获取缓存，支持缓存穿透保护和自动降级
        
        降级行为：
        - 缓存禁用时，直接调用 fetch_func 获取数据
        - Redis 连接失败时，自动降级到 fetch_func
        
        Args:
            key: 缓存键
            fetch_func: 数据获取函数（缓存未命中时调用）
            ttl: 过期时间（秒）
            model: Pydantic 模型类（用于反序列化）
            
        Returns:
            缓存的数据或从数据源获取的数据
        """
        start_time = time.time()
        
        # 缓存禁用，直接降级
        if not self.is_enabled():
            self.cache_logger.log_cache_degradation(
                reason="cache_disabled",
                operation="get_cached",
                key=key,
                fallback="fetch_func"
            )
            self.metrics.record_degradation("cache_disabled")
            if fetch_func:
                # 判断是否为异步函数
                if inspect.iscoroutinefunction(fetch_func):
                    return await fetch_func()
                else:
                    return fetch_func()
            return None
        
        try:
            # 尝试从 Redis 获取缓存
            raw_value = await self.redis_client.get(key)
            latency_ms = (time.time() - start_time) * 1000
            
            if raw_value is not None:
                # 缓存命中
                latency_ms = (time.time() - start_time) * 1000
                self.cache_logger.log_cache_get(
                    key=key,
                    hit=True,
                    latency_ms=latency_ms,
                    degraded=False
                )
                self.metrics.record_cache_hit("get")
                self.metrics.record_operation_duration(
                    "get", "success", (time.time() - start_time)
                )
                
                if raw_value == "NULL_PLACEHOLDER":
                    # 空值缓存（防止缓存穿透）
                    return None
                
                # 反序列化数据
                try:
                    if model is not None:
                        # 反序列化为 Pydantic 模型
                        data_dict = json.loads(raw_value)
                        return model(**data_dict)
                    else:
                        # 反序列化为普通对象
                        return json.loads(raw_value)
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    logger.error(f"缓存数据反序列化失败 (key={key}): {e}")
                    # 删除损坏的缓存
                    await self.redis_client.delete(key)
                    # 继续从数据源获取
            else:
                # 缓存未命中
                latency_ms = (time.time() - start_time) * 1000
                self.cache_logger.log_cache_get(
                    key=key,
                    hit=False,
                    latency_ms=latency_ms,
                    degraded=False
                )
                self.metrics.record_cache_miss("get")
                self.metrics.record_operation_duration(
                    "get", "success", (time.time() - start_time)
                )
        
        except Exception as e:
            # Redis 连接失败，自动降级
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"Redis 连接失败，降级到数据源 (key={key}): {e}")
            self.cache_logger.log_cache_degradation(
                reason="redis_connection_failed",
                operation="get_cached",
                key=key,
                error=str(e),
                fallback="fetch_func"
            )
            self.cache_logger.log_cache_get(
                key=key,
                hit=False,
                latency_ms=latency_ms,
                degraded=True,
                error=str(e)
            )
            self.metrics.record_degradation("redis_connection_failed")
            self.metrics.record_cache_miss("get")
            self.metrics.record_operation_duration(
                "get", "degraded", (time.time() - start_time)
            )
        
        # 缓存未命中或 Redis 故障，从数据源获取
        if fetch_func is None:
            return None
        
        try:
            # 调用数据获取函数
            if inspect.iscoroutinefunction(fetch_func):
                data = await fetch_func()
            else:
                data = fetch_func()
            
            # 缓存数据（包括空值）
            if self.is_enabled():
                try:
                    set_start_time = time.time()
                    if data is None:
                        # 缓存空值，使用较短的 TTL（60秒）
                        await self.redis_client.set(key, "NULL_PLACEHOLDER", ttl=60)
                        set_latency_ms = (time.time() - set_start_time) * 1000
                        self.cache_logger.log_cache_set(
                            key=key,
                            success=True,
                            ttl=60,
                            latency_ms=set_latency_ms,
                            degraded=False
                        )
                    else:
                        # 序列化并缓存数据
                        if isinstance(data, BaseModel):
                            serialized = data.model_dump_json()
                        else:
                            serialized = json.dumps(data, ensure_ascii=False)
                        
                        await self.redis_client.set(key, serialized, ttl=ttl)
                        set_latency_ms = (time.time() - set_start_time) * 1000
                        self.cache_logger.log_cache_set(
                            key=key,
                            success=True,
                            ttl=ttl,
                            latency_ms=set_latency_ms,
                            degraded=False
                        )
                except Exception as e:
                    # 缓存写入失败，记录日志但不影响返回结果
                    logger.warning(f"缓存写入失败 (key={key}): {e}")
                    self.cache_logger.log_cache_set(
                        key=key,
                        success=False,
                        ttl=ttl,
                        degraded=False,
                        error=str(e)
                    )
            
            return data
            
        except Exception as e:
            logger.error(f"数据获取函数执行失败 (key={key}): {e}")
            raise
    
    async def set_cached(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """设置缓存值
        
        降级行为：
        - 缓存禁用时，直接返回 True（不执行缓存操作）
        - Redis 连接失败时，记录日志并返回 False
        
        Args:
            key: 缓存键
            value: 要缓存的值
            ttl: 过期时间（秒）
            
        Returns:
            bool: 操作是否成功
        """
        # 缓存禁用，直接返回成功
        if not self.is_enabled():
            self.cache_logger.log_cache_set(
                key=key,
                success=True,
                ttl=ttl,
                degraded=True
            )
            self.metrics.record_operation_duration("set", "degraded", 0)
            return True
        
        start_time = time.time()
        
        try:
            # 序列化数据
            if isinstance(value, BaseModel):
                serialized = value.model_dump_json()
            elif _is_sqlalchemy_model(value):
                # 处理 SQLAlchemy 对象
                serialized = json.dumps(_serialize_sqlalchemy_object(value), ensure_ascii=False)
            else:
                serialized = json.dumps(value, ensure_ascii=False)
            
            # 写入 Redis
            result = await self.redis_client.set(key, serialized, ttl=ttl)
            latency_ms = (time.time() - start_time) * 1000
            
            self.cache_logger.log_cache_set(
                key=key,
                success=result,
                ttl=ttl,
                latency_ms=latency_ms,
                degraded=False
            )
            self.metrics.record_operation_duration(
                "set", "success" if result else "failed", (time.time() - start_time)
            )
            
            return result
            
        except (TypeError, ValueError) as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"数据序列化失败 (key={key}, type={type(value).__name__}): {e}")
            self.cache_logger.log_cache_set(
                key=key,
                success=False,
                ttl=ttl,
                latency_ms=latency_ms,
                degraded=False,
                error=str(e)
            )
            self.metrics.record_operation_duration(
                "set", "failed", (time.time() - start_time)
            )
            return False
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"缓存写入失败 (key={key}): {e}")
            self.cache_logger.log_cache_set(
                key=key,
                success=False,
                ttl=ttl,
                latency_ms=latency_ms,
                degraded=False,
                error=str(e)
            )
            self.metrics.record_operation_duration(
                "set", "failed", (time.time() - start_time)
            )
            return False
    
    async def invalidate(self, key: str) -> bool:
        """使缓存失效
        
        降级行为：
        - 缓存禁用时，直接返回 True（无需失效操作）
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 操作是否成功
        """
        # 缓存禁用，直接返回成功
        if not self.is_enabled():
            self.cache_logger.log_cache_invalidate(
                key=key,
                success=True,
                degraded=True
            )
            self.metrics.record_operation_duration("invalidate", "degraded", 0)
            return True
        
        start_time = time.time()
        try:
            result = await self.redis_client.delete(key)
            self.cache_logger.log_cache_invalidate(
                key=key,
                success=result,
                degraded=False
            )
            self.metrics.record_operation_duration(
                "invalidate", "success" if result else "failed", (time.time() - start_time)
            )
            return result
        except Exception as e:
            logger.warning(f"缓存失效失败 (key={key}): {e}")
            self.cache_logger.log_cache_invalidate(
                key=key,
                success=False,
                degraded=False,
                error=str(e)
            )
            self.metrics.record_operation_duration(
                "invalidate", "failed", (time.time() - start_time)
            )
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """批量使缓存失效
        
        降级行为：
        - 缓存禁用时，直接返回 0（无需失效操作）
        
        Args:
            pattern: 缓存键模式（支持 * 通配符）
            
        Returns:
            int: 删除的键数量
        """
        # 缓存禁用，直接返回 0
        if not self.is_enabled():
            self.cache_logger.log_cache_invalidate(
                pattern=pattern,
                count=0,
                success=True,
                degraded=True
            )
            self.metrics.record_operation_duration("invalidate_pattern", "degraded", 0)
            return 0
        
        start_time = time.time()
        try:
            deleted_count = await self.redis_client.delete_pattern(pattern)
            self.cache_logger.log_cache_invalidate(
                pattern=pattern,
                count=deleted_count,
                success=True,
                degraded=False
            )
            self.metrics.record_operation_duration(
                "invalidate_pattern", "success", (time.time() - start_time)
            )
            return deleted_count
        except Exception as e:
            logger.warning(f"批量缓存失效失败 (pattern={pattern}): {e}")
            self.cache_logger.log_cache_invalidate(
                pattern=pattern,
                count=0,
                success=False,
                degraded=False,
                error=str(e)
            )
            self.metrics.record_operation_duration(
                "invalidate_pattern", "failed", (time.time() - start_time)
            )
            return 0
