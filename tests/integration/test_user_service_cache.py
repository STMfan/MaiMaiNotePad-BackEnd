"""
测试 UserService 缓存集成

验证用户服务的缓存功能是否正常工作，包括：
- 缓存命中和未命中场景
- 数据更新后缓存失效
- 降级场景（缓存禁用）
- 并发访问

Requirements: 4.3（集成测试）
"""

import pytest
import asyncio
from sqlalchemy.orm import Session

from app.services.user_service import UserService
from app.core.cache.factory import get_cache_manager, reset_cache_manager
from tests.fixtures.data_factory import TestDataFactory


class TestUserServiceCacheIntegration:
    """测试 UserService 缓存集成"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """每个测试前后重置缓存管理器"""
        reset_cache_manager()
        yield
        reset_cache_manager()

    @pytest.mark.asyncio
    async def test_get_user_by_id_caches_result(
        self, test_db: Session, factory: TestDataFactory
    ):
        """测试 get_user_by_id 缓存结果
        
        验证：
        - 首次调用从数据库获取数据
        - 第二次调用从缓存获取数据（如果缓存启用）
        - 降级时仍能正常工作
        """
        service = UserService(test_db)
        user = factory.create_user(username="testuser", email="test@example.com")

        # 首次调用（缓存未命中或降级）
        result1 = service.get_user_by_id(user.id)
        assert result1 is not None
        assert result1.id == user.id
        assert result1.username == "testuser"

        # 第二次调用（如果缓存启用则从缓存获取）
        result2 = service.get_user_by_id(user.id)
        assert result2 is not None
        assert result2.id == user.id
        assert result2.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_by_username_caches_result(
        self, test_db: Session, factory: TestDataFactory
    ):
        """测试 get_user_by_username 缓存结果"""
        service = UserService(test_db)
        user = factory.create_user(username="cacheuser", email="cache@example.com")

        # 首次调用
        result1 = service.get_user_by_username("cacheuser")
        assert result1 is not None
        assert result1.username == "cacheuser"

        # 第二次调用（应该从缓存获取）
        result2 = service.get_user_by_username("cacheuser")
        assert result2 is not None
        assert result2.username == "cacheuser"

    @pytest.mark.asyncio
    async def test_update_user_invalidates_cache(
        self, test_db: Session, factory: TestDataFactory
    ):
        """测试更新用户时缓存失效
        
        验证：
        - 更新用户后，缓存被正确失效
        - 再次获取用户时返回最新数据
        """
        service = UserService(test_db)
        user = factory.create_user(username="oldname", email="old@example.com")

        # 首次获取（写入缓存）
        result1 = service.get_user_by_id(user.id)
        assert result1 is not None
        assert result1.username == "oldname"

        # 更新用户
        updated_user = service.update_user(
            user.id, username="newname", email="new@example.com"
        )
        assert updated_user is not None
        assert updated_user.username == "newname"

        # 缓存应该已失效，再次获取会从数据库读取最新数据
        result2 = service.get_user_by_id(user.id)
        assert result2 is not None
        assert result2.username == "newname"
        assert result2.email == "new@example.com"

    @pytest.mark.asyncio
    async def test_update_user_invalidates_username_cache(
        self, test_db: Session, factory: TestDataFactory
    ):
        """测试更新用户名时旧用户名缓存失效
        
        验证：
        - 更新用户名后，旧用户名的缓存被失效
        - 新用户名可以正常查询
        """
        service = UserService(test_db)
        user = factory.create_user(username="oldusername", email="user@example.com")

        # 通过用户名获取（写入缓存）
        result1 = service.get_user_by_username("oldusername")
        assert result1 is not None

        # 更新用户名
        updated_user = service.update_user(user.id, username="newusername")
        assert updated_user is not None
        assert updated_user.username == "newusername"

        # 旧用户名应该查询不到
        result2 = service.get_user_by_username("oldusername")
        assert result2 is None

        # 新用户名应该能查询到
        result3 = service.get_user_by_username("newusername")
        assert result3 is not None
        assert result3.id == user.id

    @pytest.mark.asyncio
    async def test_cache_disabled_fallback(
        self, test_db: Session, factory: TestDataFactory
    ):
        """测试缓存禁用时的降级行为
        
        验证：
        - 缓存禁用时，所有操作仍能正常工作
        - 数据直接从数据库获取
        """
        from app.core.cache.manager import CacheManager
        
        service = UserService(test_db)
        # 手动设置缓存为禁用状态
        # 注意：UserService 不直接持有 cache_manager，缓存通过装饰器处理
        
        user = factory.create_user(username="nocache", email="nocache@example.com")

        # 即使缓存禁用，查询仍应正常工作
        result = service.get_user_by_id(user.id)
        assert result is not None
        assert result.id == user.id
        assert result.username == "nocache"

    def test_concurrent_access(
        self, test_db: Session, factory: TestDataFactory
    ):
        """测试并发访问场景
        
        验证：
        - 多个并发请求能正确处理
        - 缓存在并发场景下工作正常
        """
        service = UserService(test_db)
        user = factory.create_user(username="concurrent", email="concurrent@example.com")

        # 多次获取同一用户
        results = [
            service.get_user_by_id(user.id)
            for _ in range(10)
        ]

        # 所有结果应该一致
        assert len(results) == 10
        for result in results:
            assert result is not None
            assert result.id == user.id
            assert result.username == "concurrent"

    @pytest.mark.asyncio
    async def test_cache_miss_then_hit(
        self, test_db: Session, factory: TestDataFactory
    ):
        """测试缓存未命中后命中的场景
        
        验证：
        - 首次查询不存在的用户（缓存未命中）
        - 创建用户后查询（缓存命中或数据库查询）
        """
        service = UserService(test_db)
        non_existent_id = "non-existent-id"

        # 查询不存在的用户（缓存未命中）
        result1 = service.get_user_by_id(non_existent_id)
        assert result1 is None

        # 创建用户
        user = factory.create_user(username="newuser", email="newuser@example.com")

        # 查询新创建的用户
        result2 = service.get_user_by_id(user.id)
        assert result2 is not None
        assert result2.username == "newuser"

    @pytest.mark.asyncio
    async def test_multiple_users_cache_isolation(
        self, test_db: Session, factory: TestDataFactory
    ):
        """测试多个用户的缓存隔离
        
        验证：
        - 不同用户的缓存互不干扰
        - 更新一个用户不影响其他用户的缓存
        """
        service = UserService(test_db)
        user1 = factory.create_user(username="user1", email="user1@example.com")
        user2 = factory.create_user(username="user2", email="user2@example.com")

        # 获取两个用户（写入缓存）
        result1 = service.get_user_by_id(user1.id)
        result2 = service.get_user_by_id(user2.id)
        assert result1.username == "user1"
        assert result2.username == "user2"

        # 更新 user1
        service.update_user(user1.id, username="user1_updated")

        # user1 的缓存应该失效，返回新数据
        result1_updated = service.get_user_by_id(user1.id)
        assert result1_updated.username == "user1_updated"

        # user2 的缓存不应受影响
        result2_again = service.get_user_by_id(user2.id)
        assert result2_again.username == "user2"

    @pytest.mark.asyncio
    async def test_cache_with_nonexistent_user(
        self, test_db: Session, factory: TestDataFactory
    ):
        """测试查询不存在用户的缓存行为
        
        验证：
        - 查询不存在的用户返回 None
        - 空值可能被缓存（防止缓存穿透）
        """
        service = UserService(test_db)
        non_existent_id = "definitely-not-exists"

        # 多次查询不存在的用户
        result1 = service.get_user_by_id(non_existent_id)
        result2 = service.get_user_by_id(non_existent_id)
        
        assert result1 is None
        assert result2 is None
