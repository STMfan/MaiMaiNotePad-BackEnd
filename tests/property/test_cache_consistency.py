"""
缓存一致性属性测试

测试缓存管理器的缓存一致性功能。

**Validates: Requirements 1.2 - 缓存读写**
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from pydantic import BaseModel

from app.core.cache.manager import CacheManager

# ============================================================================
# 测试数据模型
# ============================================================================


class CacheTestModel(BaseModel):
    """测试用的 Pydantic 模型（重命名避免 pytest 收集）"""

    id: str
    name: str
    value: int
    metadata: dict[str, Any] | None = None


# ============================================================================
# Hypothesis 策略定义
# ============================================================================

# 缓存键策略
cache_keys = st.text(
    min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=":_-")
)

# 简单值策略
simple_values = st.one_of(
    st.text(min_size=0, max_size=100), st.integers(min_value=-1000000, max_value=1000000), st.booleans(), st.none()
)

# 字典值策略
dict_values = st.dictionaries(
    st.text(min_size=1, max_size=20),
    st.one_of(
        st.text(max_size=50),
        st.integers(min_value=-1000, max_value=1000),
        st.booleans(),
    ),
    min_size=0,
    max_size=10,
)

# Pydantic 模型策略
test_models = st.builds(
    CacheTestModel,
    id=st.text(min_size=1, max_size=20),
    name=st.text(min_size=1, max_size=50),
    value=st.integers(min_value=0, max_value=10000),
    metadata=st.one_of(st.none(), st.dictionaries(st.text(min_size=1, max_size=10), st.text(max_size=20), max_size=3)),
)

# TTL 策略（1-10 秒）
ttl_values = st.integers(min_value=1, max_value=10)


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

    mock_redis.set = mock_set
    mock_redis.get = mock_get
    mock_redis.delete = mock_delete
    mock_redis.exists = mock_exists
    mock_redis._storage = storage
    mock_redis._ttl_storage = ttl_storage

    return mock_redis


# ============================================================================
# 属性测试类
# ============================================================================


class TestCacheConsistency:
    """
    测试属性 1: 缓存一致性

    **Property 1: Cache Consistency**
    对于任意缓存键 k 和数据 v，如果 set_cached(k, v) 成功执行，
    那么在 TTL 过期前，get_cached(k) 必须返回 v 或其等价表示。

    数学表示:
    ∀k, v, t: (set_cached(k, v, ttl=t) = True) ⟹
      (∀t' < t: get_cached(k) = v ∨ get_cached(k) ≡ v)

    **Validates: Requirements 1.2 - 缓存读写**
    """

    @given(key=cache_keys, value=dict_values)
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_dict_cache_consistency(self, key, value):
        """
        属性测试：字典缓存一致性

        验证字典数据在缓存后能够正确读取，保持一致性。

        **Validates: Requirements 1.2**
        """
        # 创建模拟 Redis 客户端
        mock_redis = create_mock_redis()

        # 创建 CacheManager
        manager = CacheManager(redis_client=mock_redis, enabled=True)

        # 设置缓存
        set_result = await manager.set_cached(key, value)
        assert set_result is True, "缓存设置应该成功"

        # 获取缓存
        cached_value = await manager.get_cached(key)

        # 验证一致性
        assert cached_value == value, (
            f"缓存读取的值应该与设置的值一致\n" f"设置的值: {value}\n" f"读取的值: {cached_value}"
        )

    @given(key=cache_keys, model=test_models)
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_model_cache_consistency(self, key, model):
        """
        属性测试：Pydantic 模型缓存一致性

        验证 Pydantic 模型在缓存后能够正确读取，保持一致性。

        **Validates: Requirements 1.2**
        """
        # 创建模拟 Redis 客户端
        mock_redis = create_mock_redis()

        # 创建 CacheManager
        manager = CacheManager(redis_client=mock_redis, enabled=True)

        # 设置缓存
        set_result = await manager.set_cached(key, model)
        assert set_result is True, "缓存设置应该成功"

        # 获取缓存（指定模型类型）
        cached_model = await manager.get_cached(key, model=CacheTestModel)

        # 验证一致性
        assert cached_model == model, (
            f"缓存读取的模型应该与设置的模型一致\n" f"设置的模型: {model}\n" f"读取的模型: {cached_model}"
        )

        # 验证各个字段
        assert cached_model.id == model.id
        assert cached_model.name == model.name
        assert cached_model.value == model.value
        assert cached_model.metadata == model.metadata

    @given(key=cache_keys, value=dict_values, ttl=ttl_values)
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_cache_consistency_with_ttl(self, key, value, ttl):
        """
        属性测试：带 TTL 的缓存一致性

        验证设置了 TTL 的缓存在过期前保持一致性。

        **Validates: Requirements 1.2**
        """
        # 创建模拟 Redis 客户端
        mock_redis = create_mock_redis()

        # 创建 CacheManager
        manager = CacheManager(redis_client=mock_redis, enabled=True)

        # 设置缓存（带 TTL）
        set_result = await manager.set_cached(key, value, ttl=ttl)
        assert set_result is True, "缓存设置应该成功"

        # 验证 TTL 被正确设置
        assert key in mock_redis._ttl_storage, "TTL 应该被记录"
        assert mock_redis._ttl_storage[key] == ttl, "TTL 值应该正确"

        # 在 TTL 过期前获取缓存
        cached_value = await manager.get_cached(key)

        # 验证一致性
        assert cached_value == value, (
            f"TTL 过期前，缓存值应该保持一致\n" f"设置的值: {value}\n" f"读取的值: {cached_value}\n" f"TTL: {ttl} 秒"
        )

    @given(key=cache_keys, value=dict_values)
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_multiple_reads_consistency(self, key, value):
        """
        属性测试：多次读取一致性

        验证同一个缓存键可以被多次读取，每次都返回相同的值。

        **Validates: Requirements 1.2**
        """
        # 创建模拟 Redis 客户端
        mock_redis = create_mock_redis()

        # 创建 CacheManager
        manager = CacheManager(redis_client=mock_redis, enabled=True)

        # 设置缓存
        await manager.set_cached(key, value)

        # 多次读取缓存
        read_count = 5
        for i in range(read_count):
            cached_value = await manager.get_cached(key)
            assert cached_value == value, (
                f"第 {i+1} 次读取的值应该与设置的值一致\n" f"设置的值: {value}\n" f"读取的值: {cached_value}"
            )

    @given(key=cache_keys, value1=dict_values, value2=dict_values)
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_cache_overwrite_consistency(self, key, value1, value2):
        """
        属性测试：缓存覆盖一致性

        验证缓存值被覆盖后，读取到的是最新的值。

        **Validates: Requirements 1.2**
        """
        # 确保两个值不同
        assume(value1 != value2)

        # 创建模拟 Redis 客户端
        mock_redis = create_mock_redis()

        # 创建 CacheManager
        manager = CacheManager(redis_client=mock_redis, enabled=True)

        # 设置第一个值
        await manager.set_cached(key, value1)
        cached_value1 = await manager.get_cached(key)
        assert cached_value1 == value1, "第一次设置的值应该正确"

        # 覆盖为第二个值
        await manager.set_cached(key, value2)
        cached_value2 = await manager.get_cached(key)

        # 验证读取到的是最新的值
        assert cached_value2 == value2, (
            f"覆盖后读取的值应该是最新的值\n"
            f"第一个值: {value1}\n"
            f"第二个值: {value2}\n"
            f"读取的值: {cached_value2}"
        )
        assert cached_value2 != value1, "覆盖后不应该读取到旧值"


class TestCacheConsistencyWithFetchFunc:
    """
    测试带 fetch_func 的缓存一致性

    验证使用 fetch_func 参数时的缓存一致性。

    **Validates: Requirements 1.2**
    """

    @given(key=cache_keys, value=dict_values)
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_fetch_func_cache_consistency(self, key, value):
        """
        属性测试：fetch_func 缓存一致性

        验证使用 fetch_func 获取数据后，缓存保持一致性。

        **Validates: Requirements 1.2**
        """
        # 创建模拟 Redis 客户端
        mock_redis = create_mock_redis()

        # 创建 CacheManager
        manager = CacheManager(redis_client=mock_redis, enabled=True)

        # 定义数据获取函数
        fetch_called = False

        def fetch_func():
            nonlocal fetch_called
            fetch_called = True
            return value

        # 第一次调用（缓存未命中，调用 fetch_func）
        result1 = await manager.get_cached(key, fetch_func=fetch_func)
        assert fetch_called is True, "缓存未命中时应该调用 fetch_func"
        assert result1 == value, "第一次获取的值应该正确"

        # 重置标志
        fetch_called = False

        # 第二次调用（缓存命中，不调用 fetch_func）
        result2 = await manager.get_cached(key, fetch_func=fetch_func)
        assert fetch_called is False, "缓存命中时不应该调用 fetch_func"
        assert result2 == value, "第二次获取的值应该与第一次一致"

        # 验证一致性
        assert result1 == result2, "多次获取的值应该保持一致"

    @given(key=cache_keys, value=dict_values)
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_async_fetch_func_cache_consistency(self, key, value):
        """
        属性测试：异步 fetch_func 缓存一致性

        验证使用异步 fetch_func 时的缓存一致性。

        **Validates: Requirements 1.2**
        """
        # 创建模拟 Redis 客户端
        mock_redis = create_mock_redis()

        # 创建 CacheManager
        manager = CacheManager(redis_client=mock_redis, enabled=True)

        # 定义异步数据获取函数
        fetch_called = False

        async def async_fetch_func():
            nonlocal fetch_called
            fetch_called = True
            await asyncio.sleep(0.01)  # 模拟异步操作
            return value

        # 第一次调用（缓存未命中）
        result1 = await manager.get_cached(key, fetch_func=async_fetch_func)
        assert fetch_called is True, "缓存未命中时应该调用 fetch_func"
        assert result1 == value, "第一次获取的值应该正确"

        # 重置标志
        fetch_called = False

        # 第二次调用（缓存命中）
        result2 = await manager.get_cached(key, fetch_func=async_fetch_func)
        assert fetch_called is False, "缓存命中时不应该调用 fetch_func"
        assert result2 == value, "第二次获取的值应该与第一次一致"


class TestCacheConsistencyEdgeCases:
    """
    测试缓存一致性的边界情况

    **Validates: Requirements 1.2**
    """

    @pytest.mark.asyncio
    async def test_empty_dict_consistency(self):
        """
        测试：空字典缓存一致性

        **Validates: Requirements 1.2**
        """
        mock_redis = create_mock_redis()
        manager = CacheManager(redis_client=mock_redis, enabled=True)

        key = "test:empty_dict"
        value = {}

        await manager.set_cached(key, value)
        cached_value = await manager.get_cached(key)

        assert cached_value == value
        assert isinstance(cached_value, dict)
        assert len(cached_value) == 0

    @pytest.mark.asyncio
    async def test_none_value_caching(self):
        """
        测试：None 值缓存（缓存穿透保护）

        验证 None 值被正确缓存为 NULL_PLACEHOLDER。

        **Validates: Requirements 1.2**
        """
        mock_redis = create_mock_redis()
        manager = CacheManager(redis_client=mock_redis, enabled=True)

        key = "test:none_value"

        # 使用 fetch_func 返回 None
        def fetch_none():
            return None

        # 第一次调用（缓存未命中，返回 None）
        result1 = await manager.get_cached(key, fetch_func=fetch_none)
        assert result1 is None, "应该返回 None"

        # 验证 None 被缓存为 NULL_PLACEHOLDER
        raw_value = await mock_redis.get(key)
        assert raw_value == "NULL_PLACEHOLDER", "None 应该被缓存为 NULL_PLACEHOLDER"

        # 第二次调用（缓存命中，返回 None）
        result2 = await manager.get_cached(key, fetch_func=fetch_none)
        assert result2 is None, "缓存的 None 值应该正确返回"

    @pytest.mark.asyncio
    async def test_unicode_value_consistency(self):
        """
        测试：Unicode 值缓存一致性

        验证包含中文等 Unicode 字符的数据缓存一致性。

        **Validates: Requirements 1.2**
        """
        mock_redis = create_mock_redis()
        manager = CacheManager(redis_client=mock_redis, enabled=True)

        key = "test:unicode"
        value = {"name": "测试用户", "description": "这是一个包含中文的描述", "emoji": "😀🎉🚀"}

        await manager.set_cached(key, value)
        cached_value = await manager.get_cached(key)

        assert cached_value == value
        assert cached_value["name"] == "测试用户"
        assert cached_value["description"] == "这是一个包含中文的描述"
        assert cached_value["emoji"] == "😀🎉🚀"

    @pytest.mark.asyncio
    async def test_large_value_consistency(self):
        """
        测试：大数据缓存一致性

        验证较大的数据对象缓存一致性。

        **Validates: Requirements 1.2**
        """
        mock_redis = create_mock_redis()
        manager = CacheManager(redis_client=mock_redis, enabled=True)

        key = "test:large_value"
        # 创建一个较大的字典
        value = {f"key_{i}": f"value_{i}" * 10 for i in range(100)}

        await manager.set_cached(key, value)
        cached_value = await manager.get_cached(key)

        assert cached_value == value
        assert len(cached_value) == 100

    @pytest.mark.asyncio
    async def test_nested_structure_consistency(self):
        """
        测试：嵌套结构缓存一致性

        验证包含嵌套列表和字典的复杂结构缓存一致性。

        **Validates: Requirements 1.2**
        """
        mock_redis = create_mock_redis()
        manager = CacheManager(redis_client=mock_redis, enabled=True)

        key = "test:nested"
        value = {
            "users": [
                {"id": "1", "name": "Alice", "tags": ["admin", "user"]},
                {"id": "2", "name": "Bob", "tags": ["user"]},
            ],
            "metadata": {"total": 2, "page": 1, "settings": {"sort": "name", "order": "asc"}},
        }

        await manager.set_cached(key, value)
        cached_value = await manager.get_cached(key)

        assert cached_value == value
        assert cached_value["users"][0]["name"] == "Alice"
        assert cached_value["metadata"]["settings"]["sort"] == "name"
