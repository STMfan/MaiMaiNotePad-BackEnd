"""
RedisClient 单元测试

测试 Redis 客户端的核心功能，包括连接管理、基础操作和异常处理。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from app.core.cache.redis_client import RedisClient


class TestRedisClientInitialization:
    """测试 RedisClient 初始化"""
    
    def test_init_with_default_params(self):
        """测试使用默认参数初始化"""
        client = RedisClient()
        
        assert client.host == "localhost"
        assert client.port == 6379
        assert client.db == 0
        assert client.password is None
        assert client.max_connections == 10
        assert client.socket_timeout == 5
        assert client.socket_connect_timeout == 5
        assert client.retry_on_timeout is True
        assert client.decode_responses is True
        assert client._client is None
        assert client._is_connected is False
    
    def test_init_with_custom_params(self):
        """测试使用自定义参数初始化"""
        client = RedisClient(
            host="redis.example.com",
            port=6380,
            db=1,
            password="secret",
            max_connections=20,
            socket_timeout=10,
            socket_connect_timeout=10,
            retry_on_timeout=False,
            decode_responses=False
        )
        
        assert client.host == "redis.example.com"
        assert client.port == 6380
        assert client.db == 1
        assert client.password == "secret"
        assert client.max_connections == 20
        assert client.socket_timeout == 10
        assert client.socket_connect_timeout == 10
        assert client.retry_on_timeout is False
        assert client.decode_responses is False


class TestRedisClientConnection:
    """测试 RedisClient 连接管理"""
    
    @pytest.mark.asyncio
    async def test_ensure_connection_success(self):
        """测试成功建立连接"""
        client = RedisClient()
        
        with patch('app.core.cache.redis_client.aioredis.ConnectionPool') as mock_pool_class, \
             patch('app.core.cache.redis_client.aioredis.Redis') as mock_redis_class:
            
            # 模拟连接池和 Redis 客户端
            mock_pool = MagicMock()
            mock_pool_class.return_value = mock_pool
            
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            mock_redis_class.return_value = mock_redis
            
            # 调用 _ensure_connection
            await client._ensure_connection()
            
            # 验证连接已建立
            assert client._is_connected is True
            assert client._client is not None
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_connection_already_connected(self):
        """测试已连接时不重复建立连接"""
        client = RedisClient()
        client._is_connected = True
        client._client = AsyncMock()
        
        with patch('app.core.cache.redis_client.aioredis.ConnectionPool') as mock_pool_class:
            await client._ensure_connection()
            
            # 验证没有创建新连接
            mock_pool_class.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_ensure_connection_failure(self):
        """测试连接失败"""
        client = RedisClient()
        
        with patch('app.core.cache.redis_client.aioredis.ConnectionPool') as mock_pool_class, \
             patch('app.core.cache.redis_client.aioredis.Redis') as mock_redis_class:
            
            mock_pool = MagicMock()
            mock_pool_class.return_value = mock_pool
            
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(side_effect=ConnectionError("连接失败"))
            mock_redis_class.return_value = mock_redis
            
            # 验证抛出 ConnectionError
            with pytest.raises(ConnectionError):
                await client._ensure_connection()
            
            assert client._is_connected is False
    
    @pytest.mark.asyncio
    async def test_ping_success(self):
        """测试 ping 成功"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.ping = AsyncMock(return_value=True)
            
            result = await client.ping()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_ping_failure(self):
        """测试 ping 失败"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock) as mock_ensure:
            mock_ensure.side_effect = ConnectionError("连接失败")
            
            result = await client.ping()
            
            assert result is False
            assert client._is_connected is False
    
    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭连接"""
        client = RedisClient()
        
        # 模拟已连接状态
        mock_client = AsyncMock()
        mock_pool = AsyncMock()
        client._client = mock_client
        client._connection_pool = mock_pool
        client._is_connected = True
        
        await client.close()
        
        # 验证连接已关闭
        mock_client.close.assert_called_once()
        mock_pool.disconnect.assert_called_once()
        assert client._client is None
        assert client._connection_pool is None
        assert client._is_connected is False


