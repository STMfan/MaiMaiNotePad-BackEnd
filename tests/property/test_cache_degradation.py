"""
缓存降级透明性属性测试

测试缓存管理器的降级机制，验证缓存启用和禁用时的行为一致性。

**Validates: Requirements 2.2 - 降级策略**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
from unittest.mock import AsyncMock

from app.core.cache.manager import CacheManager


# ============================================================================
# 测试数据模型
# ============================================================================

class TestModel(BaseModel):
    """测试用的 Pydantic 模型"""
    id: str
    name: str
    value: int
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Hypothesis 策略定义
# ============================================================================

# 缓存键策略
cache_keys = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters=':_-'
    )
)

# 字典值策略
dict_values = st.dictionaries(
    st.text(min_size=1, max_size=20),
    st.one_of(
        st.text(max_size=50),
        st.integers(min_value=-1000, max_value=1000),
        st.booleans(),
    ),
    min_size=1,
    max_size=10
)

# Pydantic 模型策略
test_models = st.builds(
    TestModel,
    id=st.text(min_size=1, max_size=20),
    name=st.text(min_size=1, max_size=50),
    value=st.integers(min_value=0, max_value=10000),
    metadata=st.one_of(
        st.none(),
        st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.text(max_size=20),
            max_size=3
        )
    )
)


# ============================================================================
# 辅助函数
# ============================================================================

def create_mock_redis():
    """创建模拟的 Redis 客户端
    
    Returns:
        AsyncMock: 模拟的 Redis 客户端，支持基本的 get/set/delete 操作
    """
    mock_redis = AsyncMock()
    storage = {}
    ttl_storage = {}
    
    async def mock_set(key, value, ttl=None):
        storage[key] = value
        if ttl is not None:
            ttl_storage[key] = ttl
        return True
    
    async def mock_get(key):
        return storage.get(key)
    
    async def mock_delete(key):
        if key in storage:
            del storage[key]
            if key in ttl_storage:
                del ttl_storage[key]
            return True
        return False
    
    async def mock_exists(key):
        return key in storage
    
    async def mock_delete_pattern(pattern):
        """模拟批量删除操作"""
        # 简单实现：删除所有匹配的键
        import fnmatch
        deleted_count = 0
        keys_to_delete = []
        
        for key in list(storage.keys()):
            if fnmatch.fnmatch(key, pattern):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            await mock_delete(key)
            deleted_count += 1
        
        return deleted_count
    
    mock_redis.set = mock_set
    mock_redis.get = mock_get
    mock_redis.delete = mock_delete
    mock_redis.exists = mock_exists
    mock_redis.delete_pattern = mock_delete_pattern
    mock_redis._storage = storage
    mock_redis._ttl_storage = ttl_storage
    
    return mock_redis


# ============================================================================
# 属性测试类
# ============================================================================

class TestCacheDegradationTransparency:
    """
    测试属性 6: 缓存降级透明性

    **Property 6: Cache Degradation Transparency**
    当缓存禁用或 Redis 不可用时，系统必须自动降级到数据源，
    且对调用方透明。

    数学表示:
    ∀k, f: (cache_enabled = False ∨ redis_unavailable = True) ⟹ 
      (get_cached(k, fetch_func=f) = f() ∧ no_redis_operation_executed)

    **Validates: Requirements 2.2 - 降级策略**
    """

    @given(key=cache_keys, value=dict_values)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_disabled_cache_returns_same_value(self, key, value):
        """
        属性测试：缓存禁用时返回值一致性

        验证缓存启用和禁用时，get_cached() 返回相同的值。

        **Validates: Requirements 2.2**
        """
        # 创建模拟 Redis 客户端
        mock_redis = create_mock_redis()
        
        # 定义数据获取函数
        def fetch_func():
            return value
        
        # 场景 1：缓存启用
        manager_enabled = CacheManager(redis_client=mock_redis, enabled=True)
        result_enabled = await manager_enabled.get_cached(key, fetch_func=fetch_func)
        
        # 场景 2：缓存禁用
        manager_disabled = CacheManager(redis_client=None, enabled=False)
        result_disabled = await manager_disabled.get_cached(key, fetch_func=fetch_func)
        
        # 验证透明性：两种情况返回相同的值
        assert result_enabled == result_disabled == value, (
            f"缓存启用和禁用时应该返回相同的值\n"
            f"期望值: {value}\n"
            f"缓存启用: {result_enabled}\n"
            f"缓存禁用: {result_disabled}"
        )

    @given(key=cache_keys, model=test_models)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_disabled_cache_model_consistency(self, key, model):
        """
        属性测试：缓存禁用时 Pydantic 模型一致性

        验证缓存启用和禁用时，Pydantic 模型返回值一致。

        **Validates: Requirements 2.2**
        """
        # 创建模拟 Redis 客户端
        mock_redis = create_mock_redis()
        
        # 定义数据获取函数
        def fetch_func():
            return model
        
        # 场景 1：缓存启用
        manager_enabled = CacheManager(redis_client=mock_redis, enabled=True)
        result_enabled = await manager_enabled.get_cached(
            key, 
            fetch_func=fetch_func,
            model=TestModel
        )
        
        # 场景 2：缓存禁用
        manager_disabled = CacheManager(redis_client=None, enabled=False)
        result_disabled = await manager_disabled.get_cached(
            key, 
            fetch_func=fetch_func,
            model=TestModel
        )
        
        # 验证透明性
        assert result_enabled == result_disabled == model, (
            f"缓存启用和禁用时模型应该一致\n"
            f"期望: {model}\n"
            f"缓存启用: {result_enabled}\n"
            f"缓存禁用: {result_disabled}"
        )

    @given(key=cache_keys, value=dict_values)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_disabled_cache_no_redis_operations(self, key, value):
        """
        属性测试：缓存禁用时不访问 Redis

        验证缓存禁用时，不执行任何 Redis 操作。

        **Validates: Requirements 2.2**
        """
        # 创建模拟 Redis 客户端（带调用计数）
        mock_redis = create_mock_redis()
        
        # 记录 Redis 操作次数
        redis_call_count = 0
        original_get = mock_redis.get
        original_set = mock_redis.set
        
        async def counted_get(key):
            nonlocal redis_call_count
            redis_call_count += 1
            return await original_get(key)
        
        async def counted_set(key, value, ttl=None):
            nonlocal redis_call_count
            redis_call_count += 1
            return await original_set(key, value, ttl)
        
        mock_redis.get = counted_get
        mock_redis.set = counted_set
        
        # 定义数据获取函数
        def fetch_func():
            return value
        
        # 缓存禁用
        manager_disabled = CacheManager(redis_client=mock_redis, enabled=False)
        result = await manager_disabled.get_cached(key, fetch_func=fetch_func)
        
        # 验证：不访问 Redis
        assert redis_call_count == 0, (
            f"缓存禁用时不应该访问 Redis\n"
            f"Redis 操作次数: {redis_call_count}"
        )
        
        # 验证：返回正确的值
        assert result == value

    @given(key=cache_keys, value=dict_values)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_async_fetch_func_degradation(self, key, value):
        """
        属性测试：异步 fetch_func 降级透明性

        验证使用异步 fetch_func 时的降级透明性。

        **Validates: Requirements 2.2**
        """
        # 创建模拟 Redis 客户端
        mock_redis = create_mock_redis()
        
        # 定义异步数据获取函数
        async def async_fetch_func():
            await asyncio.sleep(0.01)  # 模拟异步操作
            return value
        
        # 场景 1：缓存启用
        manager_enabled = CacheManager(redis_client=mock_redis, enabled=True)
        result_enabled = await manager_enabled.get_cached(key, fetch_func=async_fetch_func)
        
        # 场景 2：缓存禁用
        manager_disabled = CacheManager(redis_client=None, enabled=False)
        result_disabled = await manager_disabled.get_cached(key, fetch_func=async_fetch_func)
        
        # 验证透明性
        assert result_enabled == result_disabled == value, (
            f"异步 fetch_func 在缓存启用和禁用时应该返回相同的值\n"
            f"期望值: {value}\n"
            f"缓存启用: {result_enabled}\n"
            f"缓存禁用: {result_disabled}"
        )


class TestCacheDegradationNoExceptions:
    """
    测试降级过程不抛出异常

    验证缓存禁用或 Redis 故障时，操作不会抛出异常。

    **Validates: Requirements 2.2**
    """

    @given(key=cache_keys, value=dict_values)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_get_cached_no_exception_when_disabled(self, key, value):
        """
        属性测试：缓存禁用时 get_cached 不抛出异常

        **Validates: Requirements 2.2**
        """
        # 缓存禁用（redis_client 为 None）
        manager = CacheManager(redis_client=None, enabled=False)
        
        def fetch_func():
            return value
        
        # 不应该抛出异常
        try:
            result = await manager.get_cached(key, fetch_func=fetch_func)
            assert result == value
        except Exception as e:
            pytest.fail(f"缓存禁用时不应该抛出异常: {e}")

    @given(key=cache_keys, value=dict_values)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_set_cached_no_exception_when_disabled(self, key, value):
        """
        属性测试：缓存禁用时 set_cached 不抛出异常

        **Validates: Requirements 2.2**
        """
        # 缓存禁用
        manager = CacheManager(redis_client=None, enabled=False)
        
        # 不应该抛出异常
        try:
            result = await manager.set_cached(key, value)
            assert result is True  # 缓存禁用时应该返回 True
        except Exception as e:
            pytest.fail(f"缓存禁用时不应该抛出异常: {e}")

    @given(key=cache_keys)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_invalidate_no_exception_when_disabled(self, key):
        """
        属性测试：缓存禁用时 invalidate 不抛出异常

        **Validates: Requirements 2.2**
        """
        # 缓存禁用
        manager = CacheManager(redis_client=None, enabled=False)
        
        # 不应该抛出异常
        try:
            result = await manager.invalidate(key)
            assert result is True  # 缓存禁用时应该返回 True
        except Exception as e:
            pytest.fail(f"缓存禁用时不应该抛出异常: {e}")

    @given(pattern=st.text(min_size=1, max_size=20))
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_invalidate_pattern_no_exception_when_disabled(self, pattern):
        """
        属性测试：缓存禁用时 invalidate_pattern 不抛出异常

        **Validates: Requirements 2.2**
        """
        # 缓存禁用
        manager = CacheManager(redis_client=None, enabled=False)
        
        # 不应该抛出异常
        try:
            result = await manager.invalidate_pattern(pattern)
            assert result == 0  # 缓存禁用时应该返回 0
        except Exception as e:
            pytest.fail(f"缓存禁用时不应该抛出异常: {e}")


class TestCacheDegradationOperationBehavior:
    """
    测试缓存禁用时各操作的行为

    验证缓存禁用时，各操作返回预期的值。

    **Validates: Requirements 2.2**
    """

    @given(key=cache_keys, value=dict_values)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_set_cached_returns_true_when_disabled(self, key, value):
        """
        属性测试：缓存禁用时 set_cached 返回 True

        验证缓存禁用时，set_cached 直接返回 True（不执行缓存操作）。

        **Validates: Requirements 2.2**
        """
        manager = CacheManager(redis_client=None, enabled=False)
        
        result = await manager.set_cached(key, value)
        
        assert result is True, (
            f"缓存禁用时 set_cached 应该返回 True\n"
            f"实际返回: {result}"
        )

    @given(key=cache_keys)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_invalidate_returns_true_when_disabled(self, key):
        """
        属性测试：缓存禁用时 invalidate 返回 True

        **Validates: Requirements 2.2**
        """
        manager = CacheManager(redis_client=None, enabled=False)
        
        result = await manager.invalidate(key)
        
        assert result is True, (
            f"缓存禁用时 invalidate 应该返回 True\n"
            f"实际返回: {result}"
        )

    @given(pattern=st.text(min_size=1, max_size=20))
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_invalidate_pattern_returns_zero_when_disabled(self, pattern):
        """
        属性测试：缓存禁用时 invalidate_pattern 返回 0

        **Validates: Requirements 2.2**
        """
        manager = CacheManager(redis_client=None, enabled=False)
        
        result = await manager.invalidate_pattern(pattern)
        
        assert result == 0, (
            f"缓存禁用时 invalidate_pattern 应该返回 0\n"
            f"实际返回: {result}"
        )

    @given(key=cache_keys, value=dict_values)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_get_cached_without_fetch_func_when_disabled(self, key, value):
        """
        属性测试：缓存禁用时 get_cached 无 fetch_func 返回 None

        **Validates: Requirements 2.2**
        """
        manager = CacheManager(redis_client=None, enabled=False)
        
        # 不提供 fetch_func
        result = await manager.get_cached(key)
        
        assert result is None, (
            f"缓存禁用且无 fetch_func 时应该返回 None\n"
            f"实际返回: {result}"
        )


class TestCacheDegradationEdgeCases:
    """
    测试缓存降级的边界情况

    **Validates: Requirements 2.2**
    """

    @pytest.mark.asyncio
    async def test_none_value_degradation(self):
        """
        测试：None 值降级透明性

        验证 fetch_func 返回 None 时的降级透明性。

        **Validates: Requirements 2.2**
        """
        mock_redis = create_mock_redis()
        key = "test:none"
        
        def fetch_none():
            return None
        
        # 缓存启用
        manager_enabled = CacheManager(redis_client=mock_redis, enabled=True)
        result_enabled = await manager_enabled.get_cached(key, fetch_func=fetch_none)
        
        # 缓存禁用
        manager_disabled = CacheManager(redis_client=None, enabled=False)
        result_disabled = await manager_disabled.get_cached(key, fetch_func=fetch_none)
        
        # 验证透明性
        assert result_enabled is None
        assert result_disabled is None
        assert result_enabled == result_disabled

    @pytest.mark.asyncio
    async def test_empty_dict_degradation(self):
        """
        测试：空字典降级透明性

        **Validates: Requirements 2.2**
        """
        mock_redis = create_mock_redis()
        key = "test:empty_dict"
        value = {}
        
        def fetch_func():
            return value
        
        # 缓存启用
        manager_enabled = CacheManager(redis_client=mock_redis, enabled=True)
        result_enabled = await manager_enabled.get_cached(key, fetch_func=fetch_func)
        
        # 缓存禁用
        manager_disabled = CacheManager(redis_client=None, enabled=False)
        result_disabled = await manager_disabled.get_cached(key, fetch_func=fetch_func)
        
        # 验证透明性
        assert result_enabled == result_disabled == value

    @pytest.mark.asyncio
    async def test_unicode_value_degradation(self):
        """
        测试：Unicode 值降级透明性

        验证包含中文等 Unicode 字符的数据降级透明性。

        **Validates: Requirements 2.2**
        """
        mock_redis = create_mock_redis()
        key = "test:unicode"
        value = {
            "name": "测试用户",
            "description": "这是一个包含中文的描述",
            "emoji": "😀🎉🚀"
        }
        
        def fetch_func():
            return value
        
        # 缓存启用
        manager_enabled = CacheManager(redis_client=mock_redis, enabled=True)
        result_enabled = await manager_enabled.get_cached(key, fetch_func=fetch_func)
        
        # 缓存禁用
        manager_disabled = CacheManager(redis_client=None, enabled=False)
        result_disabled = await manager_disabled.get_cached(key, fetch_func=fetch_func)
        
        # 验证透明性
        assert result_enabled == result_disabled == value
        assert result_enabled["name"] == "测试用户"

    @pytest.mark.asyncio
    async def test_multiple_operations_degradation(self):
        """
        测试：多次操作降级透明性

        验证多次调用缓存操作时的降级透明性。

        **Validates: Requirements 2.2**
        """
        mock_redis = create_mock_redis()
        key = "test:multiple"
        value = {"count": 0}
        
        # 使用计数器验证 fetch_func 被调用的次数
        call_count_enabled = 0
        call_count_disabled = 0
        
        def fetch_func_enabled():
            nonlocal call_count_enabled
            call_count_enabled += 1
            return value
        
        def fetch_func_disabled():
            nonlocal call_count_disabled
            call_count_disabled += 1
            return value
        
        # 缓存启用：第一次调用 fetch_func，后续走缓存
        manager_enabled = CacheManager(redis_client=mock_redis, enabled=True)
        result1 = await manager_enabled.get_cached(key, fetch_func=fetch_func_enabled)
        result2 = await manager_enabled.get_cached(key, fetch_func=fetch_func_enabled)
        result3 = await manager_enabled.get_cached(key, fetch_func=fetch_func_enabled)
        
        assert call_count_enabled == 1, "缓存启用时只应该调用一次 fetch_func"
        assert result1 == result2 == result3 == value
        
        # 缓存禁用：每次都调用 fetch_func
        manager_disabled = CacheManager(redis_client=None, enabled=False)
        result4 = await manager_disabled.get_cached(key, fetch_func=fetch_func_disabled)
        result5 = await manager_disabled.get_cached(key, fetch_func=fetch_func_disabled)
        result6 = await manager_disabled.get_cached(key, fetch_func=fetch_func_disabled)
        
        assert call_count_disabled == 3, "缓存禁用时每次都应该调用 fetch_func"
        assert result4 == result5 == result6 == value
        
        # 验证透明性：返回值一致
        assert result1 == result4 == value

    @pytest.mark.asyncio
    async def test_is_enabled_method(self):
        """
        测试：is_enabled() 方法正确性

        验证 is_enabled() 方法在不同场景下返回正确的值。

        **Validates: Requirements 2.2**
        """
        # 场景 1：缓存启用且有 Redis 客户端
        mock_redis = create_mock_redis()
        manager1 = CacheManager(redis_client=mock_redis, enabled=True)
        assert manager1.is_enabled() is True
        
        # 场景 2：缓存禁用
        manager2 = CacheManager(redis_client=mock_redis, enabled=False)
        assert manager2.is_enabled() is False
        
        # 场景 3：没有 Redis 客户端
        manager3 = CacheManager(redis_client=None, enabled=True)
        assert manager3.is_enabled() is False
        
        # 场景 4：缓存禁用且没有 Redis 客户端
        manager4 = CacheManager(redis_client=None, enabled=False)
        assert manager4.is_enabled() is False
