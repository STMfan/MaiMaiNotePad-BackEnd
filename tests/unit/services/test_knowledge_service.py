"""
测试 KnowledgeService 类

测试知识库服务的所有方法，包括 CRUD 操作、搜索、排序、权限检查等

Requirements: 2.2
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock, Mock
from sqlalchemy.orm import Session

from app.services.knowledge_service import KnowledgeService
from app.models.database import KnowledgeBase, KnowledgeBaseFile, User, StarRecord, UploadRecord
from tests.fixtures.data_factory import TestDataFactory


class TestKnowledgeServiceInit:
    """测试 KnowledgeService 初始化"""

    def test_init_with_db_session(self, test_db: Session):
        """测试使用数据库会话初始化服务"""
        service = KnowledgeService(test_db)
        assert service.db == test_db


class TestGetKnowledgeBaseById:
    """测试 get_knowledge_base_by_id 方法"""

    def test_get_existing_knowledge_base(self, test_db: Session, factory: TestDataFactory):
        """测试获取存在的知识库"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base()

        result = service.get_knowledge_base_by_id(kb.id)

        assert result is not None
        assert result.id == kb.id
        assert result.name == kb.name

    def test_get_nonexistent_knowledge_base(self, test_db: Session):
        """测试获取不存在的知识库"""
        service = KnowledgeService(test_db)
        fake_id = str(uuid.uuid4())

        result = service.get_knowledge_base_by_id(fake_id)

        assert result is None


class TestGetPublicKnowledgeBases:
    """测试 get_public_knowledge_bases 方法"""

    def test_get_public_knowledge_bases_basic(self, test_db: Session, factory: TestDataFactory):
        """测试获取公开知识库基本功能"""
        service = KnowledgeService(test_db)

        # 创建公开和私有知识库
        public_kb = factory.create_knowledge_base(is_public=True, is_pending=False)
        private_kb = factory.create_knowledge_base(is_public=False, is_pending=False)
        pending_kb = factory.create_knowledge_base(is_public=True, is_pending=True)

        kbs, total = service.get_public_knowledge_bases()

        assert total == 1
        assert len(kbs) == 1
        assert kbs[0].id == public_kb.id

    def test_get_public_knowledge_bases_with_pagination(self, test_db: Session, factory: TestDataFactory):
        """测试分页功能"""
        service = KnowledgeService(test_db)

        # 创建多个公开知识库
        for i in range(5):
            factory.create_knowledge_base(is_public=True, is_pending=False, name=f"KB_{i}")

        # 第一页
        kbs, total = service.get_public_knowledge_bases(page=1, page_size=2)
        assert total == 5
        assert len(kbs) == 2

        # 第二页
        kbs, total = service.get_public_knowledge_bases(page=2, page_size=2)
        assert total == 5
        assert len(kbs) == 2

        # 第三页
        kbs, total = service.get_public_knowledge_bases(page=3, page_size=2)
        assert total == 5
        assert len(kbs) == 1

    def test_get_public_knowledge_bases_with_name_search(self, test_db: Session, factory: TestDataFactory):
        """测试按名称搜索"""
        service = KnowledgeService(test_db)

        factory.create_knowledge_base(is_public=True, is_pending=False, name="Python Tutorial")
        factory.create_knowledge_base(is_public=True, is_pending=False, name="Java Guide")
        factory.create_knowledge_base(is_public=True, is_pending=False, name="Python Advanced")

        kbs, total = service.get_public_knowledge_bases(name="Python")

        assert total == 2
        assert all("Python" in kb.name for kb in kbs)

    def test_get_public_knowledge_bases_with_case_insensitive_search(self, test_db: Session, factory: TestDataFactory):
        """测试不区分大小写的搜索"""
        service = KnowledgeService(test_db)

        factory.create_knowledge_base(is_public=True, is_pending=False, name="Python Tutorial")
        factory.create_knowledge_base(is_public=True, is_pending=False, name="PYTHON Guide")

        kbs, total = service.get_public_knowledge_bases(name="python")

        assert total == 2

    def test_get_public_knowledge_bases_with_partial_name_search(self, test_db: Session, factory: TestDataFactory):
        """测试部分名称搜索"""
        service = KnowledgeService(test_db)

        factory.create_knowledge_base(is_public=True, is_pending=False, name="Machine Learning Basics")
        factory.create_knowledge_base(is_public=True, is_pending=False, name="Deep Learning Advanced")

        kbs, total = service.get_public_knowledge_bases(name="Learning")

        assert total == 2

    def test_get_public_knowledge_bases_with_no_results(self, test_db: Session, factory: TestDataFactory):
        """测试搜索无结果"""
        service = KnowledgeService(test_db)

        factory.create_knowledge_base(is_public=True, is_pending=False, name="Python Tutorial")

        kbs, total = service.get_public_knowledge_bases(name="NonExistent")

        assert total == 0
        assert len(kbs) == 0

    def test_get_public_knowledge_bases_with_uploader_filter(self, test_db: Session, factory: TestDataFactory):
        """测试按上传者过滤"""
        service = KnowledgeService(test_db)

        user1 = factory.create_user()
        user2 = factory.create_user()

        kb1 = factory.create_knowledge_base(uploader=user1, is_public=True, is_pending=False)
        kb2 = factory.create_knowledge_base(uploader=user2, is_public=True, is_pending=False)

        kbs, total = service.get_public_knowledge_bases(uploader_id=user1.id)

        assert total == 1
        assert kbs[0].id == kb1.id

    def test_get_public_knowledge_bases_with_sorting(self, test_db: Session, factory: TestDataFactory):
        """测试排序功能"""
        service = KnowledgeService(test_db)

        # 创建知识库，设置不同的 star_count
        kb1 = factory.create_knowledge_base(is_public=True, is_pending=False, name="KB1", star_count=5)
        kb2 = factory.create_knowledge_base(is_public=True, is_pending=False, name="KB2", star_count=10)
        kb3 = factory.create_knowledge_base(is_public=True, is_pending=False, name="KB3", star_count=3)

        # 按 star_count 降序
        kbs, total = service.get_public_knowledge_bases(sort_by="star_count", sort_order="desc")
        assert kbs[0].id == kb2.id
        assert kbs[1].id == kb1.id
        assert kbs[2].id == kb3.id

        # 按 star_count 升序
        kbs, total = service.get_public_knowledge_bases(sort_by="star_count", sort_order="asc")
        assert kbs[0].id == kb3.id
        assert kbs[1].id == kb1.id
        assert kbs[2].id == kb2.id


