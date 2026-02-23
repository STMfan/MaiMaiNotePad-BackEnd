"""
缓存序列化属性测试

测试缓存管理器的序列化和反序列化功能。

**Validates: Requirements 1.2 - 数据序列化**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json

from app.core.cache.manager import CacheManager


# ============================================================================
# 测试数据模型
# ============================================================================

class SimpleModel(BaseModel):
    """简单的测试模型"""
    id: str
    name: str
    value: int


class NestedModel(BaseModel):
    """嵌套的测试模型"""
    id: str
    data: Dict[str, Any]
    items: List[str]
    optional_field: Optional[str] = None


# ============================================================================
# Hypothesis 策略定义
# ============================================================================

# 基础数据类型策略
basic_json_values = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-1000000, max_value=1000000),
    st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
    st.text(min_size=0, max_size=100),
)

# 递归 JSON 策略（字典和列表）
json_dicts = st.recursive(
    basic_json_values,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(
            st.text(min_size=1, max_size=20),
            children,
            max_size=5
        )
    ),
    max_leaves=10
)

# 简单字典策略
simple_dicts = st.dictionaries(
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
simple_models = st.builds(
    SimpleModel,
    id=st.text(min_size=1, max_size=20),
    name=st.text(min_size=1, max_size=50),
    value=st.integers(min_value=0, max_value=1000)
)

nested_models = st.builds(
    NestedModel,
    id=st.text(min_size=1, max_size=20),
    data=st.dictionaries(
        st.text(min_size=1, max_size=10),
        st.text(max_size=20),
        max_size=3
    ),
    items=st.lists(st.text(max_size=20), max_size=5),
    optional_field=st.one_of(st.none(), st.text(max_size=20))
)


# ============================================================================
# 属性测试类
# ============================================================================

class TestSerializationIdempotence:
    """
    测试属性 5: 序列化幂等性

    **Property 5: Serialization Idempotence**
    数据的序列化和反序列化必须是幂等的，不改变数据内容。

    数学表示:
    ∀v: deserialize(serialize(v)) ≡ v

    **Validates: Requirements 1.2 - 数据序列化**
    """

    @given(data=simple_dicts)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_dict_serialization_idempotence(self, data):
        """
        属性测试：字典序列化幂等性

        验证任意字典数据经过序列化和反序列化后保持不变。

        **Validates: Requirements 1.2**
        """
        # 序列化
        serialized = json.dumps(data, ensure_ascii=False)
        
        # 反序列化
        deserialized = json.loads(serialized)
        
        # 验证幂等性
        assert deserialized == data, (
            f"序列化后反序列化的数据应该与原始数据相同\n"
            f"原始数据: {data}\n"
            f"反序列化后: {deserialized}"
        )

    @given(model=simple_models)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_pydantic_model_serialization_idempotence(self, model):
        """
        属性测试：Pydantic 模型序列化幂等性

        验证 Pydantic 模型经过序列化和反序列化后保持不变。

        **Validates: Requirements 1.2**
        """
        # 序列化为 JSON 字符串
        serialized = model.model_dump_json()
        
        # 反序列化回 Pydantic 模型
        deserialized = SimpleModel.model_validate_json(serialized)
        
        # 验证幂等性
        assert deserialized == model, (
            f"序列化后反序列化的模型应该与原始模型相同\n"
            f"原始模型: {model}\n"
            f"反序列化后: {deserialized}"
        )
        
        # 验证各个字段
        assert deserialized.id == model.id
        assert deserialized.name == model.name
        assert deserialized.value == model.value

    @given(model=nested_models)
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_nested_model_serialization_idempotence(self, model):
        """
        属性测试：嵌套模型序列化幂等性

        验证包含嵌套结构的 Pydantic 模型序列化幂等性。

        **Validates: Requirements 1.2**
        """
        # 序列化
        serialized = model.model_dump_json()
        
        # 反序列化
        deserialized = NestedModel.model_validate_json(serialized)
        
        # 验证幂等性
        assert deserialized == model, (
            f"嵌套模型序列化后应该保持不变\n"
            f"原始: {model}\n"
            f"反序列化: {deserialized}"
        )
        
        # 验证嵌套字段
        assert deserialized.id == model.id
        assert deserialized.data == model.data
        assert deserialized.items == model.items
        assert deserialized.optional_field == model.optional_field

    @given(data=json_dicts)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_complex_json_serialization_idempotence(self, data):
        """
        属性测试：复杂 JSON 结构序列化幂等性

        验证包含嵌套列表和字典的复杂 JSON 结构的序列化幂等性。

        **Validates: Requirements 1.2**
        """
        # 序列化
        serialized = json.dumps(data, ensure_ascii=False)
        
        # 反序列化
        deserialized = json.loads(serialized)
        
        # 验证幂等性
        assert deserialized == data, (
            f"复杂 JSON 结构序列化后应该保持不变\n"
            f"原始: {data}\n"
            f"反序列化: {deserialized}"
        )


class TestCacheManagerSerialization:
    """
    测试 CacheManager 的序列化功能

    验证 CacheManager 在实际缓存操作中的序列化幂等性。

    **Validates: Requirements 1.2**
    """

    @given(data=simple_dicts)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_cache_manager_dict_round_trip(self, data):
        """
        属性测试：CacheManager 字典往返序列化

        验证通过 CacheManager 缓存的字典数据保持不变。

        **Validates: Requirements 1.2**
        """
        from unittest.mock import AsyncMock
        
        # 创建模拟的 Redis 客户端
        mock_redis = AsyncMock()
        
        # 模拟 Redis 的 set 和 get 操作
        stored_value = None
        
        async def mock_set(key, value, ttl=None):
            nonlocal stored_value
            stored_value = value
            return True
        
        async def mock_get(key):
            return stored_value
        
        mock_redis.set = mock_set
        mock_redis.get = mock_get
        
        # 创建 CacheManager
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        # 设置缓存
        await manager.set_cached("test:key", data)
        
        # 获取缓存
        retrieved = await manager.get_cached("test:key")
        
        # 验证幂等性
        assert retrieved == data, (
            f"通过 CacheManager 缓存的数据应该保持不变\n"
            f"原始: {data}\n"
            f"获取: {retrieved}"
        )

    @given(model=simple_models)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_cache_manager_model_round_trip(self, model):
        """
        属性测试：CacheManager Pydantic 模型往返序列化

        验证通过 CacheManager 缓存的 Pydantic 模型保持不变。

        **Validates: Requirements 1.2**
        """
        from unittest.mock import AsyncMock
        
        # 创建模拟的 Redis 客户端
        mock_redis = AsyncMock()
        
        stored_value = None
        
        async def mock_set(key, value, ttl=None):
            nonlocal stored_value
            stored_value = value
            return True
        
        async def mock_get(key):
            return stored_value
        
        mock_redis.set = mock_set
        mock_redis.get = mock_get
        
        # 创建 CacheManager
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        # 设置缓存（Pydantic 模型）
        await manager.set_cached("test:model", model)
        
        # 获取缓存（指定模型类型）
        retrieved = await manager.get_cached("test:model", model=SimpleModel)
        
        # 验证幂等性
        assert retrieved == model, (
            f"通过 CacheManager 缓存的模型应该保持不变\n"
            f"原始: {model}\n"
            f"获取: {retrieved}"
        )
        
        # 验证字段
        assert retrieved.id == model.id
        assert retrieved.name == model.name
        assert retrieved.value == model.value

    @given(model=nested_models)
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_cache_manager_nested_model_round_trip(self, model):
        """
        属性测试：CacheManager 嵌套模型往返序列化

        验证通过 CacheManager 缓存的嵌套 Pydantic 模型保持不变。

        **Validates: Requirements 1.2**
        """
        from unittest.mock import AsyncMock
        
        # 创建模拟的 Redis 客户端
        mock_redis = AsyncMock()
        
        stored_value = None
        
        async def mock_set(key, value, ttl=None):
            nonlocal stored_value
            stored_value = value
            return True
        
        async def mock_get(key):
            return stored_value
        
        mock_redis.set = mock_set
        mock_redis.get = mock_get
        
        # 创建 CacheManager
        manager = CacheManager(redis_client=mock_redis, enabled=True)
        
        # 设置缓存
        await manager.set_cached("test:nested", model)
        
        # 获取缓存
        retrieved = await manager.get_cached("test:nested", model=NestedModel)
        
        # 验证幂等性
        assert retrieved == model, (
            f"嵌套模型通过缓存后应该保持不变\n"
            f"原始: {model}\n"
            f"获取: {retrieved}"
        )
        
        # 验证嵌套字段
        assert retrieved.id == model.id
        assert retrieved.data == model.data
        assert retrieved.items == model.items
        assert retrieved.optional_field == model.optional_field


class TestSerializationEdgeCases:
    """
    测试序列化的边界情况

    **Validates: Requirements 1.2**
    """

    @pytest.mark.asyncio
    async def test_empty_dict_serialization(self):
        """
        测试：空字典序列化

        **Validates: Requirements 1.2**
        """
        data = {}
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized == data

    @pytest.mark.asyncio
    async def test_empty_list_serialization(self):
        """
        测试：空列表序列化

        **Validates: Requirements 1.2**
        """
        data = []
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized == data

    @pytest.mark.asyncio
    async def test_unicode_serialization(self):
        """
        测试：Unicode 字符串序列化

        验证中文等 Unicode 字符正确序列化。

        **Validates: Requirements 1.2**
        """
        data = {
            "name": "测试用户",
            "description": "这是一个测试描述，包含中文字符",
            "emoji": "😀🎉"
        }
        
        serialized = json.dumps(data, ensure_ascii=False)
        deserialized = json.loads(serialized)
        
        assert deserialized == data
        assert deserialized["name"] == "测试用户"
        assert deserialized["description"] == "这是一个测试描述，包含中文字符"
        assert deserialized["emoji"] == "😀🎉"

    @pytest.mark.asyncio
    async def test_special_characters_serialization(self):
        """
        测试：特殊字符序列化

        **Validates: Requirements 1.2**
        """
        data = {
            "quotes": 'He said "Hello"',
            "newline": "Line1\nLine2",
            "tab": "Col1\tCol2",
            "backslash": "C:\\Users\\test"
        }
        
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        
        assert deserialized == data

    @pytest.mark.asyncio
    async def test_none_value_serialization(self):
        """
        测试：None 值序列化

        **Validates: Requirements 1.2**
        """
        data = {"key": None}
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized == data
        assert deserialized["key"] is None
