"""
CacheManager 单元测试

测试缓存管理器的核心功能，包括：
- 缓存启用和禁用状态
- 序列化/反序列化
- 缓存键构建规则
- 缓存穿透保护
- 批量失效操作
- 降级场景处理
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel
from typing import Optional

from app.core.cache.manager import CacheManager


# 测试用的 Pydantic 模型
class UserModel(BaseModel):
    """测试用户模型"""
    id: str
    username: str
    email: str


class TestCacheManagerInitialization:
    """测试 CacheManager 初始化"""
    
    def test_init_with_enabled_cache(self):
        """测试启用缓存的初始化"""
        mock_redis = MagicMock()
        manager = CacheManager(
            redis_client=mock_redis,
            key_prefix="test",
            enabled=True
        )
        
        assert manager.redis_client is mock_redis
        assert manager.key_prefix == "test"
        assert manager.enabled is True
        assert manager.is_enabled() is True
    
    def test_init_with_disabled_cache(self):
        """测试禁用缓存的初始化"""
        mock_redis = MagicMock()
        manager = CacheManager(
            redis_client=mock_redis,
            key_prefix="test",
            enabled=False
        )
        
        assert manager.redis_client is mock_redis
        assert manager.enabled is False
        assert manager.is_enabled() is False
    
    def test_init_without_redis_client(self):
        """测试没有 Redis 客户端的初始化"""
        manager = CacheManager(
            redis_client=None,
            key_prefix="test",
            enabled=True
        )
        
        assert manager.redis_client is None
        assert manager.is_enabled() is False
    
    def test_init_with_default_params(self):
        """测试使用默认参数初始化"""
        manager = CacheManager()
        
        assert manager.redis_client is None
        assert manager.key_prefix == "maimnp"
        assert manager.enabled is True
        assert manager.is_enabled() is False  # 因为没有 redis_client


class TestCacheManagerKeyBuilding:
    """测试 CacheManager 缓存键构建"""
    
    def test_build_key_basic(self):
        """测试基础键构建"""
        manager = CacheManager(key_prefix="maimnp")
        
        key = manager.build_key("user", "123")
        
        assert key == "maimnp:user:123"
    
    def test_build_key_with_custom_prefix(self):
        """测试自定义前缀的键构建"""
        manager = CacheManager(key_prefix="custom")
        
        key = manager.build_key("knowledge", "456")
        
        assert key == "custom:knowledge:456"
    
    def test_build_key_with_different_resources(self):
        """测试不同资源类型的键构建"""
        manager = CacheManager(key_prefix="test")
        
        user_key = manager.build_key("user", "u123")
        kb_key = manager.build_key("knowledge_base", "kb456")
        persona_key = manager.build_key("persona", "p789")
        
        assert user_key == "test:user:u123"
        assert kb_key == "test:knowledge_base:kb456"
        assert persona_key == "test:persona:p789"


class TestCacheManagerGetCached:
    """测试 CacheManager get_cached 方法"""
    
    @pytest.mark.asyncio
    async def test_get_cached_hit_with_json(self):
        """测试缓存命中（JSON 数据）"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value='{"id": "123", "name": "test"}')
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        result = await manager.get_cached("test:key")
        
        assert result == {"id": "123", "name": "test"}
        mock_redis.get.assert_called_once_with("test:key")
    
    @pytest.mark.asyncio
    async def test_get_cached_hit_with_pydantic_model(self):
        """测试缓存命中（Pydantic 模型）"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(
            return_value='{"id": "123", "username": "alice", "email": "alice@example.com"}'
        )
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        result = await manager.get_cached("user:123", model=UserModel)
        
        assert isinstance(result, UserModel)
        assert result.id == "123"
        assert result.username == "alice"
        assert result.email == "alice@example.com"
    
    @pytest.mark.asyncio
    async def test_get_cached_miss_without_fetch_func(self):
        """测试缓存未命中且无 fetch_func"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        result = await manager.get_cached("test:key")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_cached_miss_with_sync_fetch_func(self):
        """测试缓存未命中使用同步 fetch_func"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        def fetch_data():
            return {"id": "123", "data": "from_db"}
        
        result = await manager.get_cached("test:key", fetch_func=fetch_data, ttl=3600)
        
        assert result == {"id": "123", "data": "from_db"}
        mock_redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_cached_miss_with_async_fetch_func(self):
        """测试缓存未命中使用异步 fetch_func"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        async def fetch_data():
            return {"id": "456", "data": "from_async_db"}
        
        result = await manager.get_cached("test:key", fetch_func=fetch_data, ttl=1800)
        
        assert result == {"id": "456", "data": "from_async_db"}
        mock_redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_cached_null_placeholder(self):
        """测试缓存穿透保护（空值缓存）"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="NULL_PLACEHOLDER")
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        result = await manager.get_cached("test:key")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_cached_stores_null_value(self):
        """测试缓存空值（防止缓存穿透）"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        def fetch_none():
            return None
        
        result = await manager.get_cached("test:key", fetch_func=fetch_none)
        
        assert result is None
        # 验证空值被缓存，TTL 为 60 秒
        mock_redis.set.assert_called_once_with("test:key", "NULL_PLACEHOLDER", ttl=60)
    
    @pytest.mark.asyncio
    async def test_get_cached_disabled_with_sync_fetch_func(self):
        """测试缓存禁用时使用同步 fetch_func"""
        manager = CacheManager(redis_client=None, enabled=False)
        
        def fetch_data():
            return {"id": "789", "data": "direct_from_db"}
        
        result = await manager.get_cached("test:key", fetch_func=fetch_data)
        
        assert result == {"id": "789", "data": "direct_from_db"}
    
    @pytest.mark.asyncio
    async def test_get_cached_disabled_with_async_fetch_func(self):
        """测试缓存禁用时使用异步 fetch_func"""
        manager = CacheManager(redis_client=None, enabled=False)
        
        async def fetch_data():
            return {"id": "999", "data": "async_direct_from_db"}
        
        result = await manager.get_cached("test:key", fetch_func=fetch_data)
        
        assert result == {"id": "999", "data": "async_direct_from_db"}
    
    @pytest.mark.asyncio
    async def test_get_cached_disabled_without_fetch_func(self):
        """测试缓存禁用且无 fetch_func"""
        manager = CacheManager(redis_client=None, enabled=False)
        
        result = await manager.get_cached("test:key")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_cached_redis_connection_failure(self):
        """测试 Redis 连接失败时自动降级"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("连接失败"))
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        def fetch_data():
            return {"id": "111", "data": "fallback_data"}
        
        result = await manager.get_cached("test:key", fetch_func=fetch_data)
        
        assert result == {"id": "111", "data": "fallback_data"}
    
    @pytest.mark.asyncio
    async def test_get_cached_deserialization_error(self):
        """测试反序列化失败时的处理"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="invalid json{")
        mock_redis.delete = AsyncMock(return_value=True)
        mock_redis.set = AsyncMock(return_value=True)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        def fetch_data():
            return {"id": "222", "data": "fresh_data"}
        
        result = await manager.get_cached("test:key", fetch_func=fetch_data)
        
        assert result == {"id": "222", "data": "fresh_data"}
        # 验证损坏的缓存被删除
        mock_redis.delete.assert_called_once_with("test:key")


class TestCacheManagerSetCached:
    """测试 CacheManager set_cached 方法"""
    
    @pytest.mark.asyncio
    async def test_set_cached_with_dict(self):
        """测试缓存字典数据"""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        data = {"id": "123", "name": "test"}
        result = await manager.set_cached("test:key", data, ttl=3600)
        
        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "test:key"
        assert json.loads(call_args[0][1]) == data
        assert call_args[1]["ttl"] == 3600
    
    @pytest.mark.asyncio
    async def test_set_cached_with_pydantic_model(self):
        """测试缓存 Pydantic 模型"""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        user = UserModel(id="456", username="bob", email="bob@example.com")
        result = await manager.set_cached("user:456", user, ttl=1800)
        
        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "user:456"
        # 验证序列化的数据
        serialized_data = json.loads(call_args[0][1])
        assert serialized_data["id"] == "456"
        assert serialized_data["username"] == "bob"
    
    @pytest.mark.asyncio
    async def test_set_cached_without_ttl(self):
        """测试缓存数据不设置 TTL"""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        data = {"id": "789"}
        result = await manager.set_cached("test:key", data)
        
        assert result is True
        call_args = mock_redis.set.call_args
        assert call_args[1]["ttl"] is None
    
    @pytest.mark.asyncio
    async def test_set_cached_disabled(self):
        """测试缓存禁用时设置缓存"""
        manager = CacheManager(redis_client=None, enabled=False)
        
        data = {"id": "999"}
        result = await manager.set_cached("test:key", data, ttl=3600)
        
        # 缓存禁用时直接返回 True，不执行任何操作
        assert result is True
    
    @pytest.mark.asyncio
    async def test_set_cached_serialization_error(self):
        """测试序列化失败的处理"""
        mock_redis = AsyncMock()
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        # 创建一个不可序列化的对象
        class UnserializableObject:
            def __init__(self):
                self.file = open(__file__)  # 文件对象不可序列化
        
        obj = UnserializableObject()
        result = await manager.set_cached("test:key", obj)
        
        assert result is False
        obj.file.close()
    
    @pytest.mark.asyncio
    async def test_set_cached_redis_failure(self):
        """测试 Redis 写入失败"""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(side_effect=Exception("写入失败"))
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        data = {"id": "111"}
        result = await manager.set_cached("test:key", data)
        
        assert result is False


class TestCacheManagerInvalidate:
    """测试 CacheManager invalidate 方法"""
    
    @pytest.mark.asyncio
    async def test_invalidate_success(self):
        """测试成功使缓存失效"""
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=True)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        result = await manager.invalidate("test:key")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("test:key")
    
    @pytest.mark.asyncio
    async def test_invalidate_key_not_found(self):
        """测试失效不存在的键"""
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=False)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        result = await manager.invalidate("nonexistent:key")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_invalidate_disabled(self):
        """测试缓存禁用时失效操作"""
        manager = CacheManager(redis_client=None, enabled=False)
        
        result = await manager.invalidate("test:key")
        
        # 缓存禁用时直接返回 True
        assert result is True
    
    @pytest.mark.asyncio
    async def test_invalidate_redis_failure(self):
        """测试 Redis 失效操作失败"""
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(side_effect=Exception("删除失败"))
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        result = await manager.invalidate("test:key")
        
        assert result is False