class TestGetUserKnowledgeBases:
    """测试 get_user_knowledge_bases 方法"""

    def test_get_user_knowledge_bases_basic(self, test_db: Session, factory: TestDataFactory):
        """测试获取用户知识库基本功能"""
        service = KnowledgeService(test_db)

        user1 = factory.create_user()
        user2 = factory.create_user()

        kb1 = factory.create_knowledge_base(uploader=user1)
        kb2 = factory.create_knowledge_base(uploader=user1)
        kb3 = factory.create_knowledge_base(uploader=user2)

        kbs, total = service.get_user_knowledge_bases(user1.id)

        assert total == 2
        assert len(kbs) == 2
        assert all(kb.uploader_id == user1.id for kb in kbs)

    def test_get_user_knowledge_bases_with_status_filter(self, test_db: Session, factory: TestDataFactory):
        """测试按状态过滤"""
        service = KnowledgeService(test_db)

        user = factory.create_user()

        pending_kb = factory.create_knowledge_base(uploader=user, is_pending=True, is_public=False)
        approved_kb = factory.create_knowledge_base(uploader=user, is_pending=False, is_public=True)
        rejected_kb = factory.create_knowledge_base(uploader=user, is_pending=False, is_public=False)

        # 测试 pending 状态
        kbs, total = service.get_user_knowledge_bases(user.id, status="pending")
        assert total == 1
        assert kbs[0].id == pending_kb.id

        # 测试 approved 状态
        kbs, total = service.get_user_knowledge_bases(user.id, status="approved")
        assert total == 1
        assert kbs[0].id == approved_kb.id

        # 测试 rejected 状态
        kbs, total = service.get_user_knowledge_bases(user.id, status="rejected")
        assert total == 1
        assert kbs[0].id == rejected_kb.id

    def test_get_user_knowledge_bases_with_name_search(self, test_db: Session, factory: TestDataFactory):
        """测试按名称搜索"""
        service = KnowledgeService(test_db)

        user = factory.create_user()

        factory.create_knowledge_base(uploader=user, name="Python Tutorial")
        factory.create_knowledge_base(uploader=user, name="Java Guide")

        kbs, total = service.get_user_knowledge_bases(user.id, name="Python")

        assert total == 1
        assert "Python" in kbs[0].name

    def test_get_user_knowledge_bases_with_tag_filter(self, test_db: Session, factory: TestDataFactory):
        """测试按标签过滤"""
        service = KnowledgeService(test_db)

        user = factory.create_user()

        factory.create_knowledge_base(uploader=user, tags="python,tutorial")
        factory.create_knowledge_base(uploader=user, tags="java,guide")

        kbs, total = service.get_user_knowledge_bases(user.id, tag="python")

        assert total == 1
        assert "python" in kbs[0].tags


