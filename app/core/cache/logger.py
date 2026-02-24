"""
缓存日志记录模块

提供结构化的 JSON 日志格式，记录缓存操作、降级事件和缓存禁用等信息。
"""

import json
import logging
from datetime import datetime
from typing import Any


class CacheLogger:
    """缓存日志记录器

    提供结构化的 JSON 日志格式，用于记录缓存相关的操作和事件。
    """

    def __init__(self, logger_name: str = "app.core.cache"):
        """初始化缓存日志记录器

        Args:
            logger_name: 日志记录器名称
        """
        self.logger = logging.getLogger(logger_name)

    def _format_log(self, level: str, operation: str, **kwargs) -> str:
        """格式化日志为 JSON 字符串

        Args:
            level: 日志级别（INFO, WARNING, ERROR）
            operation: 操作类型
            **kwargs: 其他日志字段

        Returns:
            str: JSON 格式的日志字符串
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "operation": operation,
            "source": "CacheManager",
            **kwargs,
        }
        return json.dumps(log_data, ensure_ascii=False)

    def log_cache_get(
        self, key: str, hit: bool, latency_ms: float, degraded: bool = False, error: str | None = None
    ) -> None:
        """记录缓存获取操作

        Args:
            key: 缓存键
            hit: 是否命中缓存
            latency_ms: 操作延迟（毫秒）
            degraded: 是否降级
            error: 错误信息（可选）
        """
        log_msg = self._format_log(
            level="INFO" if not error else "WARNING",
            operation="cache_get",
            key=key,
            hit=hit,
            latency_ms=round(latency_ms, 2),
            degraded=degraded,
        )

        if error:
            log_data = json.loads(log_msg)
            log_data["error"] = error
            log_msg = json.dumps(log_data, ensure_ascii=False)
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)

    def log_cache_set(
        self,
        key: str,
        success: bool,
        ttl: int | None = None,
        latency_ms: float | None = None,
        degraded: bool = False,
        error: str | None = None,
    ) -> None:
        """记录缓存设置操作

        Args:
            key: 缓存键
            success: 操作是否成功
            ttl: 过期时间（秒）
            latency_ms: 操作延迟（毫秒）
            degraded: 是否降级
            error: 错误信息（可选）
        """
        log_data = {"key": key, "success": success, "degraded": degraded}

        if ttl is not None:
            log_data["ttl"] = ttl

        if latency_ms is not None:
            log_data["latency_ms"] = round(latency_ms, 2)

        if error:
            log_data["error"] = error

        log_msg = self._format_log(level="INFO" if success else "WARNING", operation="cache_set", **log_data)

        if success:
            self.logger.info(log_msg)
        else:
            self.logger.warning(log_msg)

    def log_cache_invalidate(
        self,
        key: str | None = None,
        pattern: str | None = None,
        count: int = 0,
        success: bool = True,
        degraded: bool = False,
        error: str | None = None,
    ) -> None:
        """记录缓存失效操作

        Args:
            key: 缓存键（单键失效）
            pattern: 缓存键模式（批量失效）
            count: 删除的键数量
            success: 操作是否成功
            degraded: 是否降级
            error: 错误信息（可选）
        """
        log_data: dict[str, Any] = {"success": success, "degraded": degraded}

        if key:
            log_data["key"] = key

        if pattern:
            log_data["pattern"] = pattern
            log_data["count"] = count

        if error:
            log_data["error"] = error

        log_msg = self._format_log(level="INFO" if success else "WARNING", operation="cache_invalidate", **log_data)

        if success:
            self.logger.info(log_msg)
        else:
            self.logger.warning(log_msg)

    def log_cache_degradation(
        self,
        reason: str,
        operation: str,
        key: str | None = None,
        error: str | None = None,
        fallback: str = "database_query",
    ) -> None:
        """记录缓存降级事件

        Args:
            reason: 降级原因（redis_connection_failed, timeout, etc.）
            operation: 触发降级的操作
            key: 相关的缓存键（可选）
            error: 错误信息（可选）
            fallback: 降级后的回退方案
        """
        log_data = {"reason": reason, "original_operation": operation, "fallback": fallback}

        if key:
            log_data["key"] = key

        if error:
            log_data["error"] = error

        log_msg = self._format_log(level="WARNING", operation="cache_degradation", **log_data)

        self.logger.warning(log_msg)

    def log_cache_disabled(self, reason: str = "config_enabled_false") -> None:
        """记录缓存禁用事件

        Args:
            reason: 禁用原因
        """
        log_msg = self._format_log(level="INFO", operation="cache_disabled", reason=reason)

        self.logger.info(log_msg)

    def log_cache_enabled(self) -> None:
        """记录缓存启用事件"""
        log_msg = self._format_log(level="INFO", operation="cache_enabled")

        self.logger.info(log_msg)


# 全局缓存日志记录器实例
_cache_logger: CacheLogger | None = None


def get_cache_logger() -> CacheLogger:
    """获取全局缓存日志记录器实例

    Returns:
        CacheLogger: 缓存日志记录器实例
    """
    global _cache_logger
    if _cache_logger is None:
        _cache_logger = CacheLogger()
    return _cache_logger
