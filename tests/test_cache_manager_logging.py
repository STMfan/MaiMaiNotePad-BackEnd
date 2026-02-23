"""
缓存管理器日志记录集成测试

测试 CacheManager 与 CacheLogger 的集成，验证各种操作的日志记录。
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.core.cache.manager import CacheManager
from app.core.cache.redis_client import RedisClient


class TestCacheManagerLogging:
    """测试缓存管理器的日志记录功能"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """创建模拟的 Redis 客户端"""
        client = AsyncMock(spec=RedisClient)
        return client
    
    @pytest.fixture
    def cache_manager(self, mock_redis_client):
        """创建缓存管理器实例"""
        return CacheManager(
            redis_client=mock_redis_client,
            key_prefix="test",
            enabled=True
        )
    
    @pytest.fixture
    def disabled_cache_manager(self):
        """创建禁用的缓存管理器实例"""
        return CacheManager(
            redis_client=None,
            key_prefix="test",
            enabled=False
        )
    
    @pytest.mark.asyncio
    async def test_get_cached_logs_hit(self, cache_manager, mock_redis_client):
        """测试缓存命中时的日志记录"""
        # 模拟缓存命中
        mock_redis_client.get.return_value = '{"name": "test"}'
        
        with patch.object(cache_manager.cache_logger, 'log_cache_get') as mock_log:
            result = await cache_manager.get_cached("test:key")
            
            # 验证日志被调用
            assert mock_log.called
            call_args = mock_log.call_args[1]
            assert call_args['key'] == "test:key"
            assert call_args['hit'] is True
            assert call_args['degraded'] is False
            assert 'latency_ms' in call_args
    
    @pytest.mark.asyncio
    async def test_get_cached_logs_miss(self, cache_manager, mock_redis_client):
        """测试缓存未命中时的日志记录"""
        # 模拟缓存未命中
        mock_redis_client.get.return_value = None
        
        async def fetch_data():
            return {"name": "test"}
        
        with patch.object(cache_manager.cache_logger, 'log_cache_get') as mock_log_get, \
             patch.object(cache_manager.cache_logger, 'log_cache_set') as mock_log_set:
            
            result = await cache_manager.get_cached(
                "test:key",
                fetch_func=fetch_data
            )
            
            # 验证缓存未命中日志
            assert mock_log_get.called
            call_args = mock_log_get.call_args[1]
            assert call_args['hit'] is False
            
            # 验证缓存写入日志
            assert mock_log_set.called
    
    @pytest.mark.asyncio
    async def test_get_cached_logs_degradation(self, cache_manager, mock_redis_client):
        """测试 Redis 故障时的降级日志"""
        # 模拟 Redis 连接失败
        mock_redis_client.get.side_effect = Exception("Connection failed")
        
        async def fetch_data():
            return {"name": "test"}
        
        with patch.object(cache_manager.cache_logger, 'log_cache_degradation') as mock_log_deg, \
             patch.object(cache_manager.cache_logger, 'log_cache_get') as mock_log_get:
            
            result = await cache_manager.get_cached(
                "test:key",
                fetch_func=fetch_data
            )
            
            # 验证降级日志
            assert mock_log_deg.called
            call_args = mock_log_deg.call_args[1]
            assert call_args['reason'] == "redis_connection_failed"
            assert call_args['operation'] == "get_cached"
            assert call_args['key'] == "test:key"
            assert 'error' in call_args
            
            # 验证缓存获取日志包含降级标记
            assert mock_log_get.called
            call_args = mock_log_get.call_args[1]
            assert call_args['degraded'] is True
    
    @pytest.mark.asyncio
    async def test_set_cached_logs_success(self, cache_manager, mock_redis_client):
        """测试缓存设置成功的日志记录"""
        mock_redis_client.set.return_value = True
        
        with patch.object(cache_manager.cache_logger, 'log_cache_set') as mock_log:
            result = await cache_manager.set_cached(
                "test:key",
                {"name": "test"},
                ttl=3600
            )
            
            # 验证日志被调用
            assert mock_log.called
            call_args = mock_log.call_args[1]
            assert call_args['key'] == "test:key"
            assert call_args['success'] is True
            assert call_args['ttl'] == 3600
            assert call_args['degraded'] is False
            assert 'latency_ms' in call_args
    
    @pytest.mark.asyncio
    async def test_set_cached_logs_failure(self, cache_manager, mock_redis_client):
        """测试缓存设置失败的日志记录"""
        mock_redis_client.set.side_effect = Exception("Write failed")
        
        with patch.object(cache_manager.cache_logger, 'log_cache_set') as mock_log:
            result = await cache_manager.set_cached(
                "test:key",
                {"name": "test"}
            )
            
            # 验证日志被调用
            assert mock_log.called
            call_args = mock_log.call_args[1]
            assert call_args['success'] is False
            assert 'error' in call_args
    
    @pytest.mark.asyncio
    async def test_invalidate_logs_success(self, cache_manager, mock_redis_client):
        """测试缓存失效成功的日志记录"""
        mock_redis_client.delete.return_value = True
        
        with patch.object(cache_manager.cache_logger, 'log_cache_invalidate') as mock_log:
            result = await cache_manager.invalidate("test:key")
            
            # 验证日志被调用
            assert mock_log.called
            call_args = mock_log.call_args[1]
            assert call_args['key'] == "test:key"
            assert call_args['success'] is True
            assert call_args['degraded'] is False
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern_logs_success(self, cache_manager, mock_redis_client):
        """测试批量失效成功的日志记录"""
        mock_redis_client.delete_pattern.return_value = 10
        
        with patch.object(cache_manager.cache_logger, 'log_cache_invalidate') as mock_log:
            result = await cache_manager.invalidate_pattern("test:*")
            
            # 验证日志被调用
            assert mock_log.called
            call_args = mock_log.call_args[1]
            assert call_args['pattern'] == "test:*"
            assert call_args['count'] == 10
            assert call_args['success'] is True
    
    @pytest.mark.asyncio
    async def test_disabled_cache_logs_degradation(self, disabled_cache_manager):
        """测试缓存禁用时的降级日志"""
        async def fetch_data():
            return {"name": "test"}
        
        with patch.object(disabled_cache_manager.cache_logger, 'log_cache_degradation') as mock_log:
            result = await disabled_cache_manager.get_cached(
                "test:key",
                fetch_func=fetch_data
            )
            
            # 验证降级日志
            assert mock_log.called
            call_args = mock_log.call_args[1]
            assert call_args['reason'] == "cache_disabled"
            assert call_args['operation'] == "get_cached"
    
    @pytest.mark.asyncio
    async def test_disabled_cache_set_logs_degraded(self, disabled_cache_manager):
        """测试缓存禁用时设置操作的日志"""
        with patch.object(disabled_cache_manager.cache_logger, 'log_cache_set') as mock_log:
            result = await disabled_cache_manager.set_cached(
                "test:key",
                {"name": "test"}
            )
            
            # 验证日志标记为降级
            assert mock_log.called
            call_args = mock_log.call_args[1]
            assert call_args['degraded'] is True
            assert call_args['success'] is True
    
    @pytest.mark.asyncio
    async def test_disabled_cache_invalidate_logs_degraded(self, disabled_cache_manager):
        """测试缓存禁用时失效操作的日志"""
        with patch.object(disabled_cache_manager.cache_logger, 'log_cache_invalidate') as mock_log:
            result = await disabled_cache_manager.invalidate("test:key")
            
            # 验证日志标记为降级
            assert mock_log.called
            call_args = mock_log.call_args[1]
            assert call_args['degraded'] is True
    
    def test_cache_disabled_log_on_init(self):
        """测试初始化时记录缓存禁用日志"""
        with patch('app.core.cache.manager.get_cache_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            manager = CacheManager(
                redis_client=None,
                enabled=False
            )
            
            # 验证缓存禁用日志被调用
            assert mock_logger.log_cache_disabled.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