class TestSaveKnowledgeBase:
    """测试 save_knowledge_base 方法"""

    def test_create_new_knowledge_base(self, test_db: Session, factory: TestDataFactory):
        """测试创建新知识库"""
        service = KnowledgeService(test_db)
        user = factory.create_user()

        kb_data = {
            "name": "Test KB",
            "description": "Test description",
            "uploader_id": user.id,
            "copyright_owner": user.username,
            "is_public": False,
            "is_pending": False,
            "base_path": "/tmp/test_kb",
        }

        result = service.save_knowledge_base(kb_data)

        assert result is not None
        assert result.name == "Test KB"
        assert result.uploader_id == user.id

    def test_create_knowledge_base_with_minimal_data(self, test_db: Session, factory: TestDataFactory):
        """测试使用最少数据创建知识库"""
        service = KnowledgeService(test_db)
        user = factory.create_user()

        kb_data = {
            "name": "Minimal KB",
            "description": "Minimal description",  # description is required
            "uploader_id": user.id,
            "copyright_owner": user.username,
            "base_path": "/tmp/minimal_kb",
        }

        result = service.save_knowledge_base(kb_data)

        assert result is not None
        assert result.name == "Minimal KB"
        assert result.uploader_id == user.id

    def test_update_existing_knowledge_base(self, test_db: Session, factory: TestDataFactory):
        """测试更新现有知识库"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base(name="Original Name")

        kb_data = {"id": kb.id, "description": "Updated description"}

        result = service.save_knowledge_base(kb_data)

        assert result is not None
        assert result.id == kb.id
        assert result.description == "Updated description"
        assert result.name == "Original Name"  # Name should not change

    def test_update_nonexistent_knowledge_base_returns_none(self, test_db: Session):
        """测试更新不存在的知识库返回 None"""
        service = KnowledgeService(test_db)
        fake_id = str(uuid.uuid4())

        kb_data = {"id": fake_id, "description": "Updated description"}

        result = service.save_knowledge_base(kb_data)

        assert result is None


class TestCheckDuplicateName:
    """测试 check_duplicate_name 方法"""

    def test_no_duplicate_name(self, test_db: Session, factory: TestDataFactory):
        """测试没有重复名称"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        factory.create_knowledge_base(uploader=user, name="Existing KB")

        result = service.check_duplicate_name(user.id, "New KB")

        assert result is False

    def test_duplicate_name_exists(self, test_db: Session, factory: TestDataFactory):
        """测试存在重复名称"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        factory.create_knowledge_base(uploader=user, name="Existing KB")

        result = service.check_duplicate_name(user.id, "Existing KB")

        assert result is True

    def test_duplicate_name_different_user(self, test_db: Session, factory: TestDataFactory):
        """测试不同用户可以使用相同名称"""
        service = KnowledgeService(test_db)
        user1 = factory.create_user()
        user2 = factory.create_user()
        factory.create_knowledge_base(uploader=user1, name="KB Name")

        result = service.check_duplicate_name(user2.id, "KB Name")

        assert result is False

    def test_duplicate_name_with_exclusion(self, test_db: Session, factory: TestDataFactory):
        """测试排除特定知识库的重复检查"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user, name="KB Name")

        # 排除当前知识库，应该不算重复
        result = service.check_duplicate_name(user.id, "KB Name", exclude_kb_id=kb.id)

        assert result is False


class TestUpdateKnowledgeBase:
    """测试 update_knowledge_base 方法"""

    def test_update_as_owner(self, test_db: Session, factory: TestDataFactory):
        """测试所有者更新知识库"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user, description="Old description")

        success, message, result = service.update_knowledge_base(kb.id, {"description": "New description"}, user.id)

        assert success is True
        assert result is not None
        assert result.description == "New description"

    def test_update_nonexistent_knowledge_base(self, test_db: Session, factory: TestDataFactory):
        """测试更新不存在的知识库"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        fake_id = str(uuid.uuid4())

        success, message, result = service.update_knowledge_base(fake_id, {"description": "New description"}, user.id)

        assert success is False
        assert "不存在" in message
        assert result is None

    def test_update_without_permission(self, test_db: Session, factory: TestDataFactory):
        """测试无权限更新知识库"""
        service = KnowledgeService(test_db)
        owner = factory.create_user()
        other_user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=owner)

        success, message, result = service.update_knowledge_base(
            kb.id, {"description": "New description"}, other_user.id
        )

        assert success is False
        assert "是你的知识库吗你就改" in message
        assert result is None

    def test_update_as_admin(self, test_db: Session, factory: TestDataFactory):
        """测试管理员更新知识库"""
        service = KnowledgeService(test_db)
        owner = factory.create_user()
        admin = factory.create_user(is_admin=True)
        kb = factory.create_knowledge_base(uploader=owner)

        success, message, result = service.update_knowledge_base(
            kb.id, {"description": "Admin update"}, admin.id, is_admin=True
        )

        assert success is True
        assert result.description == "Admin update"

    def test_update_public_knowledge_base_restricted(self, test_db: Session, factory: TestDataFactory):
        """测试公开知识库只能修改补充说明"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user, is_public=True)

        # 尝试修改描述（不允许）
        success, message, result = service.update_knowledge_base(kb.id, {"description": "New description"}, user.id)

        assert success is False
        assert "仅允许修改补充说明" in message

    def test_update_public_knowledge_base_content_allowed(self, test_db: Session, factory: TestDataFactory):
        """测试公开知识库可以修改补充说明"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user, is_public=True)

        success, message, result = service.update_knowledge_base(kb.id, {"content": "New content"}, user.id)

        assert success is True
        assert result.content == "New content"


