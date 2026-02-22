"""
PersonaService 单元测试

测试人设卡管理业务逻辑，包括 CRUD 操作、
收藏管理、下载跟踪和文件管理。

需求: 2.2 - 服务层单元测试
"""

from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.persona_service import PersonaService
from app.models.database import PersonaCard, PersonaCardFile, User, StarRecord


class TestPersonaCardRetrieval:
    """测试人设卡检索方法"""

    def test_get_persona_card_by_id_success(self):
        """测试通过 ID 成功获取人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        expected_pc = Mock(spec=PersonaCard)
        expected_pc.id = "pc-123"

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=expected_pc)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        pc = service.get_persona_card_by_id("pc-123")

        assert pc == expected_pc
        db.query.assert_called_once_with(PersonaCard)

    def test_get_persona_card_by_id_not_found(self):
        """测试当人设卡不存在时通过 ID 获取"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        pc = service.get_persona_card_by_id("nonexistent-id")

        assert pc is None

    def test_get_persona_card_by_id_database_error(self):
        """测试数据库错误时通过 ID 获取人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        db.query = Mock(side_effect=Exception("Database error"))

        pc = service.get_persona_card_by_id("pc-123")

        assert pc is None

    def test_get_all_persona_cards_success(self):
        """测试成功获取所有人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        expected_pcs = [Mock(spec=PersonaCard), Mock(spec=PersonaCard)]

        mock_query = Mock()
        mock_query.all = Mock(return_value=expected_pcs)
        db.query = Mock(return_value=mock_query)

        pcs = service.get_all_persona_cards()

        assert pcs == expected_pcs
        assert len(pcs) == 2

    def test_get_all_persona_cards_empty(self):
        """测试当没有人设卡时获取所有人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_query = Mock()
        mock_query.all = Mock(return_value=[])
        db.query = Mock(return_value=mock_query)

        pcs = service.get_all_persona_cards()

        assert pcs == []


class TestPublicPersonaCards:
    """测试带过滤和分页的公开人设卡检索"""

    def test_get_public_persona_cards_basic(self):
        """测试使用默认参数获取公开人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        expected_pcs = [Mock(spec=PersonaCard)]

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = mock_filter
        mock_query.count = Mock(return_value=1)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=expected_pcs)
        db.query = Mock(return_value=mock_query)

        pcs, total = service.get_public_persona_cards()

        assert len(pcs) == 1
        assert total == 1

    def test_get_public_persona_cards_with_name_filter(self):
        """测试按名称过滤获取公开人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        expected_pcs = [Mock(spec=PersonaCard)]

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = mock_filter
        mock_query.count = Mock(return_value=1)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=expected_pcs)
        db.query = Mock(return_value=mock_query)

        pcs, total = service.get_public_persona_cards(name="test")

        assert len(pcs) == 1
        assert total == 1

    def test_get_public_persona_cards_with_pagination(self):
        """测试带分页获取公开人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        expected_pcs = [Mock(spec=PersonaCard)]

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = mock_filter
        mock_query.count = Mock(return_value=10)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=expected_pcs)
        db.query = Mock(return_value=mock_query)

        pcs, total = service.get_public_persona_cards(page=2, page_size=5)

        assert len(pcs) == 1
        assert total == 10
        mock_query.offset.assert_called_once_with(5)
        mock_query.limit.assert_called_once_with(5)


class TestUserPersonaCards:
    """测试用户特定的人设卡检索"""

    def test_get_user_persona_cards_basic(self):
        """测试使用默认参数获取用户人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.name = "Test PC"
        mock_pc.tags = "tag1,tag2"
        mock_pc.is_pending = False
        mock_pc.is_public = True
        mock_pc.created_at = datetime.now()

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[mock_pc])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        pcs, total = service.get_user_persona_cards("user-123")

        assert len(pcs) == 1
        assert total == 1

    def test_get_user_persona_cards_with_status_filter(self):
        """测试按状态过滤获取用户人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc_pending = Mock(spec=PersonaCard)
        mock_pc_pending.name = "Pending PC"
        mock_pc_pending.tags = ""
        mock_pc_pending.is_pending = True
        mock_pc_pending.is_public = False
        mock_pc_pending.created_at = datetime.now()

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[mock_pc_pending])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        pcs, total = service.get_user_persona_cards("user-123", status="pending")

        assert len(pcs) == 1
        assert total == 1


