"""
单元测试: FileUploadService 文件读取失败场景

测试 app/file_upload.py 中的文件读取失败处理

Task: 6.2.3 测试文件读取失败
Requirements: FR5 - 文件上传边界测试
"""
import os
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, mock_open
from fastapi import UploadFile

# Inject sqlite_db_manager mock into app.services.file_upload_service module before importing
import app.services.file_upload_service
if not hasattr(app.services.file_upload_service, 'sqlite_db_manager'):
    app.services.file_upload_service.sqlite_db_manager = Mock()

from app.services.file_upload_service import FileUploadService
from app.core.error_handlers import ValidationError


class TestFileReadFailures:
    """测试文件读取失败场景 - Task 6.2.3"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.service = FileUploadService()
    
    @pytest.mark.asyncio
    @patch('os.makedirs')
    @patch('builtins.open', create=True)
    async def test_upload_persona_card_file_read_permission_error(self, mock_file_open, mock_makedirs):
        """测试上传人设卡时文件读取权限错误
        
        验证：
        - 文件保存成功但读取失败时抛出 ValidationError
        - 错误消息指示 TOML 解析错误
        - 目录被清理
        """
        # Mock file operations - save succeeds but read fails
        mock_file_open.side_effect = PermissionError("Permission denied")
        
        # Create mock file
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"version = '1.0.0'")
        mock_file.size = 1024
        
        # Mock file saving
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/bot_config.toml", 1024)
            
            with patch('os.path.exists', return_value=True):
                with patch('shutil.rmtree') as mock_rmtree:
                    with pytest.raises(ValidationError) as exc_info:
                        await self.service.upload_persona_card(
                            files=[mock_file],
                            name="Test Persona",
                            description="Test description",
                            uploader_id="user123",
                            copyright_owner="Test Owner"
                        )
        
        # Verify error handling
        assert "TOML 语法错误" in exc_info.value.message or "配置解析失败" in exc_info.value.message
        assert exc_info.value.details["code"] == "PERSONA_TOML_PARSE_ERROR"
        # Verify cleanup was called
        mock_rmtree.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('os.makedirs')
    @patch('builtins.open', create=True)
    async def test_upload_persona_card_file_read_io_error(self, mock_file_open, mock_makedirs):
        """测试上传人设卡时文件读取 IO 错误
        
        验证：
        - 文件读取 IO 错误时抛出 ValidationError
        - 错误消息正确
        - 目录被清理
        """
        # Mock file read IO error
        mock_file_open.side_effect = IOError("Disk read error")
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"version = '1.0.0'")
        mock_file.size = 1024
        
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/bot_config.toml", 1024)
            
            with patch('os.path.exists', return_value=True):
                with patch('shutil.rmtree') as mock_rmtree:
                    with pytest.raises(ValidationError) as exc_info:
                        await self.service.upload_persona_card(
                            files=[mock_file],
                            name="Test Persona",
                            description="Test",
                            uploader_id="user123",
                            copyright_owner="Owner"
                        )
        
        assert "TOML 语法错误" in exc_info.value.message or "配置解析失败" in exc_info.value.message
        mock_rmtree.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('os.makedirs')
    @patch('builtins.open', create=True)
    async def test_upload_persona_card_file_read_unicode_decode_error(self, mock_file_open, mock_makedirs):
        """测试上传人设卡时文件读取 Unicode 解码错误
        
        验证：
        - Unicode 解码错误时抛出 ValidationError
        - 错误消息正确
        """
        # Mock Unicode decode error
        mock_file_open.side_effect = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"\xff\xfe invalid utf-8")
        mock_file.size = 1024
        
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/bot_config.toml", 1024)
            
            with patch('os.path.exists', return_value=True):
                with patch('shutil.rmtree'):
                    with pytest.raises(ValidationError) as exc_info:
                        await self.service.upload_persona_card(
                            files=[mock_file],
                            name="Test",
                            description="Test",
                            uploader_id="user123",
                            copyright_owner="Owner"
                        )
        
        assert "TOML 语法错误" in exc_info.value.message or "配置解析失败" in exc_info.value.message
    
    @pytest.mark.asyncio
    @patch('os.makedirs')
    @patch('builtins.open', create=True)
    async def test_upload_persona_card_file_not_found_after_save(self, mock_file_open, mock_makedirs):
        """测试上传人设卡后文件被意外删除
        
        验证：
        - 文件保存后被删除导致读取失败
        - 抛出 ValidationError
        """
        # Mock file not found error
        mock_file_open.side_effect = FileNotFoundError("File not found")
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"version = '1.0.0'")
        mock_file.size = 1024
        
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/bot_config.toml", 1024)
            
            with patch('os.path.exists', return_value=True):
                with patch('shutil.rmtree'):
                    with pytest.raises(ValidationError) as exc_info:
                        await self.service.upload_persona_card(
                            files=[mock_file],
                            name="Test",
                            description="Test",
                            uploader_id="user123",
                            copyright_owner="Owner"
                        )
        
        assert "TOML 语法错误" in exc_info.value.message or "配置解析失败" in exc_info.value.message
    
    @pytest.mark.asyncio
    @patch('os.makedirs')
    @patch('builtins.open', create=True)
    async def test_upload_persona_card_file_corrupted(self, mock_file_open, mock_makedirs):
        """测试上传人设卡时文件损坏
        
        验证：
        - 文件损坏导致读取失败
        - 抛出 ValidationError
        """
        # Mock file handle that raises error on read
        mock_file_handle = MagicMock()
        mock_file_handle.read.side_effect = OSError("File corrupted")
        mock_file_open.return_value.__enter__.return_value = mock_file_handle
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"version = '1.0.0'")
        mock_file.size = 1024
        
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/bot_config.toml", 1024)
            
            with patch('os.path.exists', return_value=True):
                with patch('shutil.rmtree'):
                    with pytest.raises(ValidationError) as exc_info:
                        await self.service.upload_persona_card(
                            files=[mock_file],
                            name="Test",
                            description="Test",
                            uploader_id="user123",
                            copyright_owner="Owner"
                        )
        
        assert "TOML 语法错误" in exc_info.value.message or "配置解析失败" in exc_info.value.message
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    async def test_add_files_to_persona_card_file_read_permission_error(self, mock_exists, mock_file_open, mock_db):
        """测试向人设卡添加文件时读取权限错误
        
        验证：
        - 文件读取权限错误时抛出 ValidationError
        - 新保存的文件被清理
        """
        # Mock database
        mock_pc = Mock()
        mock_pc.id = "pc123"
        mock_pc.base_path = "/path/to/pc"
        mock_db.get_persona_card_by_id.return_value = mock_pc
        mock_db.get_files_by_persona_card_id.return_value = []
        
        mock_exists.return_value = True
        
        # Mock file read permission error
        mock_file_open.side_effect = PermissionError("Permission denied")
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"version = '2.0.0'")
        mock_file.size = 1024
        
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/pc/bot_config.toml", 1024)
            
            with patch('os.remove') as mock_remove:
                with pytest.raises(ValidationError) as exc_info:
                    await self.service.add_files_to_persona_card(
                        pc_id="pc123",
                        files=[mock_file]
                    )
        
        # Verify error and cleanup
        assert "TOML 语法错误" in exc_info.value.message or "配置解析失败" in exc_info.value.message
        mock_remove.assert_called_once_with("/path/to/pc/bot_config.toml")
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    async def test_add_files_to_persona_card_file_read_io_error(self, mock_exists, mock_file_open, mock_db):
        """测试向人设卡添加文件时 IO 错误
        
        验证：
        - IO 错误时抛出 ValidationError
        - 新文件被清理
        """
        mock_pc = Mock()
        mock_pc.id = "pc123"
        mock_pc.base_path = "/path/to/pc"
        mock_db.get_persona_card_by_id.return_value = mock_pc
        mock_db.get_files_by_persona_card_id.return_value = []
        
        mock_exists.return_value = True
        mock_file_open.side_effect = IOError("Disk error")
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"version = '2.0.0'")
        mock_file.size = 1024
        
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/pc/bot_config.toml", 1024)
            
            with patch('os.remove') as mock_remove:
                with pytest.raises(ValidationError) as exc_info:
                    await self.service.add_files_to_persona_card(
                        pc_id="pc123",
                        files=[mock_file]
                    )
        
        assert "TOML 语法错误" in exc_info.value.message or "配置解析失败" in exc_info.value.message
        mock_remove.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    async def test_add_files_to_persona_card_file_not_found(self, mock_exists, mock_file_open, mock_db):
        """测试向人设卡添加文件时文件未找到
        
        验证：
        - 文件未找到错误时抛出 ValidationError
        """
        mock_pc = Mock()
        mock_pc.id = "pc123"
        mock_pc.base_path = "/path/to/pc"
        mock_db.get_persona_card_by_id.return_value = mock_pc
        mock_db.get_files_by_persona_card_id.return_value = []
        
        mock_exists.return_value = True
        mock_file_open.side_effect = FileNotFoundError("File not found")
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"version = '2.0.0'")
        mock_file.size = 1024
        
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/pc/bot_config.toml", 1024)
            
            with patch('os.remove'):
                with pytest.raises(ValidationError) as exc_info:
                    await self.service.add_files_to_persona_card(
                        pc_id="pc123",
                        files=[mock_file]
                    )
        
        assert "TOML 语法错误" in exc_info.value.message or "配置解析失败" in exc_info.value.message
    
    @pytest.mark.asyncio
    @patch('app.services.file_upload_service.sqlite_db_manager')
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    async def test_add_files_to_persona_card_file_read_timeout(self, mock_exists, mock_file_open, mock_db):
        """测试向人设卡添加文件时读取超时
        
        验证：
        - 读取超时错误时抛出 ValidationError
        """
        mock_pc = Mock()
        mock_pc.id = "pc123"
        mock_pc.base_path = "/path/to/pc"
        mock_db.get_persona_card_by_id.return_value = mock_pc
        mock_db.get_files_by_persona_card_id.return_value = []
        
        mock_exists.return_value = True
        mock_file_open.side_effect = TimeoutError("Read timeout")
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"version = '2.0.0'")
        mock_file.size = 1024
        
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/pc/bot_config.toml", 1024)
            
            with patch('os.remove'):
                with pytest.raises(ValidationError) as exc_info:
                    await self.service.add_files_to_persona_card(
                        pc_id="pc123",
                        files=[mock_file]
                    )
        
        assert "TOML 语法错误" in exc_info.value.message or "配置解析失败" in exc_info.value.message
    
    @pytest.mark.asyncio
    @patch('os.makedirs')
    @patch('builtins.open', create=True)
    async def test_upload_persona_card_file_read_memory_error(self, mock_file_open, mock_makedirs):
        """测试上传人设卡时内存不足错误
        
        验证：
        - 内存不足错误时抛出 ValidationError
        - 目录被清理
        """
        mock_file_open.side_effect = MemoryError("Out of memory")
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"version = '1.0.0'")
        mock_file.size = 1024
        
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/bot_config.toml", 1024)
            
            with patch('os.path.exists', return_value=True):
                with patch('shutil.rmtree'):
                    with pytest.raises(ValidationError) as exc_info:
                        await self.service.upload_persona_card(
                            files=[mock_file],
                            name="Test",
                            description="Test",
                            uploader_id="user123",
                            copyright_owner="Owner"
                        )
        
        assert "TOML 语法错误" in exc_info.value.message or "配置解析失败" in exc_info.value.message
    
    @pytest.mark.asyncio
    @patch('os.makedirs')
    @patch('builtins.open', create=True)
    async def test_upload_persona_card_file_read_os_error(self, mock_file_open, mock_makedirs):
        """测试上传人设卡时操作系统错误
        
        验证：
        - OS 错误时抛出 ValidationError
        - 目录被清理
        """
        mock_file_open.side_effect = OSError("OS error occurred")
        
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        mock_file.read = AsyncMock(return_value=b"version = '1.0.0'")
        mock_file.size = 1024
        
        with patch.object(self.service, '_save_uploaded_file_with_size', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = ("/path/to/bot_config.toml", 1024)
            
            with patch('os.path.exists', return_value=True):
                with patch('shutil.rmtree'):
                    with pytest.raises(ValidationError) as exc_info:
                        await self.service.upload_persona_card(
                            files=[mock_file],
                            name="Test",
                            description="Test",
                            uploader_id="user123",
                            copyright_owner="Owner"
                        )
        
        assert "TOML 语法错误" in exc_info.value.message or "配置解析失败" in exc_info.value.message