class TestCacheManagerInvalidatePattern:
    """测试 CacheManager invalidate_pattern 方法"""
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern_success(self):
        """测试成功批量失效缓存"""
        mock_redis = AsyncMock()
        mock_redis.delete_pattern = AsyncMock(return_value=5)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        result = await manager.invalidate_pattern("user:*")
        
        assert result == 5
        mock_redis.delete_pattern.assert_called_once_with("user:*")
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern_no_matches(self):
        """测试批量失效无匹配键"""
        mock_redis = AsyncMock()
        mock_redis.delete_pattern = AsyncMock(return_value=0)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        result = await manager.invalidate_pattern("nonexistent:*")
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern_disabled(self):
        """测试缓存禁用时批量失效操作"""
        manager = CacheManager(redis_client=None, enabled=False)
        
        result = await manager.invalidate_pattern("test:*")
        
        # 缓存禁用时直接返回 0
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern_redis_failure(self):
        """测试 Redis 批量失效操作失败"""
        mock_redis = AsyncMock()
        mock_redis.delete_pattern = AsyncMock(side_effect=Exception("批量删除失败"))
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        result = await manager.invalidate_pattern("test:*")
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern_with_different_patterns(self):
        """测试不同模式的批量失效"""
        mock_redis = AsyncMock()
        mock_redis.delete_pattern = AsyncMock(side_effect=[3, 7, 0])
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        result1 = await manager.invalidate_pattern("user:*")
        result2 = await manager.invalidate_pattern("knowledge:*")
        result3 = await manager.invalidate_pattern("empty:*")
        
        assert result1 == 3
        assert result2 == 7
        assert result3 == 0


