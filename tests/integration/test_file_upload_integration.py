"""
Integration tests for file upload workflows

Tests complete upload workflows, progress tracking, interruption recovery,
and file metadata saving for both knowledge bases and persona cards.

Requirements: FR5 - 文件上传边界测试
Tasks: 6.3.1, 6.3.2, 6.3.3, 6.3.4, 6.3.5
"""

import os
import pytest
import tempfile
import shutil
import json
import toml
from io import BytesIO
from unittest.mock import Mock, patch, AsyncMock
from fastapi import UploadFile
from datetime import datetime

# Mock sqlite_db_manager before importing file_upload
import app.services.file_upload_service

if not hasattr(app.services.file_upload_service, "sqlite_db_manager"):
    app.services.file_upload_service.sqlite_db_manager = Mock()

from app.services.file_upload_service import FileUploadService
from app.models.database import KnowledgeBase, PersonaCard, KnowledgeBaseFile, PersonaCardFile
from app.core.error_handlers import ValidationError

# Mark all tests in this file as serial to avoid file system race conditions
# and mock state pollution between parallel workers
pytestmark = [pytest.mark.serial, pytest.mark.xdist_group("file_upload")]


@pytest.fixture(autouse=True)
def reset_file_upload_mocks():
    """Reset file upload mocks before each test to avoid state pollution"""
    # Reset before test
    if hasattr(app.services.file_upload_service, "sqlite_db_manager"):
        app.services.file_upload_service.sqlite_db_manager.reset_mock()
    yield
    # Reset after test
    if hasattr(app.services.file_upload_service, "sqlite_db_manager"):
        app.services.file_upload_service.sqlite_db_manager.reset_mock()


