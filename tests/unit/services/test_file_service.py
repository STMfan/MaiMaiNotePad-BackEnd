"""
测试 FileService 类

测试文件服务层的所有功能，包括文件保存、验证、知识库和人设卡操作

Requirements: 2.2
"""

import os
import pytest
import tempfile
import shutil
from unittest.mock import patch
from sqlalchemy.orm import Session

from app.services.file_service import FileService, FileValidationError, FileDatabaseError
from app.models.database import KnowledgeBase, KnowledgeBaseFile


class TestFileServiceInit:
    """测试 FileService 初始化"""

    def test_init_creates_directories(self, test_db: Session):
        """测试初始化时创建必要的目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"UPLOAD_DIR": temp_dir}):
                service = FileService(test_db)

                assert os.path.exists(service.upload_dir)
                assert os.path.exists(service.knowledge_dir)
                assert os.path.exists(service.persona_dir)

    def test_init_with_relative_path(self, test_db: Session):
        """测试使用相对路径初始化"""
        with patch.dict(os.environ, {"UPLOAD_DIR": "test_uploads"}):
            service = FileService(test_db)
            assert service.upload_dir.startswith("./")


class TestFileValidation:
    """测试文件验证功能"""

    def test_validate_file_type_valid(self, test_db: Session):
        """测试有效的文件类型验证"""
        service = FileService(test_db)

        assert service._validate_file_type("test.txt", [".txt", ".json"])
        assert service._validate_file_type("test.json", [".txt", ".json"])
        assert service._validate_file_type("test.toml", [".toml"])

    def test_validate_file_type_invalid(self, test_db: Session):
        """测试无效的文件类型验证"""
        service = FileService(test_db)

        assert not service._validate_file_type("test.exe", [".txt", ".json"])
        assert not service._validate_file_type("test.pdf", [".txt", ".json"])
        assert not service._validate_file_type("", [".txt"])
        assert not service._validate_file_type(None, [".txt"])

    def test_validate_file_type_case_insensitive(self, test_db: Session):
        """测试文件类型验证不区分大小写"""
        service = FileService(test_db)

        assert service._validate_file_type("test.TXT", [".txt"])
        assert service._validate_file_type("test.JSON", [".json"])

    def test_validate_file_size_valid(self, test_db: Session):
        """测试有效的文件大小验证"""
        service = FileService(test_db)

        assert service._validate_file_size(1024)  # 1KB
        assert service._validate_file_size(service.MAX_FILE_SIZE)  # 最大值

    def test_validate_file_size_invalid(self, test_db: Session):
        """测试无效的文件大小验证"""
        service = FileService(test_db)

        assert not service._validate_file_size(service.MAX_FILE_SIZE + 1)


class TestFileSave:
    """测试文件保存功能"""

    def test_save_file_success(self, test_db: Session):
        """测试成功保存文件"""
        service = FileService(test_db)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_content = b"Test file content"
            filename = "test.txt"

            file_path, file_size = service._save_file(file_content, filename, temp_dir)

            assert os.path.exists(file_path)
            assert file_size == len(file_content)

            with open(file_path, "rb") as f:
                assert f.read() == file_content

    def test_save_file_with_duplicate_name(self, test_db: Session):
        """测试保存同名文件时添加时间戳"""
        service = FileService(test_db)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_content1 = b"First file"
            file_content2 = b"Second file"
            filename = "test.txt"

            # 保存第一个文件
            file_path1, _ = service._save_file(file_content1, filename, temp_dir)

            # 保存同名文件
            file_path2, _ = service._save_file(file_content2, filename, temp_dir)

            # 两个文件路径应该不同
            assert file_path1 != file_path2
            assert os.path.exists(file_path1)
            assert os.path.exists(file_path2)

    def test_save_file_creates_directory(self, test_db: Session):
        """测试保存文件时自动创建目录"""
        service = FileService(test_db)

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = os.path.join(temp_dir, "new_dir")
            file_content = b"Test content"

            file_path, _ = service._save_file(file_content, "test.txt", target_dir)

            assert os.path.exists(target_dir)
            assert os.path.exists(file_path)

    def test_save_file_error_handling(self, test_db: Session):
        """测试文件保存错误处理"""
        service = FileService(test_db)

        # 使用无效路径
        with pytest.raises(FileDatabaseError, match="文件保存失败"):
            service._save_file(b"content", "test.txt", "/invalid/path/that/does/not/exist")


class TestVersionExtraction:
    """测试版本号提取功能"""

    def test_extract_version_from_top_level(self, test_db: Session):
        """测试从顶层提取版本号"""
        service = FileService(test_db)

        data = {"version": "1.0.0", "name": "test"}
        assert service._extract_version_from_toml(data) == "1.0.0"

    def test_extract_version_from_meta(self, test_db: Session):
        """测试从 meta 字段提取版本号"""
        service = FileService(test_db)

        data = {"meta": {"version": "2.0.0"}, "name": "test"}
        assert service._extract_version_from_toml(data) == "2.0.0"

    def test_extract_version_from_card(self, test_db: Session):
        """测试从 card 字段提取版本号"""
        service = FileService(test_db)

        data = {"card": {"version": "3.0.0"}, "name": "test"}
        assert service._extract_version_from_toml(data) == "3.0.0"

    def test_extract_version_deep_search(self, test_db: Session):
        """测试深度搜索版本号"""
        service = FileService(test_db)

        data = {"config": {"settings": {"version": "4.0.0"}}}
        assert service._extract_version_from_toml(data) == "4.0.0"

    def test_extract_version_not_found(self, test_db: Session):
        """测试未找到版本号"""
        service = FileService(test_db)

        data = {"name": "test", "description": "no version"}
        assert service._extract_version_from_toml(data) is None

    def test_extract_version_invalid_input(self, test_db: Session):
        """测试无效输入"""
        service = FileService(test_db)

        assert service._extract_version_from_toml(None) is None
        assert service._extract_version_from_toml("not a dict") is None
        assert service._extract_version_from_toml([]) is None


class TestKnowledgeBaseUpload:
    """测试知识库上传功能"""

    def test_upload_knowledge_base_success(self, test_db: Session, factory):
        """测试成功上传知识库"""
        service = FileService(test_db)
        user = factory.create_user()

        files = [("test1.txt", b"Content 1"), ("test2.json", b'{"key": "value"}')]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(service, "knowledge_dir", temp_dir):
                kb = service.upload_knowledge_base(
                    files=files,
                    name="Test KB",
                    description="Test description",
                    uploader_id=user.id,
                    copyright_owner="Test Owner",
                )

                assert kb.name == "Test KB"
                assert kb.description == "Test description"
                assert kb.uploader_id == user.id
                assert kb.is_pending is True
                assert kb.is_public is False

                # 验证文件记录
                kb_files = test_db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == kb.id).all()
                assert len(kb_files) == 2

    def test_upload_knowledge_base_too_many_files(self, test_db: Session, factory):
        """测试上传文件数量超过限制"""
        service = FileService(test_db)
        user = factory.create_user()

        # 创建超过限制的文件列表
        files = [(f"test{i}.txt", b"content") for i in range(service.MAX_KNOWLEDGE_FILES + 1)]

        with pytest.raises(FileValidationError, match="文件数量超过限制"):
            service.upload_knowledge_base(files=files, name="Test KB", description="Test", uploader_id=user.id)

    def test_upload_knowledge_base_invalid_file_type(self, test_db: Session, factory):
        """测试上传无效文件类型"""
        service = FileService(test_db)
        user = factory.create_user()

        files = [("test.exe", b"invalid content")]

        with pytest.raises(FileValidationError, match="不支持的文件类型"):
            service.upload_knowledge_base(files=files, name="Test KB", description="Test", uploader_id=user.id)

    def test_upload_knowledge_base_file_too_large(self, test_db: Session, factory):
        """测试上传文件过大"""
        service = FileService(test_db)
        user = factory.create_user()

        # 创建超大文件
        large_content = b"x" * (service.MAX_FILE_SIZE + 1)
        files = [("test.txt", large_content)]

        with pytest.raises(FileValidationError, match="文件过大"):
            service.upload_knowledge_base(files=files, name="Test KB", description="Test", uploader_id=user.id)

    def test_upload_knowledge_base_rollback_on_error(self, test_db: Session, factory):
        """测试上传失败时回滚"""
        service = FileService(test_db)
        user = factory.create_user()

        files = [("test.txt", b"content")]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(service, "knowledge_dir", temp_dir):
                # Mock db.commit to raise an error
                with patch.object(test_db, "commit", side_effect=Exception("DB Error")):
                    with pytest.raises(FileDatabaseError, match="知识库保存失败"):
                        service.upload_knowledge_base(
                            files=files, name="Test KB", description="Test", uploader_id=user.id
                        )

                # 验证没有创建知识库记录
                kb_count = test_db.query(KnowledgeBase).count()
                assert kb_count == 0


class TestPersonaCardUpload:
    """测试人设卡上传功能"""

    def test_upload_persona_card_success(self, test_db: Session, factory):
        """测试成功上传人设卡"""
        service = FileService(test_db)
        user = factory.create_user()

        toml_content = b'version = "1.0.0"\nname = "Test Persona"'
        files = [("bot_config.toml", toml_content)]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(service, "persona_dir", temp_dir):
                pc = service.upload_persona_card(
                    files=files,
                    name="Test Persona",
                    description="Test description",
                    uploader_id=user.id,
                    copyright_owner="Test Owner",
                )

                assert pc.name == "Test Persona"
                assert pc.version == "1.0.0"
                assert pc.is_pending is True
                assert pc.is_public is False

    def test_upload_persona_card_wrong_file_count(self, test_db: Session, factory):
        """测试人设卡文件数量错误"""
        service = FileService(test_db)
        user = factory.create_user()

        # 测试没有文件
        with pytest.raises(FileValidationError, match="必须且仅包含一个"):
            service.upload_persona_card(
                files=[], name="Test", description="Test", uploader_id=user.id, copyright_owner="Test"
            )

        # 测试多个文件
        files = [("bot_config.toml", b"version = '1.0.0'"), ("extra.toml", b"extra = 'data'")]
        with pytest.raises(FileValidationError, match="必须且仅包含一个"):
            service.upload_persona_card(
                files=files, name="Test", description="Test", uploader_id=user.id, copyright_owner="Test"
            )

    def test_upload_persona_card_wrong_filename(self, test_db: Session, factory):
        """测试人设卡文件名错误"""
        service = FileService(test_db)
        user = factory.create_user()

        files = [("wrong_name.toml", b"version = '1.0.0'")]

        with pytest.raises(FileValidationError, match="配置文件名必须为 bot_config.toml"):
            service.upload_persona_card(
                files=files, name="Test", description="Test", uploader_id=user.id, copyright_owner="Test"
            )

    def test_upload_persona_card_missing_version(self, test_db: Session, factory):
        """测试人设卡缺少版本号"""
        service = FileService(test_db)
        user = factory.create_user()

        toml_content = b'name = "Test"\ndescription = "No version"'
        files = [("bot_config.toml", toml_content)]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(service, "persona_dir", temp_dir):
                with pytest.raises(FileValidationError, match="未找到版本号字段"):
                    service.upload_persona_card(
                        files=files, name="Test", description="Test", uploader_id=user.id, copyright_owner="Test"
                    )

    def test_upload_persona_card_invalid_toml(self, test_db: Session, factory):
        """测试人设卡 TOML 格式错误"""
        service = FileService(test_db)
        user = factory.create_user()

        toml_content = b"invalid toml [[[["
        files = [("bot_config.toml", toml_content)]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(service, "persona_dir", temp_dir):
                with pytest.raises(FileValidationError, match="TOML 语法错误"):
                    service.upload_persona_card(
                        files=files, name="Test", description="Test", uploader_id=user.id, copyright_owner="Test"
                    )


class TestGetContent:
    """测试获取内容功能"""

    def test_get_knowledge_base_content(self, test_db: Session, factory):
        """测试获取知识库内容"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        kb_file = factory.create_knowledge_base_file(knowledge_base=kb)

        content = service.get_knowledge_base_content(kb.id)

        assert content["knowledge_base"]["id"] == kb.id
        assert content["knowledge_base"]["name"] == kb.name
        assert len(content["files"]) == 1
        assert content["files"][0]["file_id"] == kb_file.id

    def test_get_knowledge_base_content_not_found(self, test_db: Session):
        """测试获取不存在的知识库"""
        service = FileService(test_db)

        with pytest.raises(FileValidationError, match="知识库不存在"):
            service.get_knowledge_base_content("nonexistent_id")

    def test_get_persona_card_content(self, test_db: Session, factory):
        """测试获取人设卡内容"""
        service = FileService(test_db)
        pc = factory.create_persona_card()
        pc_file = factory.create_persona_card_file(persona_card=pc)

        content = service.get_persona_card_content(pc.id)

        assert content["persona_card"]["id"] == pc.id
        assert content["persona_card"]["name"] == pc.name
        assert len(content["files"]) == 1
        assert content["files"][0]["file_id"] == pc_file.id

    def test_get_persona_card_content_not_found(self, test_db: Session):
        """测试获取不存在的人设卡"""
        service = FileService(test_db)

        with pytest.raises(FileValidationError, match="人设卡不存在"):
            service.get_persona_card_content("nonexistent_id")