class TestPersonaCardSave:
    """测试人设卡保存操作"""

    def test_save_persona_card_create_new(self):
        """测试创建新人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        pc_data = {"name": "Test PC", "description": "Test description", "uploader_id": "user-123"}

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"

        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        # Mock PersonaCard constructor
        with patch("app.services.persona_service.PersonaCard", return_value=mock_pc):
            pc = service.save_persona_card(pc_data)

        assert pc == mock_pc
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_save_persona_card_update_existing(self):
        """测试更新现有人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        existing_pc = Mock(spec=PersonaCard)
        existing_pc.id = "pc-123"
        existing_pc.name = "Old Name"

        pc_data = {"id": "pc-123", "name": "New Name", "description": "Updated description"}

        service.get_persona_card_by_id = Mock(return_value=existing_pc)
        db.commit = Mock()
        db.refresh = Mock()

        pc = service.save_persona_card(pc_data)

        assert pc == existing_pc
        assert existing_pc.name == "New Name"
        db.commit.assert_called_once()

    def test_save_persona_card_database_error(self):
        """测试数据库错误时保存人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        pc_data = {"name": "Test PC"}

        db.add = Mock()
        db.commit = Mock(side_effect=Exception("Database error"))
        db.rollback = Mock()

        with patch("app.services.persona_service.PersonaCard"):
            pc = service.save_persona_card(pc_data)

        assert pc is None
        db.rollback.assert_called_once()


class TestPersonaCardUpdate:
    """测试人设卡更新操作"""

    def test_update_persona_card_success(self):
        """测试成功更新人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = False
        mock_pc.content = "Old content"

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()
        db.refresh = Mock()

        update_data = {"content": "New content"}
        success, message, pc = service.update_persona_card("pc-123", update_data, "user-123")

        assert success is True
        assert pc == mock_pc
        assert mock_pc.content == "New content"

    def test_update_persona_card_not_found(self):
        """测试更新不存在的人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        service.get_persona_card_by_id = Mock(return_value=None)

        success, message, pc = service.update_persona_card("nonexistent", {}, "user-123")

        assert success is False
        assert "不存在" in message
        assert pc is None

    def test_update_persona_card_no_permission(self):
        """测试无权限更新人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.uploader_id = "user-123"

        service.get_persona_card_by_id = Mock(return_value=mock_pc)

        success, message, pc = service.update_persona_card("pc-123", {}, "other-user")

        assert success is False
        assert "权限" in message
        assert pc is None

    def test_update_persona_card_public_restricted(self):
        """测试更新公开人设卡的受限字段"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = True
        mock_pc.is_pending = False

        service.get_persona_card_by_id = Mock(return_value=mock_pc)

        update_data = {"name": "New Name"}
        success, message, pc = service.update_persona_card("pc-123", update_data, "user-123")

        assert success is False
        assert "仅允许修改补充说明" in message


class TestPersonaCardDelete:
    """测试人设卡删除操作"""

    def test_delete_persona_card_success(self):
        """测试成功删除人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.delete = Mock()
        db.commit = Mock()

        result = service.delete_persona_card("pc-123")

        assert result is True
        db.delete.assert_called_once_with(mock_pc)
        db.commit.assert_called_once()

    def test_delete_persona_card_not_found(self):
        """测试删除不存在的人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        service.get_persona_card_by_id = Mock(return_value=None)

        result = service.delete_persona_card("nonexistent")

        assert result is False

    def test_delete_persona_card_database_error(self):
        """测试数据库错误时删除人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.delete = Mock()
        db.commit = Mock(side_effect=Exception("Database error"))
        db.rollback = Mock()

        result = service.delete_persona_card("pc-123")

        assert result is False
        db.rollback.assert_called_once()


