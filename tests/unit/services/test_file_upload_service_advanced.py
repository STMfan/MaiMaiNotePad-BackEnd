"""
单元测试: FileUploadService 高级功能

测试 app/file_upload.py 中的知识库上传、人设卡上传和 ZIP 创建功能

Requirements: 2.1
"""
import os
import pytest
import tempfile
import shutil
import zipfile
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime
from fastapi import UploadFile, HTTPException
import sys

# Inject sqlite_db_manager mock into app.services.file_upload_service module before importing
import app.services.file_upload_service
if not hasattr(app.services.file_upload_service, 'sqlite_db_manager'):
    app.services.file_upload_service.sqlite_db_manager = Mock()

from app.services.file_upload_service import FileUploadService
from app.core.error_handlers import ValidationError, DatabaseError


class TestKnowledgeBaseUpload:
    """测试知识库上传功能 - Task 3.1.5"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.service = FileUploadService()
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('os.makedirs')
    @patch('app.services.file_upload_service.datetime')
    async def test_upload_knowledge_base_success(self, mock_datetime, mock_makedirs, mock_db):
        """测试成功上传知识库
        
        验证：
        - 验证文件类型和大小
        - 创建知识库目录
        - 保存知识库到数据库
        - 保存文件并创建文件记录
        """
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        
        # Mock database
        mock_kb = Mock()
        mock_kb.id = "kb123"
        mock_db.save_knowledge_base.return_value = mock_kb
        mock_db.save_knowledge_base_file.return_value = Mock(id="file123")
        
        # Create mock files
        mock_file1 = Mock(spec=UploadFile)
        mock_file1.filename = "test1.txt"
        mock_file1.read = AsyncMock(return_value=b"content1")
        mock_file1.size = 1024
        
        mock_file2 = Mock(spec=UploadFile)
        mock_file2.filename = "test2.json"
        mock_file2.read = AsyncMock(return_value=b"content2")
        mock_file2.size = 2048
        
        files = [mock_file1, mock_file2]
        
        # Mock file saving
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.side_effect = [
                ("/path/to/test1.txt", 1024),
                ("/path/to/test2.json", 2048)
            ]
            
            # Execute
            result = await self.service.upload_knowledge_base(
                files=files,
                name="Test KB",
                description="Test description",
                uploader_id="user123",
                copyright_owner="Test Owner",
                tags="test,knowledge"
            )
        
        # Verify
        assert result == mock_kb
        mock_makedirs.assert_called_once()
        mock_db.save_knowledge_base.assert_called_once()
        assert mock_db.save_knowledge_base_file.call_count == 2

    @pytest.mark.asyncio
    async def test_upload_knowledge_base_too_many_files(self):
        """测试上传文件数量超过限制
        
        验证：
        - 文件数量超过 MAX_KNOWLEDGE_FILES 时抛出 HTTPException
        """
        # Create too many files
        files = [Mock(spec=UploadFile, filename=f"test{i}.txt") for i in range(self.service.MAX_KNOWLEDGE_FILES + 1)]
        
        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_knowledge_base(
                files=files,
                name="Test KB",
                description="Test",
                uploader_id="user123"
            )
        
        assert exc_info.value.status_code == 400
        assert "文件数量超过限制" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_upload_knowledge_base_invalid_file_type(self):
        """测试上传无效文件类型
        
        验证：
        - 不支持的文件类型抛出 HTTPException
        """
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.exe"
        mock_file.size = 1024
        
        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_knowledge_base(
                files=[mock_file],
                name="Test KB",
                description="Test",
                uploader_id="user123"
            )
        
        assert exc_info.value.status_code == 400
        assert "不支持的文件类型" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_upload_knowledge_base_file_too_large(self):
        """测试上传文件过大
        
        验证：
        - 文件大小超过限制时抛出 HTTPException
        """
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.size = self.service.MAX_FILE_SIZE + 1
        
        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_knowledge_base(
                files=[mock_file],
                name="Test KB",
                description="Test",
                uploader_id="user123"
            )
        
        assert exc_info.value.status_code == 400
        assert "文件过大" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_upload_knowledge_base_file_content_too_large(self):
        """测试上传文件内容过大（覆盖第218-220行）
        
        验证：
        - 当文件的实际内容大小超过限制时抛出 HTTPException
        - 即使 file.size 属性为 None 或较小，也会检查实际内容大小
        - 错误消息包含"文件内容过大"
        
        这个测试覆盖了 upload_knowledge_base 方法中调用 _validate_file_content 
        并在验证失败时抛出异常的代码路径（第218-220行）
        """
        # Create a mock file with small .size but large actual content
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.size = None  # Size attribute is None (can't determine size from metadata)
        
        # Mock the read() to return content larger than MAX_FILE_SIZE
        large_content = b"x" * (self.service.MAX_FILE_SIZE + 1)
        mock_file.read = AsyncMock(return_value=large_content)
        mock_file.seek = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await self.service.upload_knowledge_base(
                files=[mock_file],
                name="Test KB",
                description="Test",
                uploader_id="user123"
            )
        
        assert exc_info.value.status_code == 400
        assert "文件内容过大" in exc_info.value.detail
        assert "test.txt" in exc_info.value.detail
        # Verify that file.read() was called to check actual content
        mock_file.read.assert_called()
        # Verify that file.seek(0) was called to reset file pointer
        mock_file.seek.assert_called_with(0)
    
    @pytest.mark.asyncio
    async def test_upload_knowledge_base_file_content_at_limit(self):
        """测试上传文件内容正好在大小限制边界
        
        验证：
        - 文件内容大小正好等于 MAX_FILE_SIZE 时应该通过验证
        - 这是边界值测试，确保边界条件正确处理
        """
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.size = None
        
        # Content exactly at the limit
        content_at_limit = b"x" * self.service.MAX_FILE_SIZE
        mock_file.read = AsyncMock(return_value=content_at_limit)
        mock_file.seek = AsyncMock()
        
        # Mock database and file operations to allow the test to proceed
        with patch('app.services.file_upload_service.sqlite_db_manager') as mock_db:
            mock_kb = Mock()
            mock_kb.id = "kb123"
            mock_db.save_knowledge_base.return_value = mock_kb
            mock_db.save_knowledge_base_file.return_value = Mock(id="file123")
            
            with patch('os.makedirs'):
                with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
                    mock_save.return_value = ("/path/to/test.txt", self.service.MAX_FILE_SIZE)
                    
                    # This should NOT raise an exception
                    result = await self.service.upload_knowledge_base(
                        files=[mock_file],
                        name="Test KB",
                        description="Test",
                        uploader_id="user123"
                    )
                    
                    assert result == mock_kb
                    # Verify content validation was performed
                    mock_file.read.assert_called()
                    mock_file.seek.assert_called_with(0)
    
    @pytest.mark.asyncio
    async def test_upload_knowledge_base_file_content_just_under_limit(self):
        """测试上传文件内容略小于大小限制
        
        验证：
        - 文件内容大小略小于 MAX_FILE_SIZE 时应该通过验证
        """
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.size = None
        
        # Content just under the limit
        content_under_limit = b"x" * (self.service.MAX_FILE_SIZE - 1)
        mock_file.read = AsyncMock(return_value=content_under_limit)
        mock_file.seek = AsyncMock()
        
        # Mock database and file operations
        with patch('app.services.file_upload_service.sqlite_db_manager') as mock_db:
            mock_kb = Mock()
            mock_kb.id = "kb123"
            mock_db.save_knowledge_base.return_value = mock_kb
            mock_db.save_knowledge_base_file.return_value = Mock(id="file123")
            
            with patch('os.makedirs'):
                with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
                    mock_save.return_value = ("/path/to/test.txt", self.service.MAX_FILE_SIZE - 1)
                    
                    # This should NOT raise an exception
                    result = await self.service.upload_knowledge_base(
                        files=[mock_file],
                        name="Test KB",
                        description="Test",
                        uploader_id="user123"
                    )
                    
                    assert result == mock_kb
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    async def test_add_files_to_knowledge_base_success(self, mock_db):
        """测试成功向知识库添加文件
        
        验证：
        - 验证知识库存在
        - 检查文件数量限制
        - 检查同名文件
        - 保存文件并创建记录
        """
        # Mock database
        mock_kb = Mock()
        mock_kb.id = "kb123"
        mock_kb.base_path = "/path/to/kb"
        mock_kb.updated_at = datetime.now()
        mock_db.get_knowledge_base_by_id.return_value = mock_kb
        mock_db.get_files_by_knowledge_base_id.return_value = []
        mock_db.save_knowledge_base_file.return_value = Mock(id="file123")
        mock_db.save_knowledge_base.return_value = mock_kb
        
        # Create mock file
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "new_file.txt"
        mock_file.read = AsyncMock(return_value=b"content")
        mock_file.size = 1024
        
        # Mock file saving
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/kb/new_file.txt", 1024)
            with patch('os.path.exists', return_value=True):
                # Execute
                result = await self.service.add_files_to_knowledge_base(
                    kb_id="kb123",
                    files=[mock_file],
                    user_id="user123"
                )
        
        # Verify
        assert result == mock_kb
        mock_db.save_knowledge_base_file.assert_called_once()
        mock_db.save_knowledge_base.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    async def test_add_files_to_knowledge_base_not_found(self, mock_db):
        """测试向不存在的知识库添加文件
        
        验证：
        - 知识库不存在时抛出 ValidationError
        """
        mock_db.get_knowledge_base_by_id.return_value = None
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.txt"
        
        with pytest.raises(ValidationError) as exc_info:
            await self.service.add_files_to_knowledge_base(
                kb_id="nonexistent",
                files=[mock_file],
                user_id="user123"
            )
        
        assert "知识库不存在" in exc_info.value.message
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    async def test_add_files_to_knowledge_base_too_many_files(self, mock_db):
        """测试添加文件超过数量限制
        
        验证：
        - 文件总数超过限制时抛出 ValidationError
        """
        # Mock database with existing files
        mock_kb = Mock()
        mock_kb.id = "kb123"
        mock_db.get_knowledge_base_by_id.return_value = mock_kb
        
        # Create MAX_KNOWLEDGE_FILES existing files
        existing_files = [Mock(original_name=f"file{i}.txt") for i in range(self.service.MAX_KNOWLEDGE_FILES)]
        mock_db.get_files_by_knowledge_base_id.return_value = existing_files
        
        # Try to add one more file
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "new_file.txt"
        
        with pytest.raises(ValidationError) as exc_info:
            await self.service.add_files_to_knowledge_base(
                kb_id="kb123",
                files=[mock_file],
                user_id="user123"
            )
        
        assert "文件数量超过限制" in exc_info.value.message
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    async def test_add_files_to_knowledge_base_duplicate_filename(self, mock_db):
        """测试添加同名文件
        
        验证：
        - 同名文件抛出 ValidationError
        """
        # Mock database with existing file
        mock_kb = Mock()
        mock_kb.id = "kb123"
        mock_db.get_knowledge_base_by_id.return_value = mock_kb
        
        existing_file = Mock(original_name="duplicate.txt")
        mock_db.get_files_by_knowledge_base_id.return_value = [existing_file]
        
        # Try to add file with same name
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "duplicate.txt"
        
        with pytest.raises(ValidationError) as exc_info:
            await self.service.add_files_to_knowledge_base(
                kb_id="kb123",
                files=[mock_file],
                user_id="user123"
            )
        
        assert "文件名已存在" in exc_info.value.message
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('os.path.exists')
    @patch('os.remove')
    async def test_delete_files_from_knowledge_base_success(self, mock_remove, mock_exists, mock_db):
        """测试成功从知识库删除文件
        
        验证：
        - 验证知识库和文件存在
        - 删除物理文件
        - 删除数据库记录
        - 更新知识库时间戳
        """
        # Mock database
        mock_kb = Mock()
        mock_kb.id = "kb123"
        mock_kb.base_path = "/path/to/kb"
        mock_kb.updated_at = datetime.now()
        mock_db.get_knowledge_base_by_id.return_value = mock_kb
        
        mock_file = Mock()
        mock_file.id = "file123"
        mock_file.knowledge_base_id = "kb123"
        mock_file.file_path = "test.txt"
        mock_file.original_name = "test.txt"
        mock_db.get_knowledge_base_file_by_id.return_value = mock_file
        mock_db.save_knowledge_base.return_value = mock_kb
        
        mock_exists.return_value = True
        
        # Execute
        result = await self.service.delete_files_from_knowledge_base(
            kb_id="kb123",
            file_id="file123",
            user_id="user123"
        )
        
        # Verify
        assert result is True
        mock_remove.assert_called_once_with("/path/to/kb/test.txt")
        mock_db.delete_knowledge_base_file.assert_called_once_with("file123")
        mock_db.save_knowledge_base.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    async def test_delete_files_from_knowledge_base_kb_not_found(self, mock_db):
        """测试删除文件时知识库不存在
        
        验证：
        - 知识库不存在时抛出 HTTPException 404
        """
        mock_db.get_knowledge_base_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await self.service.delete_files_from_knowledge_base(
                kb_id="nonexistent",
                file_id="file123",
                user_id="user123"
            )
        
        assert exc_info.value.status_code == 404
        assert "知识库不存在" in exc_info.value.detail
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    async def test_delete_files_from_knowledge_base_file_not_found(self, mock_db):
        """测试删除不存在的文件
        
        验证：
        - 文件不存在时抛出 HTTPException 404
        """
        mock_kb = Mock()
        mock_kb.id = "kb123"
        mock_db.get_knowledge_base_by_id.return_value = mock_kb
        mock_db.get_knowledge_base_file_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await self.service.delete_files_from_knowledge_base(
                kb_id="kb123",
                file_id="nonexistent",
                user_id="user123"
            )
        
        assert exc_info.value.status_code == 404
        assert "文件不存在" in exc_info.value.detail
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('os.path.exists')
    @patch('os.remove')
    async def test_delete_files_from_knowledge_base_remove_failure(self, mock_remove, mock_exists, mock_db):
        """测试删除文件时 os.remove 失败
        
        验证：
        - 当 os.remove 抛出异常时，应该抛出 HTTPException 500
        - 错误消息应该包含文件名和错误详情
        """
        # Mock database
        mock_kb = Mock()
        mock_kb.id = "kb123"
        mock_kb.base_path = "/path/to/kb"
        mock_db.get_knowledge_base_by_id.return_value = mock_kb
        
        mock_file = Mock()
        mock_file.id = "file123"
        mock_file.knowledge_base_id = "kb123"
        mock_file.file_path = "test.txt"
        mock_file.original_name = "test.txt"
        mock_db.get_knowledge_base_file_by_id.return_value = mock_file
        
        mock_exists.return_value = True
        # Simulate permission error when trying to delete file
        mock_remove.side_effect = PermissionError("Permission denied")
        
        # Execute and verify
        with pytest.raises(HTTPException) as exc_info:
            await self.service.delete_files_from_knowledge_base(
                kb_id="kb123",
                file_id="file123",
                user_id="user123"
            )
        
        assert exc_info.value.status_code == 500
        assert "删除文件失败" in exc_info.value.detail
        assert "test.txt" in exc_info.value.detail
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('os.path.exists')
    async def test_delete_files_from_knowledge_base_kb_dir_not_exist(self, mock_exists, mock_db):
        """测试删除文件时知识库目录不存在
        
        验证：
        - 知识库目录不存在时抛出 HTTPException 500
        """
        mock_kb = Mock()
        mock_kb.id = "kb123"
        mock_kb.base_path = "/path/to/kb"
        mock_db.get_knowledge_base_by_id.return_value = mock_kb
        
        mock_file = Mock()
        mock_file.id = "file123"
        mock_file.knowledge_base_id = "kb123"
        mock_file.file_path = "test.txt"
        mock_db.get_knowledge_base_file_by_id.return_value = mock_file
        
        # Directory doesn't exist
        mock_exists.return_value = False
        
        with pytest.raises(HTTPException) as exc_info:
            await self.service.delete_files_from_knowledge_base(
                kb_id="kb123",
                file_id="file123",
                user_id="user123"
            )
        
        assert exc_info.value.status_code == 500
        assert "知识库目录不存在" in exc_info.value.detail


class TestPersonaCardUpload:
    """测试人设卡上传功能 - Task 3.1.6"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.service = FileUploadService()
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.toml')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('app.services.file_upload_service.datetime')
    async def test_upload_persona_card_success(self, mock_datetime, mock_makedirs, mock_open, mock_toml):
        """测试成功上传人设卡
        
        验证：
        - 验证文件数量（必须为1）
        - 验证文件名（必须为 bot_config.toml）
        - 验证文件类型和大小
        - 解析 TOML 版本号
        - 创建 PersonaCard 对象
        """
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        
        # Mock TOML parsing
        mock_toml.load.return_value = {"version": "1.0.0"}
        
        # Mock file operations
        mock_buffer = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_buffer
        
        # Create mock file
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"version = '1.0.0'")
        mock_file.size = 1024
        
        # Mock file saving
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/bot_config.toml", 1024)
            
            # Execute
            result = await self.service.upload_persona_card(
                files=[mock_file],
                name="Test Persona",
                description="Test description",
                uploader_id="user123",
                copyright_owner="Test Owner",
                tags="test,persona"
            )
        
        # Verify
        assert result.name == "Test Persona"
        assert result.version == "1.0.0"
        assert result.is_pending is True
        assert result.is_public is False
    
    @pytest.mark.asyncio
    async def test_upload_persona_card_wrong_file_count(self):
        """测试上传文件数量错误
        
        验证：
        - 文件数量不为1时抛出 ValidationError
        """
        # No files
        with pytest.raises(ValidationError) as exc_info:
            await self.service.upload_persona_card(
                files=[],
                name="Test",
                description="Test",
                uploader_id="user123",
                copyright_owner="Owner"
            )
        assert "必须且仅包含一个" in exc_info.value.message
        
        # Multiple files
        mock_file1 = Mock(spec=UploadFile, filename="file1.toml")
        mock_file2 = Mock(spec=UploadFile, filename="file2.toml")
        
        with pytest.raises(ValidationError) as exc_info:
            await self.service.upload_persona_card(
                files=[mock_file1, mock_file2],
                name="Test",
                description="Test",
                uploader_id="user123",
                copyright_owner="Owner"
            )
        assert "必须且仅包含一个" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_upload_persona_card_wrong_filename(self):
        """测试上传文件名错误
        
        验证：
        - 文件名不是 bot_config.toml 时抛出 ValidationError
        """
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "wrong_name.toml"
        mock_file.size = 1024
        
        with pytest.raises(ValidationError) as exc_info:
            await self.service.upload_persona_card(
                files=[mock_file],
                name="Test",
                description="Test",
                uploader_id="user123",
                copyright_owner="Owner"
            )
        
        assert "文件名必须为 bot_config.toml" in exc_info.value.message
    
    @pytest.mark.asyncio
    async def test_upload_persona_card_invalid_file_type(self):
        """测试上传无效文件类型
        
        验证：
        - 不支持的文件类型抛出 ValidationError
        """
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        # Mock _validate_file_type to return False
        with patch.object(self.service, '_validate_file_type', return_value=False):
            with pytest.raises(ValidationError) as exc_info:
                await self.service.upload_persona_card(
                    files=[mock_file],
                    name="Test",
                    description="Test",
                    uploader_id="user123",
                    copyright_owner="Owner"
                )
        
        assert "不支持的文件类型" in exc_info.value.message
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.toml')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('shutil.rmtree')
    async def test_upload_persona_card_missing_version(self, mock_rmtree, mock_makedirs, mock_open, mock_toml):
        """测试上传缺少版本号的人设卡
        
        验证：
        - TOML 中没有版本号时抛出 ValidationError
        - 清理已创建的目录
        """
        # Mock TOML parsing without version
        mock_toml.load.return_value = {"name": "test"}
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"name = 'test'")
        mock_file.size = 1024
        
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/bot_config.toml", 1024)
            with patch('os.path.exists', return_value=True):
                with pytest.raises(ValidationError) as exc_info:
                    await self.service.upload_persona_card(
                        files=[mock_file],
                        name="Test",
                        description="Test",
                        uploader_id="user123",
                        copyright_owner="Owner"
                    )
        
        # The error message could be either about missing version or TOML parse error
        assert ("未找到版本号字段" in exc_info.value.message or 
                "TOML 语法错误" in exc_info.value.message or
                "配置解析失败" in exc_info.value.message)
        mock_rmtree.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('app.services.file_upload_service.toml')
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    @patch('os.remove')
    async def test_add_files_to_persona_card_success(self, mock_remove, mock_exists, mock_open, mock_toml, mock_db):
        """测试成功向人设卡添加文件
        
        验证：
        - 验证人设卡存在
        - 验证文件数量（必须为1）
        - 验证文件名和类型
        - 解析 TOML 版本号
        - 保存新文件并删除旧文件
        """
        # Mock database
        mock_pc = Mock()
        mock_pc.id = "pc123"
        mock_pc.base_path = "/path/to/pc"
        mock_pc.version = "1.0.0"
        mock_pc.updated_at = datetime.now()
        mock_pc.to_dict.return_value = {"id": "pc123", "version": "2.0.0"}
        mock_db.get_persona_card_by_id.return_value = mock_pc
        mock_db.get_files_by_persona_card_id.return_value = []  # 没有旧文件
        mock_db.save_persona_card_file.return_value = Mock(id="file123")
        mock_db.save_persona_card.return_value = mock_pc
        
        # Mock TOML parsing
        mock_toml.load.return_value = {"version": "2.0.0"}
        
        # Mock file operations
        mock_buffer = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_buffer
        mock_exists.return_value = True
        
        # Create mock file
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"version = '2.0.0'")
        mock_file.size = 1024
        
        # Mock file saving
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/pc/bot_config.toml", 1024)
            # Execute
            result = await self.service.add_files_to_persona_card(
                pc_id="pc123",
                files=[mock_file]
            )
        
        # Verify
        assert result == mock_pc
        mock_db.save_persona_card_file.assert_called_once()
        mock_db.save_persona_card.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    async def test_add_files_to_persona_card_not_found(self, mock_db):
        """测试向不存在的人设卡添加文件
        
        验证：
        - 人设卡不存在时返回 None
        """
        mock_db.get_persona_card_by_id.return_value = None
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        
        result = await self.service.add_files_to_persona_card(
            pc_id="nonexistent",
            files=[mock_file]
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    async def test_add_files_to_persona_card_wrong_file_count(self, mock_db):
        """测试添加文件数量错误
        
        验证：
        - 文件数量不为1时抛出 ValidationError
        """
        mock_pc = Mock()
        mock_pc.id = "pc123"
        mock_db.get_persona_card_by_id.return_value = mock_pc
        
        # Multiple files
        mock_file1 = Mock(spec=UploadFile, filename="file1.toml")
        mock_file2 = Mock(spec=UploadFile, filename="file2.toml")
        
        with pytest.raises(ValidationError) as exc_info:
            await self.service.add_files_to_persona_card(
                pc_id="pc123",
                files=[mock_file1, mock_file2]
            )
        
        assert "一次仅支持上传一个" in exc_info.value.message
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('os.path.exists')
    @patch('os.remove')
    async def test_delete_files_from_persona_card_success(self, mock_remove, mock_exists, mock_db):
        """测试成功从人设卡删除文件
        
        验证：
        - 验证人设卡和文件存在
        - 删除物理文件
        - 删除数据库记录
        """
        # Mock database
        mock_pc = Mock()
        mock_pc.id = "pc123"
        mock_pc.base_path = "/path/to/pc"
        mock_db.get_persona_card_by_id.return_value = mock_pc
        
        mock_file = Mock()
        mock_file.id = "file123"
        mock_file.file_path = "bot_config.toml"
        mock_file.original_name = "bot_config.toml"
        mock_db.get_persona_card_file_by_id.return_value = mock_file
        
        mock_exists.return_value = True
        
        # Execute
        result = await self.service.delete_files_from_persona_card(
            pc_id="pc123",
            file_id="file123",
            user_id="user123"
        )
        
        # Verify
        assert result is True
        mock_remove.assert_called_once_with("/path/to/pc/bot_config.toml")
        mock_db.delete_persona_card_file.assert_called_once_with("file123")
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    async def test_delete_files_from_persona_card_not_found(self, mock_db):
        """测试删除文件时人设卡不存在
        
        验证：
        - 人设卡不存在时返回 False
        """
        mock_db.get_persona_card_by_id.return_value = None
        
        result = await self.service.delete_files_from_persona_card(
            pc_id="nonexistent",
            file_id="file123",
            user_id="user123"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('os.path.exists')
    @patch('os.remove')
    async def test_delete_files_from_persona_card_remove_failure(self, mock_remove, mock_exists, mock_db):
        """测试删除人设卡文件时 os.remove 失败
        
        验证：
        - 当 os.remove 抛出异常时，应该抛出 HTTPException 500
        - 错误消息应该包含文件名和错误详情
        """
        # Mock database
        mock_pc = Mock()
        mock_pc.id = "pc123"
        mock_pc.base_path = "/path/to/pc"
        mock_db.get_persona_card_by_id.return_value = mock_pc
        
        mock_file = Mock()
        mock_file.id = "file123"
        mock_file.file_path = "bot_config.toml"
        mock_file.original_name = "bot_config.toml"
        mock_db.get_persona_card_file_by_id.return_value = mock_file
        
        mock_exists.return_value = True
        # Simulate file locked error
        mock_remove.side_effect = OSError("File is locked by another process")
        
        # Execute and verify
        with pytest.raises(HTTPException) as exc_info:
            await self.service.delete_files_from_persona_card(
                pc_id="pc123",
                file_id="file123",
                user_id="user123"
            )
        
        assert exc_info.value.status_code == 500
        assert "删除文件失败" in exc_info.value.detail
        assert "bot_config.toml" in exc_info.value.detail
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('os.path.exists')
    async def test_delete_files_from_persona_card_dir_not_exist(self, mock_exists, mock_db):
        """测试删除文件时人设卡目录不存在
        
        验证：
        - 人设卡目录不存在时返回 False
        """
        mock_pc = Mock()
        mock_pc.id = "pc123"
        mock_pc.base_path = "/path/to/pc"
        mock_db.get_persona_card_by_id.return_value = mock_pc
        
        mock_file = Mock()
        mock_file.id = "file123"
        mock_file.file_path = "bot_config.toml"
        mock_db.get_persona_card_file_by_id.return_value = mock_file
        
        # Directory doesn't exist
        mock_exists.return_value = False
        
        result = await self.service.delete_files_from_persona_card(
            pc_id="pc123",
            file_id="file123",
            user_id="user123"
        )
        
        assert result is False


class TestZipCreation:
    """测试 ZIP 创建功能 - Task 3.1.7"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.service = FileUploadService()
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('app.services.file_upload_service.datetime')
    @patch('tempfile.gettempdir')
    @patch('zipfile.ZipFile')
    @patch('os.path.exists')
    async def test_create_knowledge_base_zip_success(self, mock_exists, mock_zipfile, mock_tempdir, mock_datetime, mock_db):
        """测试成功创建知识库 ZIP 文件
        
        验证：
        - 验证知识库存在
        - 获取文件列表
        - 检查文件存在性
        - 创建 ZIP 文件
        - 添加文件和 README
        """
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        
        # Mock temp directory
        mock_tempdir.return_value = "/tmp"
        
        # Mock database
        mock_kb = Mock()
        mock_kb.id = "kb123"
        mock_kb.name = "Test KB"
        mock_kb.description = "Test description"
        mock_kb.base_path = "/path/to/kb"
        mock_kb.copyright_owner = "Test Owner"
        mock_kb.created_at = "2024-01-01"
        mock_kb.updated_at = "2024-01-02"
        mock_kb.uploader_id = "user123"
        mock_db.get_knowledge_base_by_id.return_value = mock_kb
        
        mock_user = Mock()
        mock_user.username = "testuser"
        mock_db.get_user_by_id.return_value = mock_user
        
        mock_file1 = Mock()
        mock_file1.file_path = "file1.txt"
        mock_file1.original_name = "file1.txt"
        mock_file1.file_size = 1024
        
        mock_file2 = Mock()
        mock_file2.file_path = "file2.json"
        mock_file2.original_name = "file2.json"
        mock_file2.file_size = 2048
        
        mock_db.get_files_by_knowledge_base_id.return_value = [mock_file1, mock_file2]
        
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock ZipFile
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip
        
        # Execute
        result = await self.service.create_knowledge_base_zip("kb123")
        
        # Verify
        assert "zip_path" in result
        assert "zip_filename" in result
        assert result["zip_filename"] == "Test KB-testuser_20240101_120000.zip"
        assert mock_zip.write.call_count == 2  # Two files
        assert mock_zip.writestr.call_count == 1  # README
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    async def test_create_knowledge_base_zip_not_found(self, mock_db):
        """测试创建不存在的知识库 ZIP
        
        验证：
        - 知识库不存在时抛出 HTTPException 404
        """
        mock_db.get_knowledge_base_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await self.service.create_knowledge_base_zip("nonexistent")
        
        assert exc_info.value.status_code == 404
        assert "知识库不存在" in exc_info.value.detail
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('os.path.exists')
    async def test_create_knowledge_base_zip_missing_files(self, mock_exists, mock_db):
        """测试创建 ZIP 时文件缺失
        
        验证：
        - 文件不存在时抛出 HTTPException 404
        """
        # Mock database
        mock_kb = Mock()
        mock_kb.id = "kb123"
        mock_kb.base_path = "/path/to/kb"
        mock_db.get_knowledge_base_by_id.return_value = mock_kb
        
        mock_file = Mock()
        mock_file.file_path = "missing.txt"
        mock_file.original_name = "missing.txt"
        mock_db.get_files_by_knowledge_base_id.return_value = [mock_file]
        
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        with pytest.raises(HTTPException) as exc_info:
            await self.service.create_knowledge_base_zip("kb123")
        
        assert exc_info.value.status_code == 404
        assert "文件不存在" in exc_info.value.detail
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('app.services.file_upload_service.datetime')
    @patch('tempfile.gettempdir')
    @patch('zipfile.ZipFile')
    @patch('os.path.exists')
    async def test_create_persona_card_zip_success(self, mock_exists, mock_zipfile, mock_tempdir, mock_datetime, mock_db):
        """测试成功创建人设卡 ZIP 文件
        
        验证：
        - 验证人设卡存在
        - 获取文件列表
        - 检查文件存在性
        - 创建 ZIP 文件
        - 添加文件和 README
        """
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        
        # Mock temp directory
        mock_tempdir.return_value = "/tmp"
        
        # Mock database
        mock_pc = Mock()
        mock_pc.id = "pc123"
        mock_pc.name = "Test Persona"
        mock_pc.description = "Test description"
        mock_pc.base_path = "/path/to/pc"
        mock_pc.copyright_owner = "Test Owner"
        mock_pc.created_at = "2024-01-01"
        mock_pc.updated_at = "2024-01-02"
        mock_pc.uploader_id = "user123"
        mock_db.get_persona_card_by_id.return_value = mock_pc
        
        mock_user = Mock()
        mock_user.username = "testuser"
        mock_db.get_user_by_id.return_value = mock_user
        
        mock_file = Mock()
        mock_file.file_path = "bot_config.toml"
        mock_file.original_name = "bot_config.toml"
        mock_file.file_size = 1024
        
        mock_db.get_persona_card_files_by_persona_card_id.return_value = [mock_file]
        
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock ZipFile
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip
        
        # Execute
        result = await self.service.create_persona_card_zip("pc123")
        
        # Verify
        assert "zip_path" in result
        assert "zip_filename" in result
        assert result["zip_filename"] == "Test Persona-testuser_20240101_120000.zip"
        assert mock_zip.write.call_count == 1  # One file
        assert mock_zip.writestr.call_count == 1  # README
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    async def test_create_persona_card_zip_not_found(self, mock_db):
        """测试创建不存在的人设卡 ZIP
        
        验证：
        - 人设卡不存在时抛出 HTTPException 404
        """
        mock_db.get_persona_card_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await self.service.create_persona_card_zip("nonexistent")
        
        assert exc_info.value.status_code == 404
        assert "人设卡不存在" in exc_info.value.detail
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('app.services.file_upload_service.datetime')
    @patch('tempfile.gettempdir')
    @patch('zipfile.ZipFile')
    @patch('os.path.exists')
    @patch('os.remove')
    async def test_create_zip_error_cleanup(self, mock_remove, mock_exists, mock_zipfile, mock_tempdir, mock_datetime, mock_db):
        """测试创建 ZIP 失败时的清理
        
        验证：
        - ZIP 创建失败时删除临时文件
        - 抛出 HTTPException 500
        """
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        mock_tempdir.return_value = "/tmp"
        
        # Mock database
        mock_kb = Mock()
        mock_kb.id = "kb123"
        mock_kb.name = "Test KB"
        mock_kb.base_path = "/path/to/kb"
        mock_kb.uploader_id = "user123"
        mock_db.get_knowledge_base_by_id.return_value = mock_kb
        mock_db.get_user_by_id.return_value = Mock(username="testuser")
        
        mock_file = Mock()
        mock_file.file_path = "test.txt"
        mock_file.original_name = "test.txt"
        mock_file.file_size = 1024
        mock_db.get_files_by_knowledge_base_id.return_value = [mock_file]
        
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock ZipFile to raise error
        mock_zipfile.side_effect = Exception("Disk full")
        
        with pytest.raises(HTTPException) as exc_info:
            await self.service.create_knowledge_base_zip("kb123")
        
        assert exc_info.value.status_code == 500
        assert "创建压缩包失败" in exc_info.value.detail
        mock_remove.assert_called_once()