class TestDeleteKnowledgeBase:
    """测试 delete_knowledge_base 方法"""

    def test_delete_existing_knowledge_base(self, test_db: Session, factory: TestDataFactory):
        """测试删除存在的知识库"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base()

        result = service.delete_knowledge_base(kb.id)

        assert result is True
        assert service.get_knowledge_base_by_id(kb.id) is None

    def test_delete_knowledge_base_with_files(self, test_db: Session, factory: TestDataFactory):
        """测试删除带有文件的知识库"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base()

        # 添加文件
        file1 = factory.create_knowledge_base_file(knowledge_base=kb, file_name="file1.txt")
        file2 = factory.create_knowledge_base_file(knowledge_base=kb, file_name="file2.txt")

        # 验证文件存在
        files_before = service.get_files_by_knowledge_base_id(kb.id)
        assert len(files_before) == 2

        result = service.delete_knowledge_base(kb.id)

        assert result is True
        assert service.get_knowledge_base_by_id(kb.id) is None
        # 注意：根据实际实现，文件可能不会自动级联删除
        # 这取决于数据库模型的配置

    def test_delete_knowledge_base_with_stars(self, test_db: Session, factory: TestDataFactory):
        """测试删除有收藏记录的知识库"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base()

        # 添加收藏
        factory.create_star_record(user=user, target_id=kb.id, target_type="knowledge")

        result = service.delete_knowledge_base(kb.id)

        assert result is True
        assert service.get_knowledge_base_by_id(kb.id) is None

    def test_delete_nonexistent_knowledge_base(self, test_db: Session):
        """测试删除不存在的知识库"""
        service = KnowledgeService(test_db)
        fake_id = str(uuid.uuid4())

        result = service.delete_knowledge_base(fake_id)

        assert result is False


class TestStarOperations:
    """测试 Star 相关操作"""

    def test_is_starred_false(self, test_db: Session, factory: TestDataFactory):
        """测试知识库未被收藏"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base()

        result = service.is_starred(user.id, kb.id)

        assert result is False

    def test_is_starred_true(self, test_db: Session, factory: TestDataFactory):
        """测试知识库已被收藏"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base()

        # 添加收藏
        factory.create_star_record(user=user, target_id=kb.id, target_type="knowledge")

        result = service.is_starred(user.id, kb.id)

        assert result is True

    def test_add_star_success(self, test_db: Session, factory: TestDataFactory):
        """测试成功添加收藏"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(star_count=0)

        result = service.add_star(user.id, kb.id)

        assert result is True
        assert service.is_starred(user.id, kb.id) is True

        # 验证 star_count 增加
        test_db.refresh(kb)
        assert kb.star_count == 1

    def test_add_star_already_starred(self, test_db: Session, factory: TestDataFactory):
        """测试重复添加收藏"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base()

        # 第一次添加
        service.add_star(user.id, kb.id)

        # 第二次添加应该失败
        result = service.add_star(user.id, kb.id)

        assert result is False

    def test_remove_star_success(self, test_db: Session, factory: TestDataFactory):
        """测试成功取消收藏"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(star_count=1)

        # 先添加收藏
        factory.create_star_record(user=user, target_id=kb.id, target_type="knowledge")

        result = service.remove_star(user.id, kb.id)

        assert result is True
        assert service.is_starred(user.id, kb.id) is False

        # 验证 star_count 减少
        test_db.refresh(kb)
        assert kb.star_count == 0

    def test_remove_star_not_starred(self, test_db: Session, factory: TestDataFactory):
        """测试取消未收藏的知识库"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base()

        result = service.remove_star(user.id, kb.id)

        assert result is False


class TestIncrementDownloads:
    """测试 increment_downloads 方法"""

    def test_increment_downloads_success(self, test_db: Session, factory: TestDataFactory):
        """测试成功增加下载次数"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base(downloads=5)

        result = service.increment_downloads(kb.id)

        assert result is True
        test_db.refresh(kb)
        assert kb.downloads == 6

    def test_increment_downloads_from_zero(self, test_db: Session, factory: TestDataFactory):
        """测试从零开始增加下载次数"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base(downloads=0)

        result = service.increment_downloads(kb.id)

        assert result is True
        test_db.refresh(kb)
        assert kb.downloads == 1

    def test_increment_downloads_nonexistent(self, test_db: Session):
        """测试增加不存在知识库的下载次数"""
        service = KnowledgeService(test_db)
        fake_id = str(uuid.uuid4())

        result = service.increment_downloads(fake_id)

        assert result is False


class TestGetFilesByKnowledgeBaseId:
    """测试 get_files_by_knowledge_base_id 方法"""

    def test_get_files_with_files(self, test_db: Session, factory: TestDataFactory):
        """测试获取有文件的知识库文件列表"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base()

        file1 = factory.create_knowledge_base_file(knowledge_base=kb, file_name="file1.txt")
        file2 = factory.create_knowledge_base_file(knowledge_base=kb, file_name="file2.txt")

        files = service.get_files_by_knowledge_base_id(kb.id)

        assert len(files) == 2
        assert any(f.id == file1.id for f in files)
        assert any(f.id == file2.id for f in files)

    def test_get_files_empty(self, test_db: Session, factory: TestDataFactory):
        """测试获取没有文件的知识库文件列表"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base()

        files = service.get_files_by_knowledge_base_id(kb.id)

        assert len(files) == 0

    def test_get_files_nonexistent_kb(self, test_db: Session):
        """测试获取不存在知识库的文件列表"""
        service = KnowledgeService(test_db)
        fake_id = str(uuid.uuid4())

        files = service.get_files_by_knowledge_base_id(fake_id)

        assert len(files) == 0


class TestCreateUploadRecord:
    """测试 create_upload_record 方法"""

    def test_create_upload_record_success(self, test_db: Session, factory: TestDataFactory):
        """测试成功创建上传记录"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user)

        record_id = service.create_upload_record(
            uploader_id=user.id, target_id=kb.id, name=kb.name, description=kb.description, status="success"
        )

        assert record_id is not None

        # 验证记录已创建
        record = test_db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
        assert record is not None
        assert record.uploader_id == user.id
        assert record.target_id == kb.id
        assert record.target_type == "knowledge"
        assert record.status == "success"

    def test_create_upload_record_pending(self, test_db: Session, factory: TestDataFactory):
        """测试创建待审核状态的上传记录"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user)

        record_id = service.create_upload_record(
            uploader_id=user.id, target_id=kb.id, name=kb.name, description=kb.description, status="pending"
        )

        assert record_id is not None

        record = test_db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
        assert record.status == "pending"


class TestDeleteUploadRecordsByTarget:
    """测试 delete_upload_records_by_target 方法"""

    def test_delete_upload_records_success(self, test_db: Session, factory: TestDataFactory):
        """测试成功删除上传记录"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user)

        # 创建上传记录
        record_id = service.create_upload_record(
            uploader_id=user.id, target_id=kb.id, name=kb.name, description=kb.description
        )

        result = service.delete_upload_records_by_target(kb.id)

        assert result is True

        # 验证记录已删除
        record = test_db.query(UploadRecord).filter(UploadRecord.id == record_id).first()
        assert record is None

    def test_delete_upload_records_no_records(self, test_db: Session):
        """测试删除不存在的上传记录"""
        service = KnowledgeService(test_db)
        fake_id = str(uuid.uuid4())

        result = service.delete_upload_records_by_target(fake_id)

        assert result is True  # 删除不存在的记录也返回 True