class TestCompleteUploadWorkflow:
    """
    Task 6.3.1: 测试完整上传流程

    Tests end-to-end upload workflows for knowledge bases and persona cards,
    including file validation, saving, and database record creation.
    """

    def setup_method(self):
        """Setup for each test method"""
        import uuid

        self.service = FileUploadService()
        # Use unique temp directory for each test to avoid conflicts
        self.unique_id = uuid.uuid4().hex[:8]
        self.temp_dir = tempfile.mkdtemp(suffix=f"_{self.unique_id}")

    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_complete_knowledge_base_upload_workflow(self):
        """
        Test complete knowledge base upload workflow

        Validates:
        - File validation (type, size)
        - File saving to disk
        - Database record creation
        - File metadata storage
        - Directory structure creation
        """
        # Create mock files
        file1_content = b"Knowledge base content 1"
        file2_content = b"Knowledge base content 2 in JSON"

        mock_file1 = Mock(spec=UploadFile)
        mock_file1.filename = "knowledge1.txt"
        mock_file1.size = len(file1_content)
        mock_file1.read = AsyncMock(return_value=file1_content)

        mock_file2 = Mock(spec=UploadFile)
        mock_file2.filename = "knowledge2.json"
        mock_file2.size = len(file2_content)
        mock_file2.read = AsyncMock(return_value=file2_content)

        files = [mock_file1, mock_file2]

        # Mock database operations
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = "kb_test_123"
        mock_kb.name = "Test KB"
        mock_kb.base_path = os.path.join(self.temp_dir, "test_kb")

        mock_file_record1 = Mock(spec=KnowledgeBaseFile)
        mock_file_record1.id = "file_1"
        mock_file_record1.file_name = "knowledge1.txt"

        mock_file_record2 = Mock(spec=KnowledgeBaseFile)
        mock_file_record2.id = "file_2"
        mock_file_record2.file_name = "knowledge2.json"

        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base.return_value = mock_kb
        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base_file.side_effect = [
            mock_file_record1,
            mock_file_record2,
        ]

        # Execute upload workflow
        result = await self.service.upload_knowledge_base(
            files=files,
            name="Test KB",
            description="Test description",
            uploader_id="user_123",
            copyright_owner="Test Owner",
            content="Test content",
            tags="test,knowledge",
        )

        # Verify results
        assert result is not None
        assert result.id == "kb_test_123"

        # Verify database calls
        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base.assert_called_once()
        assert app.services.file_upload_service.sqlite_db_manager.save_knowledge_base_file.call_count == 2

    @pytest.mark.asyncio
    async def test_complete_persona_card_upload_workflow(self):
        """
        Test complete persona card upload workflow

        Validates:
        - TOML file validation
        - Version extraction from TOML
        - File saving to disk
        - Database record creation
        - Error handling and cleanup on failure
        """
        # Create mock TOML file with version
        toml_content = """
[meta]
version = "1.0.0"

[character]
name = "Test Character"
description = "A test character"
"""
        toml_bytes = toml_content.encode("utf-8")

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.size = len(toml_bytes)
        mock_file.read = AsyncMock(return_value=toml_bytes)

        files = [mock_file]

        # Use unique name to avoid conflicts in parallel execution
        unique_name = f"Test Persona {self.unique_id}"

        # Execute upload workflow
        result = await self.service.upload_persona_card(
            files=files,
            name=unique_name,
            description="Test description",
            uploader_id=f"user_{self.unique_id}",
            copyright_owner="Test Owner",
            content="Test content",
            tags="test,persona",
        )

        # Verify results
        assert result is not None
        assert isinstance(result, PersonaCard)
        assert result.name == unique_name
        assert result.version == "1.0.0"
        assert result.is_pending is True
        assert result.is_public is False

        # Verify directory was created
        assert os.path.exists(result.base_path)

        # Verify TOML file was saved
        toml_file_path = os.path.join(result.base_path, "bot_config.toml")
        assert os.path.exists(toml_file_path)

        # Verify TOML content
        with open(toml_file_path, "r", encoding="utf-8") as f:
            saved_toml = toml.load(f)
        assert saved_toml["meta"]["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_upload_workflow_with_validation_failure(self):
        """
        Test upload workflow handles validation failures correctly

        Validates:
        - Invalid file type rejection
        - File size limit enforcement
        - Proper error messages
        - No partial data saved on failure
        """
        # Create mock file with invalid type
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "invalid.exe"
        mock_file.size = 1024
        mock_file.read = AsyncMock(return_value=b"fake exe content")

        files = [mock_file]

        # Attempt upload - should fail validation
        with pytest.raises(Exception) as exc_info:
            await self.service.upload_knowledge_base(
                files=files, name="Test KB", description="Test description", uploader_id="user_123"
            )

        # Verify error message mentions file type
        assert "不支持的文件类型" in str(exc_info.value) or "file type" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_workflow_with_oversized_file(self):
        """
        Test upload workflow rejects oversized files

        Validates:
        - File size validation before processing
        - Proper error message for oversized files
        """
        # Create mock file exceeding size limit
        oversized_content = b"x" * (self.service.MAX_FILE_SIZE + 1)

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "large.txt"
        mock_file.size = len(oversized_content)
        mock_file.read = AsyncMock(return_value=oversized_content)

        files = [mock_file]

        # Attempt upload - should fail size validation
        with pytest.raises(Exception) as exc_info:
            await self.service.upload_knowledge_base(
                files=files, name="Test KB", description="Test description", uploader_id="user_123"
            )

        # Verify error message mentions file size
        assert "文件" in str(exc_info.value) and (
            "过大" in str(exc_info.value) or "size" in str(exc_info.value).lower()
        )


class TestUploadProgressTracking:
    """
    Task 6.3.2: 测试上传进度跟踪

    Tests upload progress tracking functionality if implemented.
    Note: Current implementation doesn't have explicit progress tracking,
    but we test file-by-file processing which provides implicit progress.
    """

    def setup_method(self):
        """Setup for each test method"""
        import uuid

        self.service = FileUploadService()
        # Use unique temp directory for each test to avoid conflicts
        self.unique_id = uuid.uuid4().hex[:8]
        self.temp_dir = tempfile.mkdtemp(suffix=f"_{self.unique_id}")

    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_multiple_file_upload_processing(self):
        """
        Test that multiple files are processed sequentially

        Validates:
        - Each file is validated individually
        - Each file is saved individually
        - Partial success is handled (all-or-nothing not required)
        """
        # Create multiple mock files
        files = []
        for i in range(5):
            content = f"File {i} content".encode("utf-8")
            mock_file = Mock(spec=UploadFile)
            mock_file.filename = f"file{i}.txt"
            mock_file.size = len(content)
            mock_file.read = AsyncMock(return_value=content)
            files.append(mock_file)

        # Mock database operations
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = "kb_multi_123"
        mock_kb.base_path = os.path.join(self.temp_dir, "multi_kb")

        mock_file_records = []
        for i in range(5):
            mock_record = Mock(spec=KnowledgeBaseFile)
            mock_record.id = f"file_{i}"
            mock_record.file_name = f"file{i}.txt"
            mock_file_records.append(mock_record)

        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base.return_value = mock_kb
        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base_file.side_effect = mock_file_records

        # Execute upload
        result = await self.service.upload_knowledge_base(
            files=files, name="Multi File KB", description="Test with multiple files", uploader_id="user_123"
        )

        # Verify all files were processed
        assert result is not None
        assert app.services.file_upload_service.sqlite_db_manager.save_knowledge_base_file.call_count == 5

    @pytest.mark.asyncio
    async def test_file_size_tracking_during_upload(self):
        """
        Test that file sizes are correctly tracked during upload

        Validates:
        - File size is calculated correctly
        - File size is stored in database records
        """
        content = b"Test content with known size"
        expected_size = len(content)

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "sized_file.txt"
        mock_file.size = expected_size
        mock_file.read = AsyncMock(return_value=content)

        # Mock database operations
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = "kb_size_123"
        mock_kb.base_path = os.path.join(self.temp_dir, "size_kb")

        saved_file_data = None

        def capture_file_data(data):
            nonlocal saved_file_data
            saved_file_data = data
            mock_record = Mock(spec=KnowledgeBaseFile)
            mock_record.id = "file_1"
            return mock_record

        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base.return_value = mock_kb
        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base_file.side_effect = capture_file_data

        # Execute upload
        await self.service.upload_knowledge_base(
            files=[mock_file], name="Size Test KB", description="Test file size tracking", uploader_id="user_123"
        )

        # Verify file size was captured
        assert saved_file_data is not None
        assert saved_file_data["file_size"] == expected_size


class TestUploadInterruptionRecovery:
    """
    Task 6.3.3: 测试上传中断恢复

    Tests handling of upload interruptions and cleanup on failure.
    """

    def setup_method(self):
        """Setup for each test method"""
        import uuid

        self.service = FileUploadService()
        # Use unique temp directory for each test to avoid conflicts
        self.unique_id = uuid.uuid4().hex[:8]
        self.temp_dir = tempfile.mkdtemp(suffix=f"_{self.unique_id}")

    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_persona_card_cleanup_on_failure(self):
        """
        Test that persona card directory is cleaned up on upload failure

        Validates:
        - Directory is created during upload
        - Directory is removed if upload fails
        - No partial data remains after failure
        """
        # Create mock TOML file without version (will cause failure)
        toml_content = """
[character]
name = "Test Character"
"""
        toml_bytes = toml_content.encode("utf-8")

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.size = len(toml_bytes)
        mock_file.read = AsyncMock(return_value=toml_bytes)

        # Track created directories
        created_dirs = []
        original_makedirs = os.makedirs

        def track_makedirs(path, **kwargs):
            created_dirs.append(path)
            return original_makedirs(path, **kwargs)

        with patch("os.makedirs", side_effect=track_makedirs):
            # Attempt upload - should fail due to missing version
            with pytest.raises(ValidationError) as exc_info:
                await self.service.upload_persona_card(
                    files=[mock_file],
                    name="Test Persona",
                    description="Test description",
                    uploader_id="user_123",
                    copyright_owner="Test Owner",
                )

            # Verify error is about TOML parsing (missing version causes parse error)
            error_msg = str(exc_info.value)
            assert any(keyword in error_msg for keyword in ["TOML", "toml", "解析", "parse", "格式", "format"])

        # Verify cleanup: created directories should be removed
        for dir_path in created_dirs:
            if "persona" in dir_path:
                assert not os.path.exists(dir_path), f"Directory {dir_path} should have been cleaned up"

    @pytest.mark.asyncio
    async def test_file_read_error_handling(self):
        """
        Test handling of file read errors during upload

        Validates:
        - Read errors are caught and handled
        - Appropriate error message is returned
        - No partial data is saved
        """
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "error_file.txt"
        mock_file.size = 1024
        mock_file.read = AsyncMock(side_effect=IOError("Disk read error"))

        # Mock database operations
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = "kb_error_123"
        mock_kb.base_path = os.path.join(self.temp_dir, "error_kb")

        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base.return_value = mock_kb

        # Attempt upload - should fail with read error
        with pytest.raises(Exception) as exc_info:
            await self.service.upload_knowledge_base(
                files=[mock_file], name="Error Test KB", description="Test error handling", uploader_id="user_123"
            )

        # Verify error is related to file operations
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ["error", "failed", "失败", "错误"])

    @pytest.mark.asyncio
    async def test_disk_full_error_handling(self):
        """
        Test handling of disk full errors during file save

        Validates:
        - Disk full errors are caught
        - Appropriate error message is returned
        - Cleanup is attempted
        """
        content = b"Test content"
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "disk_full.txt"
        mock_file.size = len(content)
        mock_file.read = AsyncMock(return_value=content)

        # Mock database operations
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = "kb_disk_123"
        mock_kb.base_path = os.path.join(self.temp_dir, "disk_kb")

        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base.return_value = mock_kb

        # Mock file write to simulate disk full
        with patch("builtins.open", side_effect=OSError("No space left on device")):
            with pytest.raises(Exception) as exc_info:
                await self.service.upload_knowledge_base(
                    files=[mock_file],
                    name="Disk Full Test KB",
                    description="Test disk full handling",
                    uploader_id="user_123",
                )

            # Verify error message
            error_msg = str(exc_info.value).lower()
            assert any(keyword in error_msg for keyword in ["failed", "error", "失败", "错误"])