class TestAddFiles:
    """测试添加文件功能"""

    def test_add_files_to_knowledge_base_success(self, test_db: Session, factory):
        """测试成功向知识库添加文件"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        # 确保知识库目录存在
        os.makedirs(kb.base_path, exist_ok=True)

        try:
            new_files = [("new_file.txt", b"New content")]

            updated_kb = service.add_files_to_knowledge_base(kb.id, new_files, user.id)

            assert updated_kb.id == kb.id

            # 验证文件已添加
            kb_files = test_db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == kb.id).all()
            assert len(kb_files) == 1
        finally:
            # 清理
            if os.path.exists(kb.base_path):
                shutil.rmtree(kb.base_path)

    def test_add_files_duplicate_filename(self, test_db: Session, factory):
        """测试添加同名文件"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        # 创建已存在的文件
        factory.create_knowledge_base_file(knowledge_base=kb, original_name="existing.txt")

        os.makedirs(kb.base_path, exist_ok=True)

        try:
            new_files = [("existing.txt", b"Duplicate")]

            with pytest.raises(FileValidationError, match="文件名已存在"):
                service.add_files_to_knowledge_base(kb.id, new_files, user.id)
        finally:
            if os.path.exists(kb.base_path):
                shutil.rmtree(kb.base_path)

    def test_add_files_exceeds_limit(self, test_db: Session, factory):
        """测试添加文件超过数量限制"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        # 创建接近限制的文件
        for i in range(service.MAX_KNOWLEDGE_FILES):
            factory.create_knowledge_base_file(knowledge_base=kb, original_name=f"file{i}.txt")

        os.makedirs(kb.base_path, exist_ok=True)

        try:
            new_files = [("one_more.txt", b"Too many")]

            with pytest.raises(FileValidationError, match="文件数量超过限制"):
                service.add_files_to_knowledge_base(kb.id, new_files, user.id)
        finally:
            if os.path.exists(kb.base_path):
                shutil.rmtree(kb.base_path)


class TestDeleteFiles:
    """测试删除文件功能"""

    def test_delete_file_from_knowledge_base_success(self, test_db: Session, factory):
        """测试成功从知识库删除文件"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        # 创建文件
        os.makedirs(kb.base_path, exist_ok=True)
        kb_file = factory.create_knowledge_base_file(knowledge_base=kb)

        # 创建物理文件
        file_path = os.path.join(kb.base_path, kb_file.file_path)
        with open(file_path, "w") as f:
            f.write("test content")

        try:
            result = service.delete_file_from_knowledge_base(kb.id, kb_file.id, user.id)

            assert result is True
            assert not os.path.exists(file_path)

            # 验证数据库记录已删除
            deleted_file = test_db.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.id == kb_file.id).first()
            assert deleted_file is None
        finally:
            if os.path.exists(kb.base_path):
                shutil.rmtree(kb.base_path)

    def test_delete_file_not_found(self, test_db: Session, factory):
        """测试删除不存在的文件"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        with pytest.raises(FileValidationError, match="文件不存在"):
            service.delete_file_from_knowledge_base(kb.id, "nonexistent_id", user.id)

    def test_delete_knowledge_base_success(self, test_db: Session, factory):
        """测试成功删除知识库"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        # 创建知识库目录
        os.makedirs(kb.base_path, exist_ok=True)

        result = service.delete_knowledge_base(kb.id, user.id)

        assert result is True
        assert not os.path.exists(kb.base_path)

    def test_delete_knowledge_base_not_found(self, test_db: Session):
        """测试删除不存在的知识库"""
        service = FileService(test_db)

        result = service.delete_knowledge_base("nonexistent_id", "user_id")
        assert result is False