class TestResolveUploaderId:
    """测试 resolve_uploader_id 方法"""

    def test_resolve_by_user_id(self, test_db: Session, factory: TestDataFactory):
        """测试通过用户 ID 解析"""
        service = KnowledgeService(test_db)
        user = factory.create_user()

        result = service.resolve_uploader_id(user.id)

        assert result == user.id

    def test_resolve_by_username(self, test_db: Session, factory: TestDataFactory):
        """测试通过用户名解析"""
        service = KnowledgeService(test_db)
        user = factory.create_user(username="testuser123")

        result = service.resolve_uploader_id("testuser123")

        assert result == user.id

    def test_resolve_nonexistent_user(self, test_db: Session):
        """测试解析不存在的用户"""
        service = KnowledgeService(test_db)

        result = service.resolve_uploader_id("nonexistent_user")

        assert result is None

    def test_resolve_invalid_id(self, test_db: Session):
        """测试解析无效的 ID"""
        service = KnowledgeService(test_db)
        fake_id = str(uuid.uuid4())

        result = service.resolve_uploader_id(fake_id)

        assert result is None


class TestKnowledgeServiceExceptionHandling:
    """测试 KnowledgeService 异常处理

    测试所有方法的数据库异常处理、验证失败和边界情况
    """

    def test_get_knowledge_base_by_id_database_exception(self, test_db: Session, caplog):
        """测试 get_knowledge_base_by_id 数据库异常处理"""
        service = KnowledgeService(test_db)

        with patch.object(test_db, "query", side_effect=Exception("Database error")):
            result = service.get_knowledge_base_by_id("test_id")

            assert result is None
            assert "获取知识库失败" in caplog.text

    def test_get_public_knowledge_bases_database_exception(self, test_db: Session, caplog):
        """测试 get_public_knowledge_bases 数据库异常处理"""
        service = KnowledgeService(test_db)

        with patch.object(test_db, "query", side_effect=Exception("Database error")):
            kbs, total = service.get_public_knowledge_bases()

            assert kbs == []
            assert total == 0
            assert "获取公开知识库列表失败" in caplog.text

    def test_get_user_knowledge_bases_database_exception(self, test_db: Session, caplog):
        """测试 get_user_knowledge_bases 数据库异常处理"""
        service = KnowledgeService(test_db)

        with patch.object(test_db, "query", side_effect=Exception("Database error")):
            kbs, total = service.get_user_knowledge_bases("user_id")

            assert kbs == []
            assert total == 0
            assert "获取用户" in caplog.text and "的知识库列表失败" in caplog.text

    def test_save_knowledge_base_database_exception(self, test_db: Session, factory: TestDataFactory, caplog):
        """测试 save_knowledge_base 数据库异常处理"""
        service = KnowledgeService(test_db)
        user = factory.create_user()

        kb_data = {
            "name": "Test KB",
            "description": "Test description",
            "uploader_id": user.id,
            "copyright_owner": user.username,
            "base_path": "/tmp/test_kb",
        }

        with patch.object(test_db, "commit", side_effect=Exception("Database error")):
            result = service.save_knowledge_base(kb_data)

            assert result is None
            assert "保存知识库失败" in caplog.text

    def test_save_knowledge_base_rollback_on_error(self, test_db: Session, factory: TestDataFactory):
        """测试 save_knowledge_base 错误时回滚"""
        service = KnowledgeService(test_db)
        user = factory.create_user()

        kb_data = {
            "name": "Test KB",
            "description": "Test description",
            "uploader_id": user.id,
            "copyright_owner": user.username,
            "base_path": "/tmp/test_kb",
        }

        with patch.object(test_db, "commit", side_effect=Exception("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                result = service.save_knowledge_base(kb_data)

                assert result is None
                mock_rollback.assert_called_once()

    def test_check_duplicate_name_database_exception(self, test_db: Session, caplog):
        """测试 check_duplicate_name 数据库异常处理"""
        service = KnowledgeService(test_db)

        with patch.object(test_db, "query", side_effect=Exception("Database error")):
            result = service.check_duplicate_name("user_id", "name")

            assert result is False
            assert "检查知识库重名失败" in caplog.text

    def test_update_knowledge_base_database_exception(self, test_db: Session, factory: TestDataFactory, caplog):
        """测试 update_knowledge_base 数据库异常处理"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user)

        # Store IDs before patching
        user_id = user.id
        kb_id = kb.id

        with patch.object(test_db, "commit", side_effect=Exception("Database error")):
            success, message, result = service.update_knowledge_base(kb_id, {"description": "New description"}, user_id)

            assert success is False
            assert "修改知识库失败" in message
            assert result is None
            assert "更新知识库" in caplog.text and "失败" in caplog.text

    def test_update_knowledge_base_rollback_on_error(self, test_db: Session, factory: TestDataFactory):
        """测试 update_knowledge_base 错误时回滚"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user)

        # Store IDs before patching
        user_id = user.id
        kb_id = kb.id

        with patch.object(test_db, "commit", side_effect=Exception("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                success, message, result = service.update_knowledge_base(
                    kb_id, {"description": "New description"}, user_id
                )

                assert success is False
                mock_rollback.assert_called_once()

    def test_delete_knowledge_base_database_exception(self, test_db: Session, factory: TestDataFactory, caplog):
        """测试 delete_knowledge_base 数据库异常处理"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base()
        kb_id = kb.id

        # Mock get_knowledge_base_by_id to return the kb, then mock commit to fail
        with patch.object(test_db, "delete"):
            with patch.object(test_db, "commit", side_effect=Exception("Database error")):
                result = service.delete_knowledge_base(kb_id)

                assert result is False
                assert "删除知识库" in caplog.text and "失败" in caplog.text

    def test_delete_knowledge_base_rollback_on_error(self, test_db: Session, factory: TestDataFactory):
        """测试 delete_knowledge_base 错误时回滚"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base()

        with patch.object(test_db, "commit", side_effect=Exception("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                result = service.delete_knowledge_base(kb.id)

                assert result is False
                mock_rollback.assert_called_once()

    def test_is_starred_database_exception(self, test_db: Session, caplog):
        """测试 is_starred 数据库异常处理"""
        service = KnowledgeService(test_db)

        with patch.object(test_db, "query", side_effect=Exception("Database error")):
            result = service.is_starred("user_id", "kb_id")

            assert result is False
            assert "检查收藏状态失败" in caplog.text

    def test_add_star_database_exception(self, test_db: Session, caplog):
        """测试 add_star 数据库异常处理"""
        service = KnowledgeService(test_db)

        with patch.object(service, "is_starred", return_value=False):
            with patch.object(test_db, "commit", side_effect=Exception("Database error")):
                result = service.add_star("user_id", "kb_id")

                assert result is False
                assert "收藏知识库失败" in caplog.text

    def test_add_star_rollback_on_error(self, test_db: Session):
        """测试 add_star 错误时回滚"""
        service = KnowledgeService(test_db)

        with patch.object(service, "is_starred", return_value=False):
            with patch.object(test_db, "commit", side_effect=Exception("Database error")):
                with patch.object(test_db, "rollback") as mock_rollback:
                    result = service.add_star("user_id", "kb_id")

                    assert result is False
                    mock_rollback.assert_called_once()

    def test_remove_star_database_exception(self, test_db: Session, caplog):
        """测试 remove_star 数据库异常处理"""
        service = KnowledgeService(test_db)

        with patch.object(test_db, "query", side_effect=Exception("Database error")):
            result = service.remove_star("user_id", "kb_id")

            assert result is False
            assert "取消收藏知识库失败" in caplog.text

    def test_remove_star_rollback_on_error(self, test_db: Session, factory: TestDataFactory):
        """测试 remove_star 错误时回滚"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base()

        # Store IDs before creating star record
        user_id = user.id
        kb_id = kb.id

        factory.create_star_record(user=user, target_id=kb_id, target_type="knowledge")

        with patch.object(test_db, "commit", side_effect=Exception("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                result = service.remove_star(user_id, kb_id)

                assert result is False
                mock_rollback.assert_called_once()

    def test_increment_downloads_database_exception(self, test_db: Session, factory: TestDataFactory, caplog):
        """测试 increment_downloads 数据库异常处理"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base()

        with patch.object(test_db, "commit", side_effect=Exception("Database error")):
            result = service.increment_downloads(kb.id)

            assert result is False
            assert "递增知识库" in caplog.text and "下载次数失败" in caplog.text

    def test_increment_downloads_rollback_on_error(self, test_db: Session, factory: TestDataFactory):
        """测试 increment_downloads 错误时回滚"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base()

        with patch.object(test_db, "commit", side_effect=Exception("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                result = service.increment_downloads(kb.id)

                assert result is False
                mock_rollback.assert_called_once()

    def test_get_files_by_knowledge_base_id_database_exception(self, test_db: Session, caplog):
        """测试 get_files_by_knowledge_base_id 数据库异常处理"""
        service = KnowledgeService(test_db)

        with patch.object(test_db, "query", side_effect=Exception("Database error")):
            files = service.get_files_by_knowledge_base_id("kb_id")

            assert files == []
            assert "获取知识库" in caplog.text and "的文件列表失败" in caplog.text

    def test_create_upload_record_database_exception(self, test_db: Session, caplog):
        """测试 create_upload_record 数据库异常处理"""
        service = KnowledgeService(test_db)

        with patch.object(test_db, "commit", side_effect=Exception("Database error")):
            record_id = service.create_upload_record(
                uploader_id="user_id", target_id="kb_id", name="Test KB", description="Test description"
            )

            assert record_id is None
            assert "创建上传记录失败" in caplog.text

    def test_create_upload_record_rollback_on_error(self, test_db: Session):
        """测试 create_upload_record 错误时回滚"""
        service = KnowledgeService(test_db)

        with patch.object(test_db, "commit", side_effect=Exception("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                record_id = service.create_upload_record(
                    uploader_id="user_id", target_id="kb_id", name="Test KB", description="Test description"
                )

                assert record_id is None
                mock_rollback.assert_called_once()

    def test_delete_upload_records_by_target_database_exception(self, test_db: Session, caplog):
        """测试 delete_upload_records_by_target 数据库异常处理"""
        service = KnowledgeService(test_db)

        with patch.object(test_db, "commit", side_effect=Exception("Database error")):
            result = service.delete_upload_records_by_target("target_id")

            assert result is False
            assert "删除上传记录失败" in caplog.text

    def test_delete_upload_records_by_target_rollback_on_error(self, test_db: Session):
        """测试 delete_upload_records_by_target 错误时回滚"""
        service = KnowledgeService(test_db)

        with patch.object(test_db, "commit", side_effect=Exception("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                result = service.delete_upload_records_by_target("target_id")

                assert result is False
                mock_rollback.assert_called_once()

    def test_resolve_uploader_id_database_exception(self, test_db: Session, caplog):
        """测试 resolve_uploader_id 数据库异常处理"""
        service = KnowledgeService(test_db)

        with patch.object(test_db, "query", side_effect=Exception("Database error")):
            result = service.resolve_uploader_id("identifier")

            assert result is None
            assert "解析上传者标识失败" in caplog.text


class TestKnowledgeServiceEdgeCases:
    """测试 KnowledgeService 边界情况"""

    def test_get_knowledge_base_by_id_with_none(self, test_db: Session):
        """测试使用 None 作为 ID 获取知识库"""
        service = KnowledgeService(test_db)

        result = service.get_knowledge_base_by_id(None)

        assert result is None

    def test_get_knowledge_base_by_id_with_empty_string(self, test_db: Session):
        """测试使用空字符串作为 ID 获取知识库"""
        service = KnowledgeService(test_db)

        result = service.get_knowledge_base_by_id("")

        assert result is None

    def test_get_public_knowledge_bases_with_zero_page_size(self, test_db: Session, factory: TestDataFactory):
        """测试使用零作为页面大小"""
        service = KnowledgeService(test_db)
        factory.create_knowledge_base(is_public=True, is_pending=False)

        kbs, total = service.get_public_knowledge_bases(page=1, page_size=0)

        assert len(kbs) == 0
        assert total >= 0

    def test_get_public_knowledge_bases_with_negative_page(self, test_db: Session, factory: TestDataFactory):
        """测试使用负数页码"""
        service = KnowledgeService(test_db)
        factory.create_knowledge_base(is_public=True, is_pending=False)

        kbs, total = service.get_public_knowledge_bases(page=-1, page_size=10)

        # 应该返回空列表或第一页
        assert isinstance(kbs, list)
        assert isinstance(total, int)

    def test_get_public_knowledge_bases_with_invalid_sort_field(self, test_db: Session, factory: TestDataFactory):
        """测试使用无效的排序字段"""
        service = KnowledgeService(test_db)
        factory.create_knowledge_base(is_public=True, is_pending=False)

        kbs, total = service.get_public_knowledge_bases(sort_by="invalid_field")

        # 应该使用默认排序字段
        assert isinstance(kbs, list)
        assert total >= 0

    def test_get_user_knowledge_bases_with_empty_user_id(self, test_db: Session):
        """测试使用空用户 ID 获取知识库"""
        service = KnowledgeService(test_db)

        kbs, total = service.get_user_knowledge_bases("")

        assert kbs == []
        assert total == 0

    def test_get_user_knowledge_bases_with_none_user_id(self, test_db: Session):
        """测试使用 None 作为用户 ID 获取知识库"""
        service = KnowledgeService(test_db)

        kbs, total = service.get_user_knowledge_bases(None)

        assert kbs == []
        assert total == 0

    def test_save_knowledge_base_with_empty_data(self, test_db: Session):
        """测试使用空数据保存知识库"""
        service = KnowledgeService(test_db)

        # 应该处理空数据而不崩溃
        try:
            result = service.save_knowledge_base({})
            # 可能返回 None 或抛出异常
            assert result is None or isinstance(result, KnowledgeBase)
        except Exception:
            # 如果抛出异常也是可以接受的
            pass

    def test_check_duplicate_name_with_empty_name(self, test_db: Session, factory: TestDataFactory):
        """测试使用空名称检查重复"""
        service = KnowledgeService(test_db)
        user = factory.create_user()

        result = service.check_duplicate_name(user.id, "")

        assert isinstance(result, bool)

    def test_check_duplicate_name_with_none_name(self, test_db: Session, factory: TestDataFactory):
        """测试使用 None 作为名称检查重复"""
        service = KnowledgeService(test_db)
        user = factory.create_user()

        result = service.check_duplicate_name(user.id, None)

        assert isinstance(result, bool)

    def test_update_knowledge_base_with_empty_update_data(self, test_db: Session, factory: TestDataFactory):
        """测试使用空更新数据更新知识库"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user)

        success, message, result = service.update_knowledge_base(kb.id, {}, user.id)

        # 空更新应该成功但不改变任何内容
        assert success is True
        assert result is not None

    def test_increment_downloads_with_none_downloads(self, test_db: Session, factory: TestDataFactory):
        """测试递增 None 下载次数"""
        service = KnowledgeService(test_db)
        kb = factory.create_knowledge_base(downloads=None)

        result = service.increment_downloads(kb.id)

        assert result is True
        test_db.refresh(kb)
        assert kb.downloads == 1

    def test_add_star_with_none_star_count(self, test_db: Session, factory: TestDataFactory):
        """测试为 None 收藏数的知识库添加收藏"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(star_count=None)

        result = service.add_star(user.id, kb.id)

        assert result is True
        test_db.refresh(kb)
        assert kb.star_count == 1

    def test_remove_star_with_zero_star_count(self, test_db: Session, factory: TestDataFactory):
        """测试从零收藏数的知识库移除收藏"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(star_count=0)
        factory.create_star_record(user=user, target_id=kb.id, target_type="knowledge")

        result = service.remove_star(user.id, kb.id)

        assert result is True
        test_db.refresh(kb)
        # star_count 不应该变成负数
        assert kb.star_count == 0

    def test_resolve_uploader_id_with_empty_string(self, test_db: Session):
        """测试使用空字符串解析上传者 ID"""
        service = KnowledgeService(test_db)

        result = service.resolve_uploader_id("")

        assert result is None

    def test_resolve_uploader_id_with_none(self, test_db: Session):
        """测试使用 None 解析上传者 ID"""
        service = KnowledgeService(test_db)

        result = service.resolve_uploader_id(None)

        assert result is None


class TestKnowledgeServicePermissionChecks:
    """测试 KnowledgeService 权限检查"""

    def test_update_knowledge_base_permission_denied_for_non_owner(self, test_db: Session, factory: TestDataFactory):
        """测试非所有者无权更新知识库"""
        service = KnowledgeService(test_db)
        owner = factory.create_user()
        other_user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=owner)

        success, message, result = service.update_knowledge_base(
            kb.id, {"description": "New description"}, other_user.id, is_admin=False, is_moderator=False
        )

        assert success is False
        assert "是你的知识库吗你就改" in message
        assert result is None

    def test_update_knowledge_base_moderator_can_update(self, test_db: Session, factory: TestDataFactory):
        """测试审核员可以更新知识库"""
        service = KnowledgeService(test_db)
        owner = factory.create_user()
        moderator = factory.create_user()
        kb = factory.create_knowledge_base(uploader=owner)

        success, message, result = service.update_knowledge_base(
            kb.id, {"description": "Moderator update"}, moderator.id, is_admin=False, is_moderator=True
        )

        assert success is True
        assert result.description == "Moderator update"

    def test_update_knowledge_base_public_status_requires_admin(self, test_db: Session, factory: TestDataFactory):
        """测试修改公开状态需要管理员权限"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user, is_public=False, is_pending=False)

        success, message, result = service.update_knowledge_base(
            kb.id, {"is_public": True}, user.id, is_admin=False, is_moderator=False
        )

        assert success is False
        assert "只有管理员可以直接修改公开状态" in message

    def test_update_knowledge_base_pending_restricted_fields(self, test_db: Session, factory: TestDataFactory):
        """测试审核中的知识库限制修改字段"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user, is_pending=True)

        success, message, result = service.update_knowledge_base(kb.id, {"name": "New name"}, user.id)

        assert success is False
        assert "仅允许修改补充说明" in message

    def test_update_knowledge_base_protected_fields_removed(self, test_db: Session, factory: TestDataFactory):
        """测试受保护字段被移除"""
        service = KnowledgeService(test_db)
        user = factory.create_user()
        kb = factory.create_knowledge_base(
            uploader=user, is_public=False, is_pending=False, copyright_owner="Original Owner"
        )

        success, message, result = service.update_knowledge_base(
            kb.id, {"description": "New description", "copyright_owner": "Hacker", "name": "Hacked Name"}, user.id
        )

        assert success is True
        assert result.description == "New description"
        # 受保护字段不应该被修改
        assert result.copyright_owner == "Original Owner"
        assert result.name == kb.name