class TestRedisClientBasicOperations:
    """测试 RedisClient 基础操作"""
    
    @pytest.mark.asyncio
    async def test_get_success(self):
        """测试 GET 操作成功"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.get = AsyncMock(return_value="test_value")
            
            result = await client.get("test_key")
            
            assert result == "test_value"
            mock_client.get.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_get_not_found(self):
        """测试 GET 操作键不存在"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.get = AsyncMock(return_value=None)
            
            result = await client.get("nonexistent_key")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_connection_error(self):
        """测试 GET 操作连接失败"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock) as mock_ensure:
            mock_ensure.side_effect = ConnectionError("连接失败")
            
            with pytest.raises(ConnectionError):
                await client.get("test_key")
            
            assert client._is_connected is False
    
    @pytest.mark.asyncio
    async def test_set_success(self):
        """测试 SET 操作成功"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.set = AsyncMock(return_value=True)
            
            result = await client.set("test_key", "test_value")
            
            assert result is True
            mock_client.set.assert_called_once_with("test_key", "test_value")
    
    @pytest.mark.asyncio
    async def test_set_with_ttl(self):
        """测试 SET 操作带 TTL"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.setex = AsyncMock(return_value=True)
            
            result = await client.set("test_key", "test_value", ttl=3600)
            
            assert result is True
            mock_client.setex.assert_called_once_with("test_key", 3600, "test_value")
    
    @pytest.mark.asyncio
    async def test_delete_success(self):
        """测试 DELETE 操作成功"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.delete = AsyncMock(return_value=1)
            
            result = await client.delete("test_key")
            
            assert result is True
            mock_client.delete.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """测试 DELETE 操作键不存在"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.delete = AsyncMock(return_value=0)
            
            result = await client.delete("nonexistent_key")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_exists_true(self):
        """测试 EXISTS 操作键存在"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.exists = AsyncMock(return_value=1)
            
            result = await client.exists("test_key")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_exists_false(self):
        """测试 EXISTS 操作键不存在"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.exists = AsyncMock(return_value=0)
            
            result = await client.exists("nonexistent_key")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_expire_success(self):
        """测试 EXPIRE 操作成功"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.expire = AsyncMock(return_value=1)
            
            result = await client.expire("test_key", 3600)
            
            assert result is True
            mock_client.expire.assert_called_once_with("test_key", 3600)
    
    @pytest.mark.asyncio
    async def test_expire_key_not_found(self):
        """测试 EXPIRE 操作键不存在"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.expire = AsyncMock(return_value=0)
            
            result = await client.expire("nonexistent_key", 3600)
            
            assert result is False


class TestRedisClientBatchOperations:
    """测试 RedisClient 批量操作"""
    
    @pytest.mark.asyncio
    async def test_delete_pattern_success(self):
        """测试批量删除成功"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            # 模拟 SCAN 返回多批键
            mock_client.scan = AsyncMock(side_effect=[
                (10, ["key1", "key2", "key3"]),
                (0, ["key4", "key5"])
            ])
            mock_client.delete = AsyncMock(side_effect=[3, 2])
            
            result = await client.delete_pattern("test:*")
            
            assert result == 5
            assert mock_client.scan.call_count == 2
            assert mock_client.delete.call_count == 2
    
    @pytest.mark.asyncio
    async def test_delete_pattern_no_matches(self):
        """测试批量删除无匹配键"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.scan = AsyncMock(return_value=(0, []))
            
            result = await client.delete_pattern("nonexistent:*")
            
            assert result == 0
            mock_client.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_delete_pattern_connection_error(self):
        """测试批量删除连接失败"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock) as mock_ensure:
            mock_ensure.side_effect = ConnectionError("连接失败")
            
            with pytest.raises(ConnectionError):
                await client.delete_pattern("test:*")
            
            assert client._is_connected is False


class TestRedisClientErrorHandling:
    """测试 RedisClient 异常处理"""
    
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """测试超时异常处理"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.get = AsyncMock(side_effect=TimeoutError("操作超时"))
            
            with pytest.raises(TimeoutError):
                await client.get("test_key")
            
            assert client._is_connected is False
    
    @pytest.mark.asyncio
    async def test_redis_error_handling(self):
        """测试 Redis 异常处理"""
        client = RedisClient()
        
        with patch.object(client, '_ensure_connection', new_callable=AsyncMock), \
             patch.object(client, '_client', new_callable=AsyncMock) as mock_client:
            
            mock_client.get = AsyncMock(side_effect=Exception("未知错误"))
            
            with pytest.raises(RedisError):
                await client.get("test_key")