class TestZipCreation:
    """测试 ZIP 创建功能"""

    def test_create_knowledge_base_zip_success(self, test_db: Session, factory):
        """测试成功创建知识库 ZIP"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()

        # 创建知识库目录和文件
        os.makedirs(kb.base_path, exist_ok=True)
        kb_file = factory.create_knowledge_base_file(knowledge_base=kb)

        file_path = os.path.join(kb.base_path, kb_file.file_path)
        with open(file_path, "w") as f:
            f.write("test content")

        try:
            result = service.create_knowledge_base_zip(kb.id)

            assert "zip_path" in result
            assert "zip_filename" in result
            assert os.path.exists(result["zip_path"])
            assert result["zip_filename"].endswith(".zip")

            # 清理 ZIP 文件
            os.remove(result["zip_path"])
        finally:
            if os.path.exists(kb.base_path):
                shutil.rmtree(kb.base_path)

    def test_create_knowledge_base_zip_missing_files(self, test_db: Session, factory):
        """测试创建 ZIP 时文件缺失"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()

        # 创建文件记录但不创建物理文件
        factory.create_knowledge_base_file(knowledge_base=kb)

        with pytest.raises(FileValidationError, match="文件不存在"):
            service.create_knowledge_base_zip(kb.id)

    def test_create_persona_card_zip_success(self, test_db: Session, factory):
        """测试成功创建人设卡 ZIP"""
        service = FileService(test_db)
        pc = factory.create_persona_card()

        # 创建人设卡目录和文件
        os.makedirs(pc.base_path, exist_ok=True)
        pc_file = factory.create_persona_card_file(persona_card=pc)

        file_path = os.path.join(pc.base_path, pc_file.file_path)
        with open(file_path, "w") as f:
            f.write("test content")

        try:
            result = service.create_persona_card_zip(pc.id)

            assert "zip_path" in result
            assert "zip_filename" in result
            assert os.path.exists(result["zip_path"])

            # 清理 ZIP 文件
            os.remove(result["zip_path"])
        finally:
            if os.path.exists(pc.base_path):
                shutil.rmtree(pc.base_path)


