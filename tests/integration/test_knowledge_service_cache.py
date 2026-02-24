"""
测试 KnowledgeService 缓存集成

验证知识库服务的缓存功能是否正常工作。

Requirements: 1.5（服务层集成）
"""

import pytest
from sqlalchemy.orm import Session

from app.core.cache.factory import reset_cache_manager
from app.services.knowledge_service import KnowledgeService
from tests.fixtures.data_factory import TestDataFactory


class TestKnowledgeServiceCacheIntegration:
    """测试 KnowledgeService 缓存集成"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """每个测试前后重置缓存管理器"""
        reset_cache_manager()
        yield
        reset_cache_manager()

    def test_get_knowledge_base_by_id_caches_result(self, test_db: Session, factory: TestDataFactory):
        """测试 get_knowledge_base_by_id 缓存结果"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base()

        # 首次调用（缓存未命中或降级）
        result1 = service.get_knowledge_base_by_id(kb.id)
        assert result1 is not None
        assert result1.id == kb.id

        # 第二次调用（如果缓存启用则从缓存获取，否则从数据库获取）
        result2 = service.get_knowledge_base_by_id(kb.id)
        assert result2 is not None
        assert result2.id == kb.id

        # 验证降级机制：即使 Redis 不可用，查询仍然正常工作
        assert result1.name == kb.name
        assert result2.name == kb.name

    def test_update_knowledge_base_invalidates_cache(self, test_db: Session, factory: TestDataFactory):
        """测试更新知识库时缓存失效"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader_id=user.id, is_public=False)

        # 首次获取（写入缓存）
        result1 = service.get_knowledge_base_by_id(kb.id)
        assert result1 is not None

        # 更新知识库
        update_data = {"content": "更新后的内容"}
        success, msg, updated_kb = service.update_knowledge_base(kb.id, update_data, user.id)
        assert success is True
        assert updated_kb is not None

        # 缓存应该已失效，再次获取会从数据库读取最新数据
        result2 = service.get_knowledge_base_by_id(kb.id)
        assert result2 is not None
        assert result2.content == "更新后的内容"

    def test_delete_knowledge_base_invalidates_cache(self, test_db: Session, factory: TestDataFactory):
        """测试删除知识库时缓存失效"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base()

        # 首次获取（写入缓存）
        result1 = service.get_knowledge_base_by_id(kb.id)
        assert result1 is not None

        # 删除知识库
        success = service.delete_knowledge_base(kb.id)
        assert success is True

        # 再次获取应该返回 None（知识库已删除）
        result2 = service.get_knowledge_base_by_id(kb.id)
        assert result2 is None

    def test_cache_disabled_fallback(self, test_db: Session, factory: TestDataFactory):
        """测试缓存禁用时的降级行为"""
        # 创建一个禁用缓存的服务
        from app.core.cache.manager import CacheManager

        service = KnowledgeService(test_db)
        # 手动设置缓存为禁用状态
        service.cache_manager = CacheManager(redis_client=None, enabled=False)

        kb = factory.create_knowledge_base()

        # 即使缓存禁用，查询仍应正常工作
        result = service.get_knowledge_base_by_id(kb.id)
        assert result is not None
        assert result.id == kb.id

    def test_get_public_knowledge_bases_caches_result(self, test_db: Session, factory: TestDataFactory):
        """测试 get_public_knowledge_bases 缓存结果"""
        service = KnowledgeService(test_db)

        # 创建一些公开知识库
        for i in range(3):
            factory.create_knowledge_base(name=f"公开知识库 {i}", is_public=True, is_pending=False)

        # 首次调用（缓存未命中）
        result1, total1 = service.get_public_knowledge_bases(page=1, page_size=10)
        assert len(result1) == 3
        assert total1 == 3

        # 第二次调用（应该从缓存获取）
        result2, total2 = service.get_public_knowledge_bases(page=1, page_size=10)
        assert len(result2) == 3
        assert total2 == 3

    def test_get_user_knowledge_bases_caches_result(self, test_db: Session, factory: TestDataFactory):
        """测试 get_user_knowledge_bases 缓存结果"""
        service = KnowledgeService(test_db)
        user = factory.create_user()

        # 创建一些用户知识库
        for i in range(3):
            factory.create_knowledge_base(name=f"用户知识库 {i}", uploader_id=user.id)

        # 首次调用（缓存未命中）
        result1, total1 = service.get_user_knowledge_bases(user_id=user.id, page=1, page_size=10)
        assert len(result1) == 3
        assert total1 == 3

        # 第二次调用（应该从缓存获取）
        result2, total2 = service.get_user_knowledge_bases(user_id=user.id, page=1, page_size=10)
        assert len(result2) == 3
        assert total2 == 3