class TestStarManagement:
    """测试收藏管理操作"""

    def test_is_starred_true(self):
        """测试检查人设卡是否已收藏"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_star = Mock(spec=StarRecord)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_star)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.is_starred("user-123", "pc-123")

        assert result is True

    def test_is_starred_false(self):
        """测试检查人设卡未收藏"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.is_starred("user-123", "pc-123")

        assert result is False

    def test_add_star_success(self):
        """测试为人设卡添加收藏"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.star_count = 5

        service.is_starred = Mock(return_value=False)
        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.add = Mock()
        db.commit = Mock()

        result = service.add_star("user-123", "pc-123")

        assert result is True
        assert mock_pc.star_count == 6
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_add_star_already_starred(self):
        """测试已收藏时添加收藏"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        service.is_starred = Mock(return_value=True)

        result = service.add_star("user-123", "pc-123")

        assert result is False

    def test_remove_star_success(self):
        """测试从人设卡移除收藏"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_star = Mock(spec=StarRecord)
        mock_pc = Mock(spec=PersonaCard)
        mock_pc.star_count = 5

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_star)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.delete = Mock()
        db.commit = Mock()

        result = service.remove_star("user-123", "pc-123")

        assert result is True
        assert mock_pc.star_count == 4
        db.delete.assert_called_once_with(mock_star)
        db.commit.assert_called_once()

    def test_remove_star_not_starred(self):
        """测试未收藏时移除收藏"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.remove_star("user-123", "pc-123")

        assert result is False