class TestGetFilePath:
    """测试获取文件路径功能"""

    def test_get_knowledge_base_file_path_success(self, test_db: Session, factory):
        """测试成功获取知识库文件路径"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        kb_file = factory.create_knowledge_base_file(knowledge_base=kb)

        result = service.get_knowledge_base_file_path(kb.id, kb_file.id)

        assert result is not None
        assert result["file_name"] == kb_file.original_name
        assert result["file_path"] == kb_file.file_path

    def test_get_knowledge_base_file_path_not_found(self, test_db: Session, factory):
        """测试获取不存在的文件路径"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()

        result = service.get_knowledge_base_file_path(kb.id, "nonexistent_id")
        assert result is None

    def test_get_persona_card_file_path_success(self, test_db: Session, factory):
        """测试成功获取人设卡文件路径"""
        service = FileService(test_db)
        pc = factory.create_persona_card()
        pc_file = factory.create_persona_card_file(persona_card=pc)

        result = service.get_persona_card_file_path(pc.id, pc_file.id)

        assert result is not None
        assert result["file_id"] == pc_file.id
        assert result["file_name"] == pc_file.original_name
        assert result["file_path"] == pc_file.file_path

    def test_get_persona_card_file_path_not_found(self, test_db: Session, factory):
        """测试获取不存在的人设卡文件路径"""
        service = FileService(test_db)
        pc = factory.create_persona_card()

        result = service.get_persona_card_file_path(pc.id, "nonexistent_id")
        assert result is None