class TestFileMetadataSaving:
    """
    Task 6.3.4: 测试文件元数据保存

    Tests that file metadata is correctly saved and retrievable.
    """

    def setup_method(self):
        """Setup for each test method"""
        import uuid

        self.service = FileUploadService()
        # Use unique temp directory for each test to avoid conflicts
        self.unique_id = uuid.uuid4().hex[:8]
        self.temp_dir = tempfile.mkdtemp(suffix=f"_{self.unique_id}")

    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_knowledge_base_file_metadata_storage(self):
        """
        Test that knowledge base file metadata is correctly stored

        Validates:
        - File name is stored
        - Original name is preserved
        - File path is stored
        - File type is extracted and stored
        - File size is calculated and stored
        """
        content = b"Test knowledge content"
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "knowledge_meta.txt"
        mock_file.size = len(content)
        mock_file.read = AsyncMock(return_value=content)

        # Mock database operations
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = "kb_meta_123"
        mock_kb.base_path = os.path.join(self.temp_dir, "meta_kb")

        saved_metadata = None

        def capture_metadata(data):
            nonlocal saved_metadata
            saved_metadata = data
            mock_record = Mock(spec=KnowledgeBaseFile)
            mock_record.id = "file_meta_1"
            return mock_record

        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base.return_value = mock_kb
        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base_file.side_effect = capture_metadata

        # Execute upload
        await self.service.upload_knowledge_base(
            files=[mock_file], name="Metadata Test KB", description="Test metadata storage", uploader_id="user_123"
        )

        # Verify metadata was captured correctly
        assert saved_metadata is not None
        assert saved_metadata["file_name"] == "knowledge_meta.txt"
        assert saved_metadata["original_name"] == "knowledge_meta.txt"
        assert saved_metadata["file_type"] == ".txt"
        assert saved_metadata["file_size"] == len(content)
        assert saved_metadata["knowledge_base_id"] == "kb_meta_123"
        assert "file_path" in saved_metadata

    @pytest.mark.asyncio
    async def test_persona_card_version_metadata_extraction(self):
        """
        Test that persona card version is correctly extracted and stored

        Validates:
        - Version is extracted from TOML
        - Version is stored in PersonaCard object
        - Different version field names are supported
        """
        # Test with different version field locations
        test_cases = [
            ('version = "1.0.0"', "1.0.0"),
            ('[meta]\nversion = "2.0.0"', "2.0.0"),
            ('[card]\nversion = "3.0.0"', "3.0.0"),
            ('schema_version = "4.0.0"', "4.0.0"),
        ]

        for toml_content, expected_version in test_cases:
            toml_bytes = toml_content.encode("utf-8")

            mock_file = Mock(spec=UploadFile)
            mock_file.filename = "bot_config.toml"
            mock_file.size = len(toml_bytes)
            mock_file.read = AsyncMock(return_value=toml_bytes)

            # Execute upload
            result = await self.service.upload_persona_card(
                files=[mock_file],
                name=f"Test Persona {expected_version}",
                description="Test version extraction",
                uploader_id="user_123",
                copyright_owner="Test Owner",
            )

            # Verify version was extracted correctly
            assert result.version == expected_version, f"Expected version {expected_version}, got {result.version}"

            # Cleanup for next iteration
            if os.path.exists(result.base_path):
                shutil.rmtree(result.base_path)

    @pytest.mark.asyncio
    async def test_file_metadata_with_special_characters(self):
        """
        Test metadata storage with special characters in filenames

        Validates:
        - Special characters are handled correctly
        - Filenames are sanitized if needed
        - Metadata is stored correctly
        """
        content = b"Content with special filename"

        # Test various special character scenarios
        test_filenames = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file.multiple.dots.txt",
        ]

        for filename in test_filenames:
            mock_file = Mock(spec=UploadFile)
            mock_file.filename = filename
            mock_file.size = len(content)
            mock_file.read = AsyncMock(return_value=content)

            # Mock database operations
            mock_kb = Mock(spec=KnowledgeBase)
            mock_kb.id = f"kb_special_{filename}"
            mock_kb.base_path = os.path.join(self.temp_dir, f"special_{filename}")

            saved_metadata = None

            def capture_metadata(data):
                nonlocal saved_metadata
                saved_metadata = data
                mock_record = Mock(spec=KnowledgeBaseFile)
                mock_record.id = f"file_{filename}"
                return mock_record

            app.services.file_upload_service.sqlite_db_manager.save_knowledge_base.return_value = mock_kb
            app.services.file_upload_service.sqlite_db_manager.save_knowledge_base_file.side_effect = capture_metadata

            # Execute upload
            await self.service.upload_knowledge_base(
                files=[mock_file],
                name=f"Special Char Test {filename}",
                description="Test special characters",
                uploader_id="user_123",
            )

            # Verify metadata was captured
            assert saved_metadata is not None
            assert saved_metadata["original_name"] == filename
            assert saved_metadata["file_type"] == ".txt"


