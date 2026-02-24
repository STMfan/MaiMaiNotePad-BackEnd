"""
缓存装饰器单元测试

测试 @cached 和 @cache_invalidate 装饰器的功能。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cache.decorators import _build_cache_key, cache_invalidate, cached
from app.core.cache.manager import CacheManager


class TestCachedDecorator:
    """测试 @cached 装饰器"""

    @pytest.mark.asyncio
    async def test_cached_basic_functionality(self, mock_cache_manager):
        """测试基本缓存功能"""
        # 模拟缓存未命中，然后缓存命中
        mock_cache_manager.get_cached.side_effect = [None, {"id": "123", "name": "Alice"}]
        mock_cache_manager.set_cached.return_value = True

        @cached(key_pattern="user:{user_id}", ttl=3600)
        async def get_user(user_id: str):
            return {"id": user_id, "name": "Alice"}

        # 第一次调用 - 缓存未命中
        result1 = await get_user("123")
        assert result1 == {"id": "123", "name": "Alice"}
        mock_cache_manager.get_cached.assert_called_once()
        mock_cache_manager.set_cached.assert_called_once()

        # 第二次调用 - 缓存命中
        result2 = await get_user("123")
        assert result2 == {"id": "123", "name": "Alice"}
        assert mock_cache_manager.get_cached.call_count == 2

    @pytest.mark.asyncio
    async def test_cached_with_cache_disabled(self, mock_cache_manager_disabled):
        """测试缓存禁用时的降级行为"""
        call_count = 0

        @cached(key_pattern="user:{user_id}", ttl=3600)
        async def get_user(user_id: str):
            nonlocal call_count
            call_count += 1
            return {"id": user_id, "name": "Alice"}

        # 缓存禁用，每次都执行原函数
        result1 = await get_user("123")
        assert result1 == {"id": "123", "name": "Alice"}
        assert call_count == 1

        result2 = await get_user("123")
        assert result2 == {"id": "123", "name": "Alice"}
        assert call_count == 2  # 函数被调用了两次

        # 验证没有调用 Redis 操作
        mock_cache_manager_disabled.get_cached.assert_not_called()
        mock_cache_manager_disabled.set_cached.assert_not_called()

    @pytest.mark.asyncio
    async def test_cached_with_custom_key_builder(self, mock_cache_manager):
        """测试自定义键构建函数"""
        mock_cache_manager.get_cached.return_value = None
        mock_cache_manager.set_cached.return_value = True

        def custom_key_builder(*args, **kwargs):
            user_id = kwargs.get("user_id") or args[0]
            return f"custom:user:{user_id}"

        @cached(key_pattern="user:{user_id}", key_builder=custom_key_builder, ttl=3600)
        async def get_user(user_id: str):
            return {"id": user_id, "name": "Alice"}

        result = await get_user("123")
        assert result == {"id": "123", "name": "Alice"}

        # 验证使用了自定义键
        mock_cache_manager.get_cached.assert_called_once_with("custom:user:123")
        mock_cache_manager.set_cached.assert_called_once_with("custom:user:123", {"id": "123", "name": "Alice"}, 3600)

    @pytest.mark.asyncio
    async def test_cached_with_positional_args(self, mock_cache_manager):
        """测试位置参数的键生成"""
        mock_cache_manager.get_cached.return_value = None
        mock_cache_manager.set_cached.return_value = True

        @cached(key_pattern="user:{user_id}", ttl=3600)
        async def get_user(user_id: str):
            return {"id": user_id, "name": "Alice"}

        # 使用位置参数调用
        result = await get_user("123")
        assert result == {"id": "123", "name": "Alice"}

        # 验证键构建正确
        mock_cache_manager.get_cached.assert_called_once_with("user:123")

    @pytest.mark.asyncio
    async def test_cached_with_keyword_args(self, mock_cache_manager):
        """测试关键字参数的键生成"""
        mock_cache_manager.get_cached.return_value = None
        mock_cache_manager.set_cached.return_value = True

        @cached(key_pattern="user:{user_id}", ttl=3600)
        async def get_user(user_id: str):
            return {"id": user_id, "name": "Alice"}

        # 使用关键字参数调用
        result = await get_user(user_id="123")
        assert result == {"id": "123", "name": "Alice"}

        # 验证键构建正确
        mock_cache_manager.get_cached.assert_called_once_with("user:123")

    @pytest.mark.asyncio
    async def test_cached_with_multiple_params(self, mock_cache_manager):
        """测试多参数的键生成"""
        mock_cache_manager.get_cached.return_value = None
        mock_cache_manager.set_cached.return_value = True

        @cached(key_pattern="kb:list:user:{user_id}:page:{page}", ttl=300)
        async def get_knowledge_list(user_id: str, page: int):
            return [{"id": "kb1"}, {"id": "kb2"}]

        result = await get_knowledge_list("user123", 1)
        assert len(result) == 2

        # 验证键构建正确
        mock_cache_manager.get_cached.assert_called_once_with("kb:list:user:user123:page:1")

    @pytest.mark.asyncio
    async def test_cached_redis_read_failure(self, mock_cache_manager):
        """测试 Redis 读取失败时的降级"""
        # 模拟 Redis 读取失败
        mock_cache_manager.get_cached.side_effect = Exception("Redis connection failed")
        mock_cache_manager.set_cached.return_value = True

        call_count = 0

        @cached(key_pattern="user:{user_id}", ttl=3600)
        async def get_user(user_id: str):
            nonlocal call_count
            call_count += 1
            return {"id": user_id, "name": "Alice"}

        # Redis 失败，应该降级到原函数
        result = await get_user("123")
        assert result == {"id": "123", "name": "Alice"}
        assert call_count == 1

        # 验证尝试了缓存读取
        mock_cache_manager.get_cached.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_redis_write_failure(self, mock_cache_manager):
        """测试 Redis 写入失败不影响返回结果"""
        mock_cache_manager.get_cached.return_value = None
        # 模拟 Redis 写入失败
        mock_cache_manager.set_cached.side_effect = Exception("Redis write failed")

        @cached(key_pattern="user:{user_id}", ttl=3600)
        async def get_user(user_id: str):
            return {"id": user_id, "name": "Alice"}

        # 写入失败不应影响返回结果
        result = await get_user("123")
        assert result == {"id": "123", "name": "Alice"}

        # 验证尝试了缓存写入
        mock_cache_manager.set_cached.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_key_builder_failure(self, mock_cache_manager):
        """测试键构建失败时的降级"""

        def failing_key_builder(*args, **kwargs):
            raise ValueError("Key builder failed")

        call_count = 0

        @cached(key_pattern="user:{user_id}", key_builder=failing_key_builder, ttl=3600)
        async def get_user(user_id: str):
            nonlocal call_count
            call_count += 1
            return {"id": user_id, "name": "Alice"}

        # 键构建失败，应该降级到原函数
        result = await get_user("123")
        assert result == {"id": "123", "name": "Alice"}
        assert call_count == 1

        # 验证没有调用 Redis 操作
        mock_cache_manager.get_cached.assert_not_called()

    def test_cached_sync_function_warning(self, mock_cache_manager):
        """测试同步函数的警告"""

        @cached(key_pattern="user:{user_id}", ttl=3600)
        def sync_get_user(user_id: str):
            return {"id": user_id, "name": "Alice"}

        # 同步函数应该直接执行，不使用缓存
        result = sync_get_user("123")
        assert result == {"id": "123", "name": "Alice"}

        # 验证没有调用 Redis 操作
        mock_cache_manager.get_cached.assert_not_called()


class TestCacheInvalidateDecorator:
    """测试 @cache_invalidate 装饰器"""

    @pytest.mark.asyncio
    async def test_cache_invalidate_basic(self, mock_cache_manager):
        """测试基本缓存失效功能"""
        mock_cache_manager.invalidate.return_value = True

        @cache_invalidate(key_pattern="user:{user_id}")
        async def update_user(user_id: str, data: dict):
            return {"id": user_id, **data}

        result = await update_user("123", {"name": "Bob"})
        assert result == {"id": "123", "name": "Bob"}

        # 验证缓存失效被调用
        mock_cache_manager.invalidate.assert_called_once_with("user:123")

    @pytest.mark.asyncio
    async def test_cache_invalidate_with_cache_disabled(self, mock_cache_manager_disabled):
        """测试缓存禁用时跳过失效操作"""

        @cache_invalidate(key_pattern="user:{user_id}")
        async def update_user(user_id: str, data: dict):
            return {"id": user_id, **data}

        result = await update_user("123", {"name": "Bob"})
        assert result == {"id": "123", "name": "Bob"}

        # 验证没有调用失效操作
        mock_cache_manager_disabled.invalidate.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_invalidate_with_custom_key_builder(self, mock_cache_manager):
        """测试自定义键构建函数"""
        mock_cache_manager.invalidate.return_value = True

        def custom_key_builder(*args, **kwargs):
            user_id = kwargs.get("user_id") or args[0]
            return f"custom:user:{user_id}"

        @cache_invalidate(key_pattern="user:{user_id}", key_builder=custom_key_builder)
        async def update_user(user_id: str, data: dict):
            return {"id": user_id, **data}

        result = await update_user("123", {"name": "Bob"})
        assert result == {"id": "123", "name": "Bob"}

        # 验证使用了自定义键
        mock_cache_manager.invalidate.assert_called_once_with("custom:user:123")

    @pytest.mark.asyncio
    async def test_cache_invalidate_failure_does_not_affect_result(self, mock_cache_manager):
        """测试缓存失效失败不影响函数返回"""
        # 模拟失效操作失败
        mock_cache_manager.invalidate.side_effect = Exception("Redis invalidate failed")

        @cache_invalidate(key_pattern="user:{user_id}")
        async def update_user(user_id: str, data: dict):
            return {"id": user_id, **data}

        # 失效失败不应影响返回结果
        result = await update_user("123", {"name": "Bob"})
        assert result == {"id": "123", "name": "Bob"}

        # 验证尝试了失效操作
        mock_cache_manager.invalidate.assert_called_once()

    def test_cache_invalidate_sync_function_warning(self, mock_cache_manager):
        """测试同步函数的警告"""

        @cache_invalidate(key_pattern="user:{user_id}")
        def sync_update_user(user_id: str, data: dict):
            return {"id": user_id, **data}

        # 同步函数应该直接执行，不使用缓存失效
        result = sync_update_user("123", {"name": "Bob"})
        assert result == {"id": "123", "name": "Bob"}

        # 验证没有调用失效操作
        mock_cache_manager.invalidate.assert_not_called()


class TestBuildCacheKey:
    """测试 _build_cache_key 辅助函数"""

    def test_build_key_with_single_param(self):
        """测试单参数键构建"""

        async def get_user(user_id: str):
            pass

        key = _build_cache_key("user:{user_id}", get_user, ("123",), {})
        assert key == "user:123"

    def test_build_key_with_keyword_args(self):
        """测试关键字参数键构建"""

        async def get_user(user_id: str):
            pass

        key = _build_cache_key("user:{user_id}", get_user, (), {"user_id": "123"})
        assert key == "user:123"

    def test_build_key_with_multiple_params(self):
        """测试多参数键构建"""

        async def get_knowledge_list(user_id: str, page: int):
            pass

        key = _build_cache_key("kb:list:user:{user_id}:page:{page}", get_knowledge_list, ("user123", 1), {})
        assert key == "kb:list:user:user123:page:1"

    def test_build_key_with_mixed_args(self):
        """测试混合参数键构建"""

        async def get_knowledge_list(user_id: str, page: int):
            pass

        key = _build_cache_key("kb:list:user:{user_id}:page:{page}", get_knowledge_list, ("user123",), {"page": 2})
        assert key == "kb:list:user:user123:page:2"

    def test_build_key_skips_self_parameter(self):
        """测试跳过 self 参数"""

        class UserService:
            async def get_user(self, user_id: str):
                pass

        service = UserService()
        # 在实际使用中，装饰器会接收到包含 self 的 args
        # 但 self 参数应该被跳过，不参与键构建
        key = _build_cache_key("user:{user_id}", service.get_user, (service, "123"), {})  # args 包含 self 和 user_id
        assert key == "user:123"

    def test_build_key_missing_parameter_raises_error(self):
        """测试缺少参数时抛出错误"""

        async def get_user(user_id: str):
            pass

        with pytest.raises(ValueError) as exc_info:
            _build_cache_key("user:{user_id}:{username}", get_user, ("123",), {})

        assert "username" in str(exc_info.value)
        assert "不存在" in str(exc_info.value)


# Fixtures


@pytest.fixture
def mock_cache_manager(monkeypatch):
    """模拟启用的缓存管理器"""
    mock_manager = MagicMock(spec=CacheManager)
    mock_manager.is_enabled.return_value = True
    mock_manager.get_cached = AsyncMock()
    mock_manager.set_cached = AsyncMock()
    mock_manager.invalidate = AsyncMock()

    # 模拟 get_cache_manager 返回 mock
    with patch("app.core.cache.factory.get_cache_manager", return_value=mock_manager):
        yield mock_manager


@pytest.fixture
def mock_cache_manager_disabled(monkeypatch):
    """模拟禁用的缓存管理器"""
    mock_manager = MagicMock(spec=CacheManager)
    mock_manager.is_enabled.return_value = False
    mock_manager.get_cached = AsyncMock()
    mock_manager.set_cached = AsyncMock()
    mock_manager.invalidate = AsyncMock()

    # 模拟 get_cache_manager 返回 mock
    with patch("app.core.cache.factory.get_cache_manager", return_value=mock_manager):
        yield mock_manager