class TestExceptionHandling:
    """测试 file_service 异常处理"""

    def test_save_file_permission_denied(self, test_db: Session):
        """测试文件保存权限被拒绝"""
        service = FileService(test_db)

        # 使用只读目录模拟权限错误
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(FileDatabaseError, match="文件保存失败"):
                service._save_file(b"content", "test.txt", "/tmp")

    def test_save_file_disk_full(self, test_db: Session):
        """测试磁盘空间不足"""
        service = FileService(test_db)

        # 模拟磁盘空间不足
        with patch("builtins.open", side_effect=OSError("No space left on device")):
            with pytest.raises(FileDatabaseError, match="文件保存失败"):
                service._save_file(b"content", "test.txt", "/tmp")

    def test_upload_knowledge_base_db_exception(self, test_db: Session, factory):
        """测试知识库上传时数据库异常"""
        service = FileService(test_db)
        user = factory.create_user()

        files = [("test.txt", b"content")]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(service, "knowledge_dir", temp_dir):
                # Mock db.flush to raise exception
                with patch.object(test_db, "flush", side_effect=Exception("DB Error")):
                    with pytest.raises(FileDatabaseError, match="知识库保存失败"):
                        service.upload_knowledge_base(files=files, name="Test", description="Test", uploader_id=user.id)

    def test_upload_persona_card_db_exception(self, test_db: Session, factory):
        """测试人设卡上传时数据库异常"""
        service = FileService(test_db)
        user = factory.create_user()

        toml_content = b'version = "1.0.0"'
        files = [("bot_config.toml", toml_content)]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(service, "persona_dir", temp_dir):
                # Mock db.flush to raise exception
                with patch.object(test_db, "flush", side_effect=Exception("DB Error")):
                    with pytest.raises(FileDatabaseError, match="人设卡保存失败"):
                        service.upload_persona_card(
                            files=files, name="Test", description="Test", uploader_id=user.id, copyright_owner="Test"
                        )

    def test_add_files_kb_not_found(self, test_db: Session):
        """测试向不存在的知识库添加文件"""
        service = FileService(test_db)

        files = [("test.txt", b"content")]

        with pytest.raises(FileValidationError, match="知识库不存在"):
            service.add_files_to_knowledge_base("nonexistent_id", files, "user_id")

    def test_add_files_kb_dir_not_exist(self, test_db: Session, factory):
        """测试知识库目录不存在"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()

        # 设置不存在的目录（不要commit，避免数据库状态问题）
        kb.base_path = "/nonexistent/path"

        files = [("test.txt", b"content")]

        with pytest.raises(FileDatabaseError, match="知识库目录不存在"):
            service.add_files_to_knowledge_base(kb.id, files, "user_id")

    def test_add_files_db_exception(self, test_db: Session, factory):
        """测试添加文件时数据库异常"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        os.makedirs(kb.base_path, exist_ok=True)

        try:
            files = [("test.txt", b"content")]

            # Mock db.commit to raise exception
            with patch.object(test_db, "commit", side_effect=Exception("DB Error")):
                with pytest.raises(FileDatabaseError, match="添加文件失败"):
                    service.add_files_to_knowledge_base(kb.id, files, user.id)
        finally:
            if os.path.exists(kb.base_path):
                shutil.rmtree(kb.base_path)

    def test_delete_file_kb_not_found(self, test_db: Session):
        """测试从不存在的知识库删除文件"""
        service = FileService(test_db)

        with pytest.raises(FileValidationError, match="知识库不存在"):
            service.delete_file_from_knowledge_base("nonexistent_id", "file_id", "user_id")

    def test_delete_file_kb_dir_not_exist(self, test_db: Session, factory):
        """测试删除文件时知识库目录不存在"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        user = factory.create_user()
        kb_file = factory.create_knowledge_base_file(knowledge_base=kb)

        # 设置不存在的目录
        kb.base_path = "/nonexistent/path"
        test_db.commit()

        with pytest.raises(FileDatabaseError, match="知识库目录不存在"):
            service.delete_file_from_knowledge_base(kb.id, kb_file.id, user.id)

    def test_delete_file_db_exception(self, test_db: Session, factory):
        """测试删除文件时数据库异常"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()

        os.makedirs(kb.base_path, exist_ok=True)
        kb_file = factory.create_knowledge_base_file(knowledge_base=kb)

        # 创建物理文件
        file_path = os.path.join(kb.base_path, kb_file.file_path)
        with open(file_path, "w") as f:
            f.write("test")

        try:
            # Mock os.remove to raise exception
            with patch("os.remove", side_effect=Exception("Cannot delete file")):
                with pytest.raises(FileDatabaseError, match="删除文件失败"):
                    service.delete_file_from_knowledge_base(kb.id, kb_file.id, "user_id")
        finally:
            if os.path.exists(kb.base_path):
                shutil.rmtree(kb.base_path)

    def test_delete_knowledge_base_dir_error(self, test_db: Session, factory):
        """测试删除知识库目录失败"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        # 创建目录
        os.makedirs(kb.base_path, exist_ok=True)

        # Mock shutil.rmtree to raise exception
        with patch("shutil.rmtree", side_effect=Exception("Cannot delete")):
            result = service.delete_knowledge_base(kb.id, user.id)
            assert result is False

    def test_create_kb_zip_not_found(self, test_db: Session):
        """测试创建不存在的知识库ZIP"""
        service = FileService(test_db)

        with pytest.raises(FileValidationError, match="知识库不存在"):
            service.create_knowledge_base_zip("nonexistent_id")

    def test_create_pc_zip_not_found(self, test_db: Session):
        """测试创建不存在的人设卡ZIP"""
        service = FileService(test_db)

        with pytest.raises(FileValidationError, match="人设卡不存在"):
            service.create_persona_card_zip("nonexistent_id")

    def test_create_kb_zip_error(self, test_db: Session, factory):
        """测试创建知识库ZIP时发生错误"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        kb_file = factory.create_knowledge_base_file(knowledge_base=kb)

        os.makedirs(kb.base_path, exist_ok=True)

        file_path = os.path.join(kb.base_path, kb_file.file_path)
        with open(file_path, "w") as f:
            f.write("test")

        try:
            # Mock zipfile.ZipFile to raise exception
            with patch("zipfile.ZipFile", side_effect=Exception("Zip error")):
                with pytest.raises(FileDatabaseError, match="创建压缩包失败"):
                    service.create_knowledge_base_zip(kb.id)
        finally:
            if os.path.exists(kb.base_path):
                shutil.rmtree(kb.base_path)

    def test_create_pc_zip_error(self, test_db: Session, factory):
        """测试创建人设卡ZIP时发生错误"""
        service = FileService(test_db)
        pc = factory.create_persona_card()

        os.makedirs(pc.base_path, exist_ok=True)
        pc_file = factory.create_persona_card_file(persona_card=pc)

        file_path = os.path.join(pc.base_path, pc_file.file_path)
        with open(file_path, "w") as f:
            f.write("test")

        try:
            # Mock zipfile.ZipFile to raise exception
            with patch("zipfile.ZipFile", side_effect=Exception("Zip error")):
                with pytest.raises(FileDatabaseError, match="创建压缩包失败"):
                    service.create_persona_card_zip(pc.id)
        finally:
            if os.path.exists(pc.base_path):
                shutil.rmtree(pc.base_path)

    def test_get_kb_file_path_kb_not_found(self, test_db: Session):
        """测试获取不存在知识库的文件路径"""
        service = FileService(test_db)

        result = service.get_knowledge_base_file_path("nonexistent_id", "file_id")
        assert result is None

    def test_get_pc_file_path_pc_not_found(self, test_db: Session):
        """测试获取不存在人设卡的文件路径"""
        service = FileService(test_db)

        result = service.get_persona_card_file_path("nonexistent_id", "file_id")
        assert result is None