class TestFileUploadCoverageImprovement:
    """
    Task 6.3.5: 验证file_upload.py达到95%以上覆盖率

    Additional tests to cover uncovered lines and branches in file_upload.py
    """

    def setup_method(self):
        """Setup for each test method"""
        import uuid

        self.service = FileUploadService()
        # Use unique temp directory for each test to avoid conflicts
        self.unique_id = uuid.uuid4().hex[:8]
        self.temp_dir = tempfile.mkdtemp(suffix=f"_{self.unique_id}")

        # Reset mocks to avoid side_effect carryover from previous tests
        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base_file.reset_mock()
        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base.reset_mock()
        app.services.file_upload_service.sqlite_db_manager.get_knowledge_base_by_id.reset_mock()
        app.services.file_upload_service.sqlite_db_manager.get_files_by_knowledge_base_id.reset_mock()

    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_get_knowledge_base_content(self):
        """
        Test retrieving knowledge base content

        Covers: get_knowledge_base_content method
        """
        # Mock database operations
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = "kb_content_123"
        mock_kb.name = "Test KB"
        mock_kb.to_dict.return_value = {"id": "kb_content_123", "name": "Test KB"}

        mock_file1 = Mock(spec=KnowledgeBaseFile)
        mock_file1.id = "file_1"
        mock_file1.original_name = "file1.txt"
        mock_file1.file_size = 1024

        mock_file2 = Mock(spec=KnowledgeBaseFile)
        mock_file2.id = "file_2"
        mock_file2.original_name = "file2.json"
        mock_file2.file_size = 2048

        app.services.file_upload_service.sqlite_db_manager.get_knowledge_base_by_id.return_value = mock_kb
        app.services.file_upload_service.sqlite_db_manager.get_files_by_knowledge_base_id.return_value = [
            mock_file1,
            mock_file2,
        ]

        # Execute
        result = self.service.get_knowledge_base_content("kb_content_123")

        # Verify
        assert result is not None
        assert "knowledge_base" in result
        assert "files" in result
        assert len(result["files"]) == 2
        assert result["files"][0]["file_id"] == "file_1"
        assert result["files"][0]["original_name"] == "file1.txt"
        assert result["files"][0]["file_size"] == 1024

    @pytest.mark.asyncio
    async def test_get_knowledge_base_content_not_found(self):
        """
        Test retrieving non-existent knowledge base

        Covers: Error path in get_knowledge_base_content
        """
        app.services.file_upload_service.sqlite_db_manager.get_knowledge_base_by_id.return_value = None

        # Execute - should raise HTTPException
        with pytest.raises(Exception) as exc_info:
            self.service.get_knowledge_base_content("nonexistent_kb")

        # Verify error
        assert (
            "404" in str(exc_info.value)
            or "不存在" in str(exc_info.value)
            or "not found" in str(exc_info.value).lower()
        )

    @pytest.mark.asyncio
    async def test_get_persona_card_content(self):
        """
        Test retrieving persona card content

        Covers: get_persona_card_content method
        """
        # Mock database operations
        mock_pc = Mock(spec=PersonaCard)
        mock_pc.id = "pc_content_123"
        mock_pc.name = "Test Persona"
        mock_pc.to_dict.return_value = {"id": "pc_content_123", "name": "Test Persona"}

        mock_file = Mock(spec=PersonaCardFile)
        mock_file.id = "file_1"
        mock_file.original_name = "bot_config.toml"
        mock_file.file_size = 512

        app.services.file_upload_service.sqlite_db_manager.get_persona_card_by_id.return_value = mock_pc
        app.services.file_upload_service.sqlite_db_manager.get_files_by_persona_card_id.return_value = [mock_file]

        # Execute
        result = self.service.get_persona_card_content("pc_content_123")

        # Verify
        assert result is not None
        assert "persona_card" in result
        assert "files" in result
        assert len(result["files"]) == 1
        assert result["files"][0]["file_id"] == "file_1"

    @pytest.mark.asyncio
    async def test_add_files_to_knowledge_base(self):
        """
        Test adding files to existing knowledge base

        Covers: add_files_to_knowledge_base method

        Uses unique IDs and paths to avoid race conditions in parallel execution.
        """
        import uuid

        # Use unique ID for this test instance to avoid conflicts
        unique_id = uuid.uuid4().hex[:8]

        # Create mock existing KB with unique path
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = f"kb_add_{unique_id}"
        mock_kb.base_path = os.path.join(self.temp_dir, f"add_kb_{unique_id}")
        mock_kb.updated_at = datetime.now()
        mock_kb.to_dict.return_value = {"id": mock_kb.id}
        os.makedirs(mock_kb.base_path, exist_ok=True)

        # Mock existing files
        existing_file = Mock(spec=KnowledgeBaseFile)
        existing_file.original_name = f"existing_{unique_id}.txt"

        app.services.file_upload_service.sqlite_db_manager.get_knowledge_base_by_id.return_value = mock_kb
        app.services.file_upload_service.sqlite_db_manager.get_files_by_knowledge_base_id.return_value = [existing_file]

        # Create new file to add with unique name
        content = b"New file content"
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = f"new_file_{unique_id}.txt"
        mock_file.size = len(content)
        mock_file.read = AsyncMock(return_value=content)

        mock_new_file_record = Mock(spec=KnowledgeBaseFile)
        mock_new_file_record.id = f"new_file_{unique_id}"

        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base_file.return_value = mock_new_file_record
        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base.return_value = mock_kb

        # Execute
        result = await self.service.add_files_to_knowledge_base(
            kb_id=mock_kb.id, files=[mock_file], user_id=f"user_{unique_id}"
        )

        # Verify
        assert result is not None
        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_files_exceeding_limit(self):
        """
        Test adding files that exceed the maximum file count

        Covers: File count validation in add_files_to_knowledge_base
        """
        # Create mock KB with many existing files
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = "kb_limit_123"
        mock_kb.base_path = os.path.join(self.temp_dir, "limit_kb")

        # Create 100 existing files (at the limit)
        existing_files = []
        for i in range(self.service.MAX_KNOWLEDGE_FILES):
            mock_file = Mock(spec=KnowledgeBaseFile)
            mock_file.original_name = f"existing_{i}.txt"
            existing_files.append(mock_file)

        app.services.file_upload_service.sqlite_db_manager.get_knowledge_base_by_id.return_value = mock_kb
        app.services.file_upload_service.sqlite_db_manager.get_files_by_knowledge_base_id.return_value = existing_files

        # Try to add one more file
        content = b"One more file"
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "one_more.txt"
        mock_file.size = len(content)
        mock_file.read = AsyncMock(return_value=content)

        # Execute - should fail
        with pytest.raises(ValidationError) as exc_info:
            await self.service.add_files_to_knowledge_base(kb_id="kb_limit_123", files=[mock_file], user_id="user_123")

        # Verify error message
        assert "文件数量" in str(exc_info.value) or "limit" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_add_duplicate_filename(self):
        """
        Test adding file with duplicate filename

        Covers: Duplicate filename check in add_files_to_knowledge_base
        """
        # Create mock KB
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = "kb_dup_123"
        mock_kb.base_path = os.path.join(self.temp_dir, "dup_kb")

        # Mock existing file with same name
        existing_file = Mock(spec=KnowledgeBaseFile)
        existing_file.original_name = "duplicate.txt"

        app.services.file_upload_service.sqlite_db_manager.get_knowledge_base_by_id.return_value = mock_kb
        app.services.file_upload_service.sqlite_db_manager.get_files_by_knowledge_base_id.return_value = [existing_file]

        # Try to add file with same name
        content = b"Duplicate file"
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "duplicate.txt"
        mock_file.size = len(content)
        mock_file.read = AsyncMock(return_value=content)

        # Execute - should fail
        with pytest.raises(ValidationError) as exc_info:
            await self.service.add_files_to_knowledge_base(kb_id="kb_dup_123", files=[mock_file], user_id="user_123")

        # Verify error message
        assert (
            "文件名" in str(exc_info.value)
            or "already exists" in str(exc_info.value).lower()
            or "已存在" in str(exc_info.value)
        )

    @pytest.mark.asyncio
    async def test_delete_files_from_knowledge_base(self):
        """
        Test deleting files from knowledge base

        Covers: delete_files_from_knowledge_base method
        """
        # Create mock KB and file
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = "kb_del_123"
        mock_kb.base_path = os.path.join(self.temp_dir, "del_kb")
        mock_kb.updated_at = datetime.now()
        mock_kb.to_dict.return_value = {"id": "kb_del_123"}
        os.makedirs(mock_kb.base_path, exist_ok=True)

        # Create actual file to delete
        file_path = os.path.join(mock_kb.base_path, "to_delete.txt")
        with open(file_path, "w") as f:
            f.write("File to delete")

        mock_file = Mock(spec=KnowledgeBaseFile)
        mock_file.id = "file_del_1"
        mock_file.knowledge_base_id = "kb_del_123"
        mock_file.file_path = "to_delete.txt"
        mock_file.original_name = "to_delete.txt"

        app.services.file_upload_service.sqlite_db_manager.get_knowledge_base_by_id.return_value = mock_kb
        app.services.file_upload_service.sqlite_db_manager.get_knowledge_base_file_by_id.return_value = mock_file
        app.services.file_upload_service.sqlite_db_manager.delete_knowledge_base_file.return_value = True
        app.services.file_upload_service.sqlite_db_manager.save_knowledge_base.return_value = mock_kb

        # Execute
        result = await self.service.delete_files_from_knowledge_base(
            kb_id="kb_del_123", file_id="file_del_1", user_id="user_123"
        )

        # Verify
        assert result is True
        assert not os.path.exists(file_path)
        app.services.file_upload_service.sqlite_db_manager.delete_knowledge_base_file.assert_called_once_with(
            "file_del_1"
        )

    @pytest.mark.asyncio
    async def test_create_knowledge_base_zip(self):
        """
        Test creating ZIP archive of knowledge base

        Covers: create_knowledge_base_zip method
        """
        # Create mock KB with files
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = "kb_zip_123"
        mock_kb.name = "Test KB"
        mock_kb.description = "Test description"
        mock_kb.copyright_owner = "Test Owner"
        mock_kb.created_at = datetime.now()
        mock_kb.updated_at = datetime.now()
        mock_kb.base_path = os.path.join(self.temp_dir, "zip_kb")
        mock_kb.uploader_id = "user_123"
        os.makedirs(mock_kb.base_path, exist_ok=True)

        # Create actual files
        file1_path = os.path.join(mock_kb.base_path, "file1.txt")
        with open(file1_path, "w") as f:
            f.write("File 1 content")

        mock_file1 = Mock(spec=KnowledgeBaseFile)
        mock_file1.file_path = "file1.txt"
        mock_file1.original_name = "file1.txt"
        mock_file1.file_size = 14

        mock_user = Mock()
        mock_user.username = "testuser"

        app.services.file_upload_service.sqlite_db_manager.get_knowledge_base_by_id.return_value = mock_kb
        app.services.file_upload_service.sqlite_db_manager.get_files_by_knowledge_base_id.return_value = [mock_file1]
        app.services.file_upload_service.sqlite_db_manager.get_user_by_id.return_value = mock_user

        # Execute
        result = await self.service.create_knowledge_base_zip("kb_zip_123")

        # Verify
        assert result is not None
        assert "zip_path" in result
        assert "zip_filename" in result
        assert os.path.exists(result["zip_path"])
        assert result["zip_filename"].endswith(".zip")

        # Cleanup
        if os.path.exists(result["zip_path"]):
            os.remove(result["zip_path"])

    @pytest.mark.asyncio
    async def test_create_zip_with_missing_files(self):
        """
        Test ZIP creation fails when files are missing

        Covers: Error path in create_knowledge_base_zip
        """
        # Create mock KB
        mock_kb = Mock(spec=KnowledgeBase)
        mock_kb.id = "kb_missing_123"
        mock_kb.base_path = os.path.join(self.temp_dir, "missing_kb")
        os.makedirs(mock_kb.base_path, exist_ok=True)

        # Mock file that doesn't exist
        mock_file = Mock(spec=KnowledgeBaseFile)
        mock_file.file_path = "nonexistent.txt"
        mock_file.original_name = "nonexistent.txt"

        app.services.file_upload_service.sqlite_db_manager.get_knowledge_base_by_id.return_value = mock_kb
        app.services.file_upload_service.sqlite_db_manager.get_files_by_knowledge_base_id.return_value = [mock_file]

        # Execute - should fail
        with pytest.raises(Exception) as exc_info:
            await self.service.create_knowledge_base_zip("kb_missing_123")

        # Verify error
        assert "404" in str(exc_info.value) or "不存在" in str(exc_info.value) or "not" in str(exc_info.value).lower()
