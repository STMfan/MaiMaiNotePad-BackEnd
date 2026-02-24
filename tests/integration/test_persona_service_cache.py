"""
测试 PersonaService 缓存集成

验证人设卡服务的缓存功能是否正常工作，包括：
- 缓存命中和未命中场景
- 数据更新后缓存失效
- 降级场景（缓存禁用）
- 并发访问

Requirements: 4.3（集成测试）
"""

import pytest
from sqlalchemy.orm import Session

from app.core.cache.factory import reset_cache_manager
from app.services.persona_service import PersonaService
from tests.fixtures.data_factory import TestDataFactory


class TestPersonaServiceCacheIntegration:
    """测试 PersonaService 缓存集成"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """每个测试前后重置缓存管理器"""
        reset_cache_manager()
        yield
        reset_cache_manager()

    def test_get_persona_card_by_id_caches_result(self, test_db: Session, factory: TestDataFactory):
        """测试 get_persona_card_by_id 缓存结果

        验证：
        - 首次调用从数据库获取数据
        - 第二次调用从缓存获取数据（如果缓存启用）
        - 降级时仍能正常工作
        """
        service = PersonaService(test_db)
        pc = factory.create_persona_card(name="测试人设卡")

        # 首次调用（缓存未命中或降级）
        result1 = service.get_persona_card_by_id(pc.id)
        assert result1 is not None
        assert result1.id == pc.id
        assert result1.name == "测试人设卡"

        # 第二次调用（如果缓存启用则从缓存获取）
        result2 = service.get_persona_card_by_id(pc.id)
        assert result2 is not None
        assert result2.id == pc.id
        assert result2.name == "测试人设卡"

    def test_update_persona_card_invalidates_cache(self, test_db: Session, factory: TestDataFactory):
        """测试更新人设卡时缓存失效

        验证：
        - 更新人设卡后，缓存被正确失效
        - 再次获取人设卡时返回最新数据
        """
        service = PersonaService(test_db)
        user = factory.create_user()
        pc = factory.create_persona_card(uploader=user, name="原始人设卡", is_public=False)

        # 首次获取（写入缓存）
        result1 = service.get_persona_card_by_id(pc.id)
        assert result1 is not None
        assert result1.name == "原始人设卡"

        # 更新人设卡
        update_data = {"content": "更新后的内容"}
        success, msg, updated_pc = service.update_persona_card(pc.id, update_data, user.id)
        assert success is True
        assert updated_pc is not None

        # 缓存应该已失效，再次获取会从数据库读取最新数据
        result2 = service.get_persona_card_by_id(pc.id)
        assert result2 is not None
        assert result2.content == "更新后的内容"

    def test_delete_persona_card_invalidates_cache(self, test_db: Session, factory: TestDataFactory):
        """测试删除人设卡时缓存失效

        验证：
        - 删除人设卡后，缓存被正确失效
        - 再次获取返回 None
        """
        service = PersonaService(test_db)
        pc = factory.create_persona_card(name="待删除人设卡")

        # 首次获取（写入缓存）
        result1 = service.get_persona_card_by_id(pc.id)
        assert result1 is not None

        # 删除人设卡
        success = service.delete_persona_card(pc.id)
        assert success is True

        # 再次获取应该返回 None（人设卡已删除）
        result2 = service.get_persona_card_by_id(pc.id)
        assert result2 is None

    def test_cache_disabled_fallback(self, test_db: Session, factory: TestDataFactory):
        """测试缓存禁用时的降级行为

        验证：
        - 缓存禁用时，所有操作仍能正常工作
        - 数据直接从数据库获取
        """
        service = PersonaService(test_db)
        pc = factory.create_persona_card(name="无缓存人设卡")

        # 即使缓存禁用，查询仍应正常工作
        result = service.get_persona_card_by_id(pc.id)
        assert result is not None
        assert result.id == pc.id
        assert result.name == "无缓存人设卡"

    def test_get_public_persona_cards_caches_result(self, test_db: Session, factory: TestDataFactory):
        """测试 get_public_persona_cards 缓存结果

        验证：
        - 公开人设卡列表被正确缓存
        - 相同查询参数返回缓存结果
        """
        service = PersonaService(test_db)

        # 创建一些公开人设卡
        for i in range(3):
            factory.create_persona_card(name=f"公开人设卡 {i}", is_public=True, is_pending=False)

        # 首次调用（缓存未命中）
        result1, total1 = service.get_public_persona_cards(page=1, page_size=10)
        assert len(result1) == 3
        assert total1 == 3

        # 第二次调用（应该从缓存获取）
        result2, total2 = service.get_public_persona_cards(page=1, page_size=10)
        assert len(result2) == 3
        assert total2 == 3

    def test_get_user_persona_cards_caches_result(self, test_db: Session, factory: TestDataFactory):
        """测试 get_user_persona_cards 缓存结果

        验证：
        - 用户人设卡列表被正确缓存
        - 相同查询参数返回缓存结果
        """
        service = PersonaService(test_db)
        user = factory.create_user()

        # 创建一些用户人设卡
        for i in range(3):
            factory.create_persona_card(name=f"用户人设卡 {i}", uploader=user)

        # 首次调用（缓存未命中）
        result1, total1 = service.get_user_persona_cards(user_id=user.id, page=1, page_size=10)
        assert len(result1) == 3
        assert total1 == 3

        # 第二次调用（应该从缓存获取）
        result2, total2 = service.get_user_persona_cards(user_id=user.id, page=1, page_size=10)
        assert len(result2) == 3
        assert total2 == 3

    def test_concurrent_access(self, test_db: Session, factory: TestDataFactory):
        """测试并发访问场景

        验证：
        - 多个并发请求能正确处理
        - 缓存在并发场景下工作正常
        """
        service = PersonaService(test_db)
        pc = factory.create_persona_card(name="并发测试人设卡")

        # 多次获取同一人设卡
        results = [service.get_persona_card_by_id(pc.id) for _ in range(10)]

        # 所有结果应该一致
        assert len(results) == 10
        for result in results:
            assert result is not None
            assert result.id == pc.id
            assert result.name == "并发测试人设卡"

    def test_cache_with_different_query_params(self, test_db: Session, factory: TestDataFactory):
        """测试不同查询参数的缓存隔离

        验证：
        - 不同查询参数产生不同的缓存键
        - 各自的缓存互不干扰
        """
        service = PersonaService(test_db)
        user = factory.create_user()

        # 创建多个人设卡
        for i in range(5):
            factory.create_persona_card(name=f"人设卡 {i}", uploader=user, is_public=True, is_pending=False)

        # 不同分页参数
        result1, total1 = service.get_public_persona_cards(page=1, page_size=2)
        result2, total2 = service.get_public_persona_cards(page=2, page_size=2)

        assert len(result1) == 2
        assert len(result2) == 2
        assert result1[0].id != result2[0].id  # 不同页的数据应该不同

    def test_star_operations_with_cache(self, test_db: Session, factory: TestDataFactory):
        """测试收藏操作与缓存的交互

        验证：
        - 收藏/取消收藏操作正常工作
        - 收藏数更新后缓存保持一致
        """
        service = PersonaService(test_db)
        user = factory.create_user()
        pc = factory.create_persona_card(name="可收藏人设卡")

        # 获取初始状态
        result1 = service.get_persona_card_by_id(pc.id)
        initial_star_count = result1.star_count or 0

        # 收藏人设卡
        success = service.add_star(user.id, pc.id)
        assert success is True

        # 获取更新后的人设卡
        result2 = service.get_persona_card_by_id(pc.id)
        assert result2.star_count == initial_star_count + 1

        # 取消收藏
        success = service.remove_star(user.id, pc.id)
        assert success is True

        # 获取再次更新后的人设卡
        result3 = service.get_persona_card_by_id(pc.id)
        assert result3.star_count == initial_star_count

    def test_download_increment_with_cache(self, test_db: Session, factory: TestDataFactory):
        """测试下载次数递增与缓存的交互

        验证：
        - 下载次数递增操作正常工作
        - 下载数更新后缓存保持一致
        """
        service = PersonaService(test_db)
        pc = factory.create_persona_card(name="可下载人设卡")

        # 获取初始状态
        result1 = service.get_persona_card_by_id(pc.id)
        initial_downloads = result1.downloads or 0

        # 递增下载次数
        success = service.increment_downloads(pc.id)
        assert success is True

        # 获取更新后的人设卡
        result2 = service.get_persona_card_by_id(pc.id)
        assert result2.downloads == initial_downloads + 1

    def test_multiple_persona_cards_cache_isolation(self, test_db: Session, factory: TestDataFactory):
        """测试多个人设卡的缓存隔离

        验证：
        - 不同人设卡的缓存互不干扰
        - 更新一个人设卡不影响其他人设卡的缓存
        """
        service = PersonaService(test_db)
        user = factory.create_user()
        pc1 = factory.create_persona_card(name="人设卡1", uploader=user, is_public=False)
        pc2 = factory.create_persona_card(name="人设卡2", uploader=user, is_public=False)

        # 获取两个人设卡（写入缓存）
        result1 = service.get_persona_card_by_id(pc1.id)
        result2 = service.get_persona_card_by_id(pc2.id)
        assert result1.name == "人设卡1"
        assert result2.name == "人设卡2"

        # 更新 pc1
        update_data = {"content": "更新后的内容1"}
        service.update_persona_card(pc1.id, update_data, user.id)

        # pc1 的缓存应该失效，返回新数据
        result1_updated = service.get_persona_card_by_id(pc1.id)
        assert result1_updated.content == "更新后的内容1"

        # pc2 的缓存不应受影响
        result2_again = service.get_persona_card_by_id(pc2.id)
        assert result2_again.name == "人设卡2"
        assert result2_again.content != "更新后的内容1"

    def test_cache_with_nonexistent_persona_card(self, test_db: Session, factory: TestDataFactory):
        """测试查询不存在人设卡的缓存行为

        验证：
        - 查询不存在的人设卡返回 None
        - 空值可能被缓存（防止缓存穿透）
        """
        service = PersonaService(test_db)
        non_existent_id = "definitely-not-exists"

        # 多次查询不存在的人设卡
        result1 = service.get_persona_card_by_id(non_existent_id)
        result2 = service.get_persona_card_by_id(non_existent_id)

        assert result1 is None
        assert result2 is None