class TestCacheManagerComplexScenarios:
    """测试 CacheManager 复杂场景"""
    
    @pytest.mark.asyncio
    async def test_cache_workflow_enabled(self):
        """测试完整的缓存工作流（启用状态）"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=[None, '{"id": "123", "data": "cached"}'])
        mock_redis.set = AsyncMock(return_value=True)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        # 第一次获取：缓存未命中，从数据源获取
        def fetch_data():
            return {"id": "123", "data": "cached"}
        
        result1 = await manager.get_cached("test:key", fetch_func=fetch_data, ttl=3600)
        assert result1 == {"id": "123", "data": "cached"}
        mock_redis.set.assert_called_once()
        
        # 第二次获取：缓存命中
        result2 = await manager.get_cached("test:key")
        assert result2 == {"id": "123", "data": "cached"}
    
    @pytest.mark.asyncio
    async def test_cache_workflow_disabled(self):
        """测试完整的缓存工作流（禁用状态）"""
        manager = CacheManager(redis_client=None, enabled=False)
        
        call_count = 0
        
        def fetch_data():
            nonlocal call_count
            call_count += 1
            return {"id": "456", "data": f"call_{call_count}"}
        
        # 第一次获取：直接从数据源获取
        result1 = await manager.get_cached("test:key", fetch_func=fetch_data)
        assert result1 == {"id": "456", "data": "call_1"}
        
        # 第二次获取：仍然从数据源获取（缓存禁用）
        result2 = await manager.get_cached("test:key", fetch_func=fetch_data)
        assert result2 == {"id": "456", "data": "call_2"}
        
        # 验证每次都调用了 fetch_func
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_cache_with_pydantic_model_workflow(self):
        """测试 Pydantic 模型的完整缓存流程"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        user = UserModel(id="789", username="charlie", email="charlie@example.com")
        
        # 设置缓存
        set_result = await manager.set_cached("user:789", user, ttl=3600)
        assert set_result is True
        
        # 模拟从 Redis 获取
        mock_redis.get = AsyncMock(
            return_value='{"id": "789", "username": "charlie", "email": "charlie@example.com"}'
        )
        
        # 获取缓存
        cached_user = await manager.get_cached("user:789", model=UserModel)
        assert isinstance(cached_user, UserModel)
        assert cached_user.id == "789"
        assert cached_user.username == "charlie"
    
    @pytest.mark.asyncio
    async def test_cache_penetration_protection(self):
        """测试缓存穿透保护机制"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=[None, "NULL_PLACEHOLDER"])
        mock_redis.set = AsyncMock(return_value=True)
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        fetch_call_count = 0
        
        def fetch_nonexistent_data():
            nonlocal fetch_call_count
            fetch_call_count += 1
            return None
        
        # 第一次查询：数据不存在，缓存空值
        result1 = await manager.get_cached("nonexistent:key", fetch_func=fetch_nonexistent_data)
        assert result1 is None
        assert fetch_call_count == 1
        # 验证空值被缓存
        mock_redis.set.assert_called_once_with("nonexistent:key", "NULL_PLACEHOLDER", ttl=60)
        
        # 第二次查询：命中空值缓存，不再调用 fetch_func
        result2 = await manager.get_cached("nonexistent:key", fetch_func=fetch_nonexistent_data)
        assert result2 is None
        assert fetch_call_count == 1  # fetch_func 没有被再次调用
    
    @pytest.mark.asyncio
    async def test_degradation_on_redis_failure(self):
        """测试 Redis 故障时的自动降级"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis 连接失败"))
        
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        def fetch_data():
            return {"id": "999", "data": "fallback"}
        
        # Redis 失败，自动降级到 fetch_func
        result = await manager.get_cached("test:key", fetch_func=fetch_data)
        
        assert result == {"id": "999", "data": "fallback"}