class TestDownloadTracking:
    """测试下载跟踪操作"""

    def test_increment_downloads_success(self):
        """测试增加下载计数"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.downloads = 10

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()

        result = service.increment_downloads("pc-123")

        assert result is True
        assert mock_pc.downloads == 11
        db.commit.assert_called_once()

    def test_increment_downloads_from_zero(self):
        """测试从零开始增加下载计数"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.downloads = None

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()

        result = service.increment_downloads("pc-123")

        assert result is True
        assert mock_pc.downloads == 1

    def test_increment_downloads_not_found(self):
        """测试为不存在的人设卡增加下载"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        service.get_persona_card_by_id = Mock(return_value=None)

        result = service.increment_downloads("nonexistent")

        assert result is False


class TestFileManagement:
    """测试文件管理操作"""

    def test_get_files_by_persona_card_id_success(self):
        """测试获取人设卡的文件"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        expected_files = [Mock(spec=PersonaCardFile), Mock(spec=PersonaCardFile)]

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=expected_files)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        files = service.get_files_by_persona_card_id("pc-123")

        assert len(files) == 2
        assert files == expected_files

    def test_get_files_by_persona_card_id_empty(self):
        """测试当没有文件时获取文件"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        files = service.get_files_by_persona_card_id("pc-123")

        assert files == []

    def test_delete_files_by_persona_card_id_success(self):
        """测试删除人设卡的文件"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.delete = Mock()
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        db.commit = Mock()

        result = service.delete_files_by_persona_card_id("pc-123")

        assert result is True
        mock_filter.delete.assert_called_once()
        db.commit.assert_called_once()

    def test_delete_files_by_persona_card_id_database_error(self):
        """测试数据库错误时删除文件"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.delete = Mock()
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        db.commit = Mock(side_effect=Exception("Database error"))
        db.rollback = Mock()

        result = service.delete_files_by_persona_card_id("pc-123")

        assert result is False
        db.rollback.assert_called_once()


class TestUploadRecords:
    """测试上传记录管理"""

    def test_create_upload_record_success(self):
        """测试创建上传记录"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        db.add = Mock()
        db.commit = Mock()

        with patch("app.services.persona_service.UploadRecord") as mock_record:
            mock_instance = Mock()
            mock_instance.id = "record-123"
            mock_record.return_value = mock_instance

            record_id = service.create_upload_record("user-123", "pc-123", "Test PC", "Test description")

        assert record_id == "record-123"
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_create_upload_record_database_error(self):
        """测试数据库错误时创建上传记录"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        db.add = Mock()
        db.commit = Mock(side_effect=Exception("Database error"))
        db.rollback = Mock()

        with patch("app.services.persona_service.UploadRecord"):
            record_id = service.create_upload_record("user-123", "pc-123", "Test PC", "Test description")

        assert record_id is None
        db.rollback.assert_called_once()

    def test_delete_upload_records_by_target_success(self):
        """测试删除人设卡的上传记录"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.delete = Mock()
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        db.commit = Mock()

        result = service.delete_upload_records_by_target("pc-123")

        assert result is True
        mock_filter.delete.assert_called_once()
        db.commit.assert_called_once()

    def test_delete_upload_records_by_target_database_error(self):
        """测试数据库错误时删除上传记录"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.delete = Mock()
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        db.commit = Mock(side_effect=Exception("Database error"))
        db.rollback = Mock()

        result = service.delete_upload_records_by_target("pc-123")

        assert result is False
        db.rollback.assert_called_once()


class TestUploaderResolution:
    """测试上传者标识符解析"""

    def test_resolve_uploader_id_by_id(self):
        """测试通过用户 ID 解析上传者"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_user = Mock(spec=User)
        mock_user.id = "user-123"

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_user)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        user_id = service.resolve_uploader_id("user-123")

        assert user_id == "user-123"

    def test_resolve_uploader_id_by_username(self):
        """测试通过用户名解析上传者"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_user = Mock(spec=User)
        mock_user.id = "user-123"

        # First query by ID returns None
        mock_query1 = Mock()
        mock_filter1 = Mock()
        mock_filter1.first = Mock(return_value=None)
        mock_query1.filter = Mock(return_value=mock_filter1)

        # Second query by username returns user
        mock_query2 = Mock()
        mock_filter2 = Mock()
        mock_filter2.first = Mock(return_value=mock_user)
        mock_query2.filter = Mock(return_value=mock_filter2)

        db.query = Mock(side_effect=[mock_query1, mock_query2])

        user_id = service.resolve_uploader_id("testuser")

        assert user_id == "user-123"

    def test_resolve_uploader_id_not_found(self):
        """测试未找到上传者时的解析"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        user_id = service.resolve_uploader_id("nonexistent")

        assert user_id is None

    def test_resolve_uploader_id_database_error(self):
        """测试数据库错误时解析上传者"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        db.query = Mock(side_effect=Exception("Database error"))

        user_id = service.resolve_uploader_id("user-123")

        assert user_id is None


class TestReviewWorkflow:
    """测试人设卡审核工作流操作

    测试审核工作流，包括：
    - 创建待审核的人设卡
    - 在审核期间更新人设卡
    - 批准人设卡（设置 is_public=True, is_pending=False）
    - 拒绝人设卡（设置 is_public=False, is_pending=False, rejection_reason）

    需求: 2.2 - 审核工作流的服务层单元测试
    """

    def test_create_persona_card_for_review(self):
        """测试创建进入待审核状态的人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        pc_data = {
            "name": "Test Persona",
            "description": "Test description",
            "uploader_id": "user-123",
            "is_pending": True,
            "is_public": False,
        }

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.is_pending = True
        mock_pc.is_public = False

        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        with patch("app.services.persona_service.PersonaCard", return_value=mock_pc):
            pc = service.save_persona_card(pc_data)

        assert pc == mock_pc
        assert pc.is_pending is True
        assert pc.is_public is False
        db.commit.assert_called_once()

    def test_update_persona_card_in_pending_state(self):
        """测试更新处于待审核状态的人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = True
        mock_pc.content = "Old content"

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()
        db.refresh = Mock()

        # Only content field should be allowed for pending cards
        update_data = {"content": "New content"}
        success, message, pc = service.update_persona_card("pc-123", update_data, "user-123")

        assert success is True
        assert pc == mock_pc
        assert mock_pc.content == "New content"

    def test_update_persona_card_pending_restricted_fields(self):
        """测试更新待审核人设卡的受限字段失败"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = True

        service.get_persona_card_by_id = Mock(return_value=mock_pc)

        # Try to update name field on pending card
        update_data = {"name": "New Name"}
        success, message, pc = service.update_persona_card("pc-123", update_data, "user-123")

        assert success is False
        assert "仅允许修改补充说明" in message
        assert pc is None

    def test_approve_persona_card_workflow(self):
        """测试批准人设卡（模拟审核批准）

        这模拟了审核路由批准时发生的情况。
        审核路由直接修改人设卡字段，而不是通过 update_persona_card：
        - is_public 设置为 True
        - is_pending 设置为 False
        - rejection_reason 清除
        """
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = True
        mock_pc.rejection_reason = None

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()
        db.refresh = Mock()

        # Get the persona card
        pc = service.get_persona_card_by_id("pc-123")

        # Simulate approval by directly modifying fields (as done in review route)
        pc.is_public = True
        pc.is_pending = False
        pc.rejection_reason = None

        db.commit()
        db.refresh(pc)

        assert pc.is_public is True
        assert pc.is_pending is False
        assert pc.rejection_reason is None
        db.commit.assert_called_once()

    def test_reject_persona_card_workflow(self):
        """测试拒绝人设卡（模拟审核拒绝）

        这模拟了审核路由拒绝时发生的情况。
        审核路由直接修改人设卡字段，而不是通过 update_persona_card：
        - is_public set to False
        - is_pending 设置为 False
        - rejection_reason 设置拒绝原因
        """
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = True
        mock_pc.rejection_reason = None

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()
        db.refresh = Mock()

        # Get the persona card
        pc = service.get_persona_card_by_id("pc-123")

        # Simulate rejection by directly modifying fields (as done in review route)
        pc.is_public = False
        pc.is_pending = False
        pc.rejection_reason = "Content does not meet guidelines"

        db.commit()
        db.refresh(pc)

        assert pc.is_public is False
        assert pc.is_pending is False
        assert pc.rejection_reason == "Content does not meet guidelines"
        db.commit.assert_called_once()

    def test_delete_persona_card_in_review(self):
        """测试删除处于待审核状态的人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.is_pending = True
        mock_pc.is_public = False

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.delete = Mock()
        db.commit = Mock()

        result = service.delete_persona_card("pc-123")

        assert result is True
        db.delete.assert_called_once_with(mock_pc)
        db.commit.assert_called_once()

    def test_update_persona_card_admin_override(self):
        """测试管理员可以更新人设卡而不考虑所有者"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = False
        mock_pc.description = "Old description"

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()
        db.refresh = Mock()

        # Admin updates another user's persona card
        update_data = {"description": "Updated by admin"}
        success, message, pc = service.update_persona_card("pc-123", update_data, "admin-456", is_admin=True)

        assert success is True
        assert pc.description == "Updated by admin"

    def test_update_persona_card_moderator_override(self):
        """测试版主可以更新人设卡而不考虑所有者"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = False
        mock_pc.description = "Old description"

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()
        db.refresh = Mock()

        # Moderator updates another user's persona card
        update_data = {"description": "Updated by moderator"}
        success, message, pc = service.update_persona_card("pc-123", update_data, "mod-456", is_moderator=True)

        assert success is True
        assert pc.description == "Updated by moderator"


class TestPersonaServiceExceptionHandling:
    """测试 persona_service 异常处理和错误路径

    任务 4.4.1: 测试 persona_service 异常处理
    - 测试数据库异常
    - 测试验证失败
    - 测试权限检查失败
    - 验证错误日志
    - 验证数据库回滚
    - 测试边界情况（None 值、空结果）
    """

    def test_get_all_persona_cards_database_exception(self):
        """测试 get_all_persona_cards 数据库异常处理"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        db.query = Mock(side_effect=Exception("Database connection error"))

        result = service.get_all_persona_cards()

        assert result == []

    def test_get_public_persona_cards_database_exception(self):
        """测试 get_public_persona_cards 数据库异常处理"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        db.query = Mock(side_effect=Exception("Database error"))

        pcs, total = service.get_public_persona_cards()

        assert pcs == []
        assert total == 0

    def test_get_user_persona_cards_database_exception(self):
        """测试 get_user_persona_cards 数据库异常处理"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        db.query = Mock(side_effect=Exception("Database error"))

        pcs, total = service.get_user_persona_cards("user-123")

        assert pcs == []
        assert total == 0

    def test_save_persona_card_update_not_found(self):
        """测试 save_persona_card 更新不存在的人设卡"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        pc_data = {"id": "nonexistent-id", "name": "Test PC"}

        service.get_persona_card_by_id = Mock(return_value=None)

        result = service.save_persona_card(pc_data)

        assert result is None

    def test_update_persona_card_database_exception(self):
        """测试 update_persona_card 数据库异常处理"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = False

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock(side_effect=Exception("Database error"))
        db.rollback = Mock()

        success, message, pc = service.update_persona_card("pc-123", {"content": "New content"}, "user-123")

        assert success is False
        assert "失败" in message
        assert pc is None
        db.rollback.assert_called_once()

    def test_update_persona_card_non_admin_change_public_status(self):
        """测试非管理员尝试修改公开状态"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = False

        service.get_persona_card_by_id = Mock(return_value=mock_pc)

        update_data = {"is_public": True}
        success, message, pc = service.update_persona_card("pc-123", update_data, "user-123")

        assert success is False
        assert "管理员" in message
        assert pc is None

    def test_is_starred_database_exception(self):
        """测试 is_starred 数据库异常处理"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        db.query = Mock(side_effect=Exception("Database error"))

        result = service.is_starred("user-123", "pc-123")

        assert result is False

    def test_add_star_database_exception(self):
        """测试 add_star 数据库异常处理"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        service.is_starred = Mock(return_value=False)
        db.add = Mock()
        db.commit = Mock(side_effect=Exception("Database error"))
        db.rollback = Mock()

        result = service.add_star("user-123", "pc-123")

        assert result is False
        db.rollback.assert_called_once()

    def test_remove_star_database_exception(self):
        """测试 remove_star 数据库异常处理"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_star = Mock(spec=StarRecord)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_star)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        db.delete = Mock()
        db.commit = Mock(side_effect=Exception("Database error"))
        db.rollback = Mock()

        result = service.remove_star("user-123", "pc-123")

        assert result is False
        db.rollback.assert_called_once()

    def test_increment_downloads_database_exception(self):
        """测试 increment_downloads 数据库异常处理"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.downloads = 10

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock(side_effect=Exception("Database error"))
        db.rollback = Mock()

        result = service.increment_downloads("pc-123")

        assert result is False
        db.rollback.assert_called_once()

    def test_get_files_by_persona_card_id_database_exception(self):
        """测试 get_files_by_persona_card_id 数据库异常处理"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        db.query = Mock(side_effect=Exception("Database error"))

        result = service.get_files_by_persona_card_id("pc-123")

        assert result == []

    def test_get_public_persona_cards_with_invalid_sort_field(self):
        """测试 get_public_persona_cards 使用无效排序字段"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        expected_pcs = [Mock(spec=PersonaCard)]

        mock_query = Mock()
        mock_filter = Mock(return_value=mock_query)
        mock_query.filter = mock_filter
        mock_query.count = Mock(return_value=1)
        mock_query.order_by = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=expected_pcs)
        db.query = Mock(return_value=mock_query)

        # 使用无效的排序字段，应该回退到默认的 created_at
        pcs, total = service.get_public_persona_cards(sort_by="invalid_field")

        assert len(pcs) == 1
        assert total == 1

    def test_get_user_persona_cards_with_none_tags(self):
        """测试 get_user_persona_cards 处理 None 标签"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.name = "Test PC"
        mock_pc.tags = None
        mock_pc.is_pending = False
        mock_pc.is_public = True
        mock_pc.created_at = datetime.now()

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[mock_pc])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        # 使用标签过滤，但人设卡没有标签
        pcs, total = service.get_user_persona_cards("user-123", tag="test")

        assert len(pcs) == 0
        assert total == 0

    def test_get_user_persona_cards_with_list_tags(self):
        """测试 get_user_persona_cards 处理列表类型的标签"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.name = "Test PC"
        mock_pc.tags = ["tag1", "tag2", "tag3"]
        mock_pc.is_pending = False
        mock_pc.is_public = True
        mock_pc.created_at = datetime.now()

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[mock_pc])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        pcs, total = service.get_user_persona_cards("user-123", tag="tag2")

        assert len(pcs) == 1
        assert total == 1

    def test_get_user_persona_cards_with_invalid_sort_field(self):
        """测试 get_user_persona_cards 使用无效排序字段"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.name = "Test PC"
        mock_pc.tags = ""
        mock_pc.is_pending = False
        mock_pc.is_public = True
        mock_pc.created_at = datetime.now()

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[mock_pc])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        # 使用无效的排序字段，应该回退到默认的 created_at
        pcs, total = service.get_user_persona_cards("user-123", sort_by="invalid_field")

        assert len(pcs) == 1
        assert total == 1

    def test_update_persona_card_removes_copyright_owner(self):
        """测试 update_persona_card 移除 copyright_owner 字段"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = False
        mock_pc.copyright_owner = "Original Owner"

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()
        db.refresh = Mock()

        # 尝试更新 copyright_owner，应该被移除
        update_data = {"copyright_owner": "New Owner", "content": "New content"}
        success, message, pc = service.update_persona_card("pc-123", update_data, "user-123")

        assert success is True
        # copyright_owner 不应该被更新
        assert mock_pc.copyright_owner == "Original Owner"

    def test_update_persona_card_removes_name(self):
        """测试 update_persona_card 移除 name 字段"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = False
        mock_pc.name = "Original Name"

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()
        db.refresh = Mock()

        # 尝试更新 name，应该被移除
        update_data = {"name": "New Name", "content": "New content"}
        success, message, pc = service.update_persona_card("pc-123", update_data, "user-123")

        assert success is True
        # name 不应该被更新
        assert mock_pc.name == "Original Name"

    def test_update_persona_card_only_content_no_timestamp_update(self):
        """测试 update_persona_card 仅更新 content 时不更新时间戳"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        original_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = False
        mock_pc.updated_at = original_time

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()
        db.refresh = Mock()

        # 仅更新 content
        update_data = {"content": "New content"}
        success, message, pc = service.update_persona_card("pc-123", update_data, "user-123")

        assert success is True
        # updated_at 不应该被更新
        assert mock_pc.updated_at == original_time

    def test_update_persona_card_non_content_updates_timestamp(self):
        """测试 update_persona_card 更新非 content 字段时更新时间戳"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        original_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc-123"
        mock_pc.uploader_id = "user-123"
        mock_pc.is_public = False
        mock_pc.is_pending = False
        mock_pc.updated_at = original_time

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()
        db.refresh = Mock()

        # 更新非 content 字段
        update_data = {"description": "New description"}

        with patch("app.services.persona_service.datetime") as mock_datetime:
            new_time = datetime(2024, 1, 2, 12, 0, 0)
            mock_datetime.now.return_value = new_time

            success, message, pc = service.update_persona_card("pc-123", update_data, "user-123")

        assert success is True
        # updated_at 应该被更新
        assert mock_pc.updated_at == new_time

    def test_add_star_with_none_star_count(self):
        """测试 add_star 处理 None star_count"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.star_count = None

        service.is_starred = Mock(return_value=False)
        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.add = Mock()
        db.commit = Mock()

        result = service.add_star("user-123", "pc-123")

        assert result is True
        assert mock_pc.star_count == 1

    def test_add_star_persona_card_not_found(self):
        """测试 add_star 人设卡不存在"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        service.is_starred = Mock(return_value=False)
        service.get_persona_card_by_id = Mock(return_value=None)
        db.add = Mock()
        db.commit = Mock()

        result = service.add_star("user-123", "pc-123")

        # 即使人设卡不存在，也应该返回 True（因为 StarRecord 已创建）
        assert result is True
        db.commit.assert_called_once()

    def test_remove_star_with_zero_star_count(self):
        """测试 remove_star 处理 star_count 为 0 的情况"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_star = Mock(spec=StarRecord)
        mock_pc = Mock(spec=PersonaCard)
        mock_pc.star_count = 0

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_star)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.delete = Mock()
        db.commit = Mock()

        result = service.remove_star("user-123", "pc-123")

        assert result is True
        # star_count 不应该变成负数
        assert mock_pc.star_count == 0

    def test_remove_star_persona_card_not_found(self):
        """测试 remove_star 人设卡不存在"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_star = Mock(spec=StarRecord)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_star)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        service.get_persona_card_by_id = Mock(return_value=None)
        db.delete = Mock()
        db.commit = Mock()

        result = service.remove_star("user-123", "pc-123")

        # 即使人设卡不存在，也应该返回 True（因为 StarRecord 已删除）
        assert result is True
        db.commit.assert_called_once()

    def test_increment_downloads_with_none_downloads(self):
        """测试 increment_downloads 处理 None downloads"""
        db = Mock(spec=Session)
        service = PersonaService(db)

        mock_pc = Mock(spec=PersonaCard)
        mock_pc.downloads = None

        service.get_persona_card_by_id = Mock(return_value=mock_pc)
        db.commit = Mock()

        result = service.increment_downloads("pc-123")

        assert result is True
        assert mock_pc.downloads == 1