class TestEdgeCases:
    """测试边界情况"""

    def test_validate_file_type_empty_filename(self, test_db: Session):
        """测试空文件名验证"""
        service = FileService(test_db)

        assert not service._validate_file_type("", [".txt"])
        assert not service._validate_file_type(None, [".txt"])

    def test_validate_file_size_zero(self, test_db: Session):
        """测试零字节文件"""
        service = FileService(test_db)

        assert service._validate_file_size(0)

    def test_validate_file_size_negative(self, test_db: Session):
        """测试负数文件大小"""
        service = FileService(test_db)

        # 负数应该通过验证（虽然不现实，但代码允许）
        assert service._validate_file_size(-1)

    def test_extract_version_with_list(self, test_db: Session):
        """测试从包含列表的数据中提取版本"""
        service = FileService(test_db)

        data = {"items": [{"version": "1.0.0"}, {"version": "2.0.0"}]}
        # 深度搜索会找到列表中的版本（顺序可能不确定）
        version = service._extract_version_from_toml(data)
        assert version in ["1.0.0", "2.0.0"]

    def test_extract_version_circular_reference(self, test_db: Session):
        """测试循环引用数据"""
        service = FileService(test_db)

        data = {"name": "test"}
        data["self"] = data  # 循环引用

        # 不应该崩溃，应该返回None
        version = service._extract_version_from_toml(data)
        assert version is None

    def test_upload_kb_with_none_values(self, test_db: Session, factory):
        """测试使用None值上传知识库"""
        service = FileService(test_db)
        user = factory.create_user()

        files = [("test.txt", b"content")]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(service, "knowledge_dir", temp_dir):
                kb = service.upload_knowledge_base(
                    files=files,
                    name="Test",
                    description="Test",
                    uploader_id=user.id,
                    copyright_owner=None,
                    content=None,
                    tags=None,
                )

                assert kb.copyright_owner is None
                assert kb.content is None
                assert kb.tags is None

    def test_upload_pc_with_none_values(self, test_db: Session, factory):
        """测试使用None值上传人设卡"""
        service = FileService(test_db)
        user = factory.create_user()

        toml_content = b'version = "1.0.0"'
        files = [("bot_config.toml", toml_content)]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(service, "persona_dir", temp_dir):
                pc = service.upload_persona_card(
                    files=files,
                    name="Test",
                    description="Test",
                    uploader_id=user.id,
                    copyright_owner="Test",
                    content=None,
                    tags=None,
                )

                assert pc.content is None
                assert pc.tags is None

    def test_persona_card_file_size_exceeded(self, test_db: Session, factory):
        """测试人设卡文件大小超限"""
        service = FileService(test_db)
        user = factory.create_user()

        # 创建超大文件
        large_content = b"x" * (service.MAX_FILE_SIZE + 1)
        files = [("bot_config.toml", large_content)]

        with pytest.raises(FileValidationError, match="文件过大"):
            service.upload_persona_card(
                files=files, name="Test", description="Test", uploader_id=user.id, copyright_owner="Test"
            )

    def test_persona_card_wrong_file_type(self, test_db: Session, factory):
        """测试人设卡错误文件类型"""
        service = FileService(test_db)
        user = factory.create_user()

        # 文件名正确但类型错误
        files = [("bot_config.toml", b"content")]  # 内容不是有效的TOML

        # 这会先通过文件名检查，然后在TOML解析时失败
        with pytest.raises(FileValidationError, match="TOML 语法错误"):
            service.upload_persona_card(
                files=files, name="Test", description="Test", uploader_id=user.id, copyright_owner="Test"
            )

    def test_add_files_invalid_file_type(self, test_db: Session, factory):
        """测试添加无效文件类型到知识库"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        os.makedirs(kb.base_path, exist_ok=True)

        try:
            files = [("test.exe", b"invalid")]

            with pytest.raises(FileValidationError, match="不支持的文件类型"):
                service.add_files_to_knowledge_base(kb.id, files, user.id)
        finally:
            if os.path.exists(kb.base_path):
                shutil.rmtree(kb.base_path)

    def test_add_files_file_too_large(self, test_db: Session, factory):
        """测试添加过大文件到知识库"""
        service = FileService(test_db)
        kb = factory.create_knowledge_base()

        os.makedirs(kb.base_path, exist_ok=True)

        try:
            large_content = b"x" * (service.MAX_FILE_SIZE + 1)
            files = [("test.txt", large_content)]

            with pytest.raises(FileValidationError, match="文件过大"):
                service.add_files_to_knowledge_base(kb.id, files, "user_id")
        finally:
            if os.path.exists(kb.base_path):
                shutil.rmtree(kb.base_path)
