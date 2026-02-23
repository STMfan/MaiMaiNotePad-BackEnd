"""
缓存监控指标模块

提供 Prometheus 格式的监控指标导出，用于监控缓存性能和降级情况。
"""

from prometheus_client import Counter, Gauge, Histogram
import logging

logger = logging.getLogger(__name__)


# 缓存命中/未命中计数器
cache_hits_total = Counter(
    'cache_hits_total',
    '缓存命中总次数',
    ['operation']  # operation: get, middleware
)

cache_misses_total = Counter(
    'cache_misses_total',
    '缓存未命中总次数',
    ['operation']  # operation: get, middleware
)

# 缓存降级计数器
cache_degradation_total = Counter(
    'cache_degradation_total',
    '缓存降级总次数',
    ['reason']  # reason: disabled, connection_failed, timeout, etc.
)

# 缓存启用状态
cache_enabled_status = Gauge(
    'cache_enabled_status',
    '缓存启用状态（1=启用，0=禁用）'
)

# 缓存操作耗时
cache_operation_duration = Histogram(
    'cache_operation_duration_seconds',
    '缓存操作耗时（秒）',
    ['operation', 'status'],  # operation: get, set, invalidate; status: success, degraded, failed
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)


class CacheMetrics:
    """缓存指标记录器
    
    提供便捷的方法来记录各种缓存指标。
    """
    
    @staticmethod
    def record_cache_hit(operation: str = "get") -> None:
        """记录缓存命中
        
        Args:
            operation: 操作类型（get, middleware）
        """
        cache_hits_total.labels(operation=operation).inc()
    
    @staticmethod
    def record_cache_miss(operation: str = "get") -> None:
        """记录缓存未命中
        
        Args:
            operation: 操作类型（get, middleware）
        """
        cache_misses_total.labels(operation=operation).inc()
    
    @staticmethod
    def record_degradation(reason: str) -> None:
        """记录缓存降级事件
        
        Args:
            reason: 降级原因（disabled, connection_failed, timeout, etc.）
        """
        cache_degradation_total.labels(reason=reason).inc()
        logger.debug(f"记录降级指标: reason={reason}")
    
    @staticmethod
    def set_cache_enabled(enabled: bool) -> None:
        """设置缓存启用状态
        
        Args:
            enabled: 是否启用（True=1, False=0）
        """
        cache_enabled_status.set(1 if enabled else 0)
        logger.debug(f"设置缓存状态指标: enabled={enabled}")
    
    @staticmethod
    def record_operation_duration(
        operation: str,
        status: str,
        duration_seconds: float
    ) -> None:
        """记录缓存操作耗时
        
        Args:
            operation: 操作类型（get, set, invalidate）
            status: 操作状态（success, degraded, failed）
            duration_seconds: 操作耗时（秒）
        """
        cache_operation_duration.labels(
            operation=operation,
            status=status
        ).observe(duration_seconds)
    
    @staticmethod
    def get_cache_hit_rate() -> float:
        """计算缓存命中率
        
        Returns:
            float: 缓存命中率（0-100）
        """
        try:
            # 获取所有 operation 标签的命中和未命中总数
            hits = sum(
                sample.value
                for sample in cache_hits_total.collect()[0].samples
            )
            misses = sum(
                sample.value
                for sample in cache_misses_total.collect()[0].samples
            )
            
            total = hits + misses
            if total == 0:
                return 0.0
            
            return (hits / total) * 100
        except Exception as e:
            logger.error(f"计算缓存命中率失败: {e}")
            return 0.0


# 全局指标记录器实例
_metrics: CacheMetrics = CacheMetrics()


def get_cache_metrics() -> CacheMetrics:
    """获取全局缓存指标记录器实例
    
    Returns:
        CacheMetrics: 缓存指标记录器实例
    """
    return _metrics
