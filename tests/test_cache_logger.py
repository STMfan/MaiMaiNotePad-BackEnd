"""
缓存日志记录测试

测试结构化 JSON 日志格式的正确性。
"""

import pytest
import json
import logging
from unittest.mock import Mock, patch
from app.core.cache.logger import CacheLogger, get_cache_logger


class TestCacheLogger:
    """测试缓存日志记录器"""
    
    @pytest.fixture
    def cache_logger(self):
        """创建缓存日志记录器实例"""
        return CacheLogger("test.cache")
    
    @pytest.fixture
    def mock_logger(self, cache_logger):
        """模拟日志记录器"""
        cache_logger.logger = Mock()
        return cache_logger.logger
    
    def test_log_cache_get_hit(self, cache_logger, mock_logger):
        """测试记录缓存命中"""
        cache_logger.log_cache_get(
            key="user:123",
            hit=True,
            latency_ms=5.2
        )
        
        # 验证日志被调用
        assert mock_logger.info.called
        
        # 解析日志内容
        log_msg = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_msg)
        
        # 验证日志字段
        assert log_data["level"] == "INFO"
        assert log_data["operation"] == "cache_get"
        assert log_data["key"] == "user:123"
        assert log_data["hit"] is True
        assert log_data["latency_ms"] == 5.2
        assert log_data["degraded"] is False
        assert "timestamp" in log_data
        assert "source" in log_data
    
    def test_log_cache_get_miss(self, cache_logger, mock_logger):
        """测试记录缓存未命中"""
        cache_logger.log_cache_get(
            key="user:456",
            hit=False,
            latency_ms=3.1
        )
        
        assert mock_logger.info.called
        log_msg = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_msg)
        
        assert log_data["hit"] is False
        assert log_data["key"] == "user:456"
    
    def test_log_cache_get_with_error(self, cache_logger, mock_logger):
        """测试记录缓存获取错误"""
        cache_logger.log_cache_get(
            key="user:789",
            hit=False,
            latency_ms=10.5,
            degraded=True,
            error="Connection refused"
        )
        
        # 有错误时应该使用 warning 级别
        assert mock_logger.warning.called
        log_msg = mock_logger.warning.call_args[0][0]
        log_data = json.loads(log_msg)
        
        assert log_data["level"] == "WARNING"
        assert log_data["degraded"] is True
        assert log_data["error"] == "Connection refused"
    
    def test_log_cache_set_success(self, cache_logger, mock_logger):
        """测试记录缓存设置成功"""
        cache_logger.log_cache_set(
            key="user:123",
            success=True,
            ttl=3600,
            latency_ms=2.5
        )
        
        assert mock_logger.info.called
        log_msg = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_msg)
        
        assert log_data["operation"] == "cache_set"
        assert log_data["success"] is True
        assert log_data["ttl"] == 3600
        assert log_data["latency_ms"] == 2.5
    
    def test_log_cache_set_failure(self, cache_logger, mock_logger):
        """测试记录缓存设置失败"""
        cache_logger.log_cache_set(
            key="user:123",
            success=False,
            error="Serialization error"
        )
        
        assert mock_logger.warning.called
        log_msg = mock_logger.warning.call_args[0][0]
        log_data = json.loads(log_msg)
        
        assert log_data["success"] is False
        assert log_data["error"] == "Serialization error"
    
    def test_log_cache_invalidate_single_key(self, cache_logger, mock_logger):
        """测试记录单键失效"""
        cache_logger.log_cache_invalidate(
            key="user:123",
            success=True
        )
        
        assert mock_logger.info.called
        log_msg = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_msg)
        
        assert log_data["operation"] == "cache_invalidate"
        assert log_data["key"] == "user:123"
        assert log_data["success"] is True
    
    def test_log_cache_invalidate_pattern(self, cache_logger, mock_logger):
        """测试记录批量失效"""
        cache_logger.log_cache_invalidate(
            pattern="user:*",
            count=10,
            success=True
        )
        
        assert mock_logger.info.called
        log_msg = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_msg)
        
        assert log_data["pattern"] == "user:*"
        assert log_data["count"] == 10
    
    def test_log_cache_degradation(self, cache_logger, mock_logger):
        """测试记录缓存降级事件"""
        cache_logger.log_cache_degradation(
            reason="redis_connection_failed",
            operation="get_cached",
            key="user:123",
            error="Connection timeout",
            fallback="database_query"
        )
        
        assert mock_logger.warning.called
        log_msg = mock_logger.warning.call_args[0][0]
        log_data = json.loads(log_msg)
        
        assert log_data["level"] == "WARNING"
        assert log_data["operation"] == "cache_degradation"
        assert log_data["reason"] == "redis_connection_failed"
        assert log_data["original_operation"] == "get_cached"
        assert log_data["key"] == "user:123"
        assert log_data["error"] == "Connection timeout"
        assert log_data["fallback"] == "database_query"
    
    def test_log_cache_disabled(self, cache_logger, mock_logger):
        """测试记录缓存禁用事件"""
        cache_logger.log_cache_disabled(
            reason="config_enabled_false"
        )
        
        assert mock_logger.info.called
        log_msg = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_msg)
        
        assert log_data["operation"] == "cache_disabled"
        assert log_data["reason"] == "config_enabled_false"
    
    def test_log_cache_enabled(self, cache_logger, mock_logger):
        """测试记录缓存启用事件"""
        cache_logger.log_cache_enabled()
        
        assert mock_logger.info.called
        log_msg = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_msg)
        
        assert log_data["operation"] == "cache_enabled"
    
    def test_get_cache_logger_singleton(self):
        """测试全局日志记录器单例"""
        logger1 = get_cache_logger()
        logger2 = get_cache_logger()
        
        assert logger1 is logger2
    
    def test_json_format_valid(self, cache_logger, mock_logger):
        """测试 JSON 格式有效性"""
        cache_logger.log_cache_get(
            key="test:key",
            hit=True,
            latency_ms=1.0
        )
        
        log_msg = mock_logger.info.call_args[0][0]
        
        # 验证可以解析为 JSON
        try:
            log_data = json.loads(log_msg)
            assert isinstance(log_data, dict)
        except json.JSONDecodeError:
            pytest.fail("日志格式不是有效的 JSON")
    
    def test_timestamp_format(self, cache_logger, mock_logger):
        """测试时间戳格式"""
        cache_logger.log_cache_get(
            key="test:key",
            hit=True,
            latency_ms=1.0
        )
        
        log_msg = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_msg)
        
        # 验证时间戳格式（ISO 8601 with Z suffix）
        timestamp = log_data["timestamp"]
        assert timestamp.endswith("Z")
        assert "T" in timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
