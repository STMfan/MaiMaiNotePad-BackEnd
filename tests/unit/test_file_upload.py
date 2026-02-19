"""
Unit tests for file upload functionality
Tests file type validation, size validation, storage, and error handling
"""

import pytest
import os
import tempfile
import shutil
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import UploadFile, HTTPException
from datetime import datetime

from app.file_upload import FileUploadService


class TestFileTypeValidation:
    """Test file type validation for allowed and disallowed types"""
    
    def test_validate_knowledge_file_type_txt_allowed(self):
        """Test that .txt files are allowed for knowledge bases"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.txt"
        
        result = service._validate_file_type(mock_file, service.ALLOWED_KNOWLEDGE_TYPES)
        
        assert result is True
    
    def test_validate_knowledge_file_type_json_allowed(self):
        """Test that .json files are allowed for knowledge bases"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.json"
        
        result = service._validate_file_type(mock_file, service.ALLOWED_KNOWLEDGE_TYPES)
        
        assert result is True
    
    def test_validate_knowledge_file_type_pdf_rejected(self):
        """Test that .pdf files are rejected for knowledge bases"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        
        result = service._validate_file_type(mock_file, service.ALLOWED_KNOWLEDGE_TYPES)
        
        assert result is False
    
    def test_validate_knowledge_file_type_exe_rejected(self):
        """Test that .exe files are rejected for knowledge bases"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "malware.exe"
        
        result = service._validate_file_type(mock_file, service.ALLOWED_KNOWLEDGE_TYPES)
        
        assert result is False
    
    def test_validate_persona_file_type_toml_allowed(self):
        """Test that .toml files are allowed for persona cards"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "bot_config.toml"
        
        result = service._validate_file_type(mock_file, service.ALLOWED_PERSONA_TYPES)
        
        assert result is True
    
    def test_validate_persona_file_type_txt_rejected(self):
        """Test that .txt files are rejected for persona cards"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "config.txt"
        
        result = service._validate_file_type(mock_file, service.ALLOWED_PERSONA_TYPES)
        
        assert result is False
    
    def test_validate_file_type_no_extension(self):
        """Test that files without extension are rejected"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "noextension"
        
        result = service._validate_file_type(mock_file, service.ALLOWED_KNOWLEDGE_TYPES)
        
        assert result is False
    
    def test_validate_file_type_empty_filename(self):
        """Test that empty filename is rejected"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = ""
        
        result = service._validate_file_type(mock_file, service.ALLOWED_KNOWLEDGE_TYPES)
        
        assert result is False
    
    def test_validate_file_type_none_filename(self):
        """Test that None filename is rejected"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = None
        
        result = service._validate_file_type(mock_file, service.ALLOWED_KNOWLEDGE_TYPES)
        
        assert result is False
    
    def test_validate_file_type_case_insensitive(self):
        """Test that file type validation is case insensitive"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.TXT"
        
        result = service._validate_file_type(mock_file, service.ALLOWED_KNOWLEDGE_TYPES)
        
        assert result is True


class TestFileSizeValidation:
    """Test file size validation within and over limits"""
    
    def test_validate_file_size_within_limit(self):
        """Test that files within size limit are accepted"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.size = 1024 * 1024  # 1 MB
        
        result = service._validate_file_size(mock_file)
        
        assert result is True
    
    def test_validate_file_size_at_limit(self):
        """Test that files at exact size limit are accepted"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.size = service.MAX_FILE_SIZE
        
        result = service._validate_file_size(mock_file)
        
        assert result is True
    
    def test_validate_file_size_over_limit(self):
        """Test that files over size limit are rejected"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.size = service.MAX_FILE_SIZE + 1
        
        result = service._validate_file_size(mock_file)
        
        assert result is False
    
    def test_validate_file_size_zero(self):
        """Test that zero-size files are accepted (edge case)"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.size = 0
        
        result = service._validate_file_size(mock_file)
        
        assert result is True
    
    def test_validate_file_size_none(self):
        """Test that files with no size info are accepted (fallback)"""
        service = FileUploadService()
        mock_file = Mock(spec=UploadFile)
        mock_file.size = None
        
        result = service._validate_file_size(mock_file)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_file_content_within_limit(self):
        """Test that file content within size limit is accepted"""
        service = FileUploadService()
        content = b"x" * (1024 * 1024)  # 1 MB
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=content)
        mock_file.seek = AsyncMock()
        
        result = await service._validate_file_content(mock_file)
        
        assert result is True
        mock_file.seek.assert_called_once_with(0)
    
    @pytest.mark.asyncio
    async def test_validate_file_content_over_limit(self):
        """Test that file content over size limit is rejected"""
        service = FileUploadService()
        content = b"x" * (service.MAX_FILE_SIZE + 1)
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=content)
        mock_file.seek = AsyncMock()
        
        result = await service._validate_file_content(mock_file)
        
        assert result is False
        mock_file.seek.assert_called_once_with(0)


class TestFileStorage:
    """Test file storage operations including save, filename generation, and path construction"""
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_creates_unique_filename(self):
        """Test that saved files get unique timestamped filenames"""
        service = FileUploadService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            content = b"test content"
            mock_file = AsyncMock(spec=UploadFile)
            mock_file.filename = "test.txt"
            mock_file.read = AsyncMock(return_value=content)
            
            file_path = await service._save_uploaded_file(mock_file, temp_dir)
            
            assert os.path.exists(file_path)
            assert "test.txt" in file_path
            assert temp_dir in file_path
            
            # Verify content
            with open(file_path, "rb") as f:
                saved_content = f.read()
            assert saved_content == content
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_with_size_returns_path_and_size(self):
        """Test that _save_uploaded_file_with_size returns both path and size"""
        service = FileUploadService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            content = b"test content"
            mock_file = AsyncMock(spec=UploadFile)
            mock_file.filename = "test.txt"
            mock_file.read = AsyncMock(return_value=content)
            
            file_path, file_size = await service._save_uploaded_file_with_size(mock_file, temp_dir)
            
            assert os.path.exists(file_path)
            assert file_size == len(content)
            assert file_size == 12  # "test content" is 12 bytes
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_handles_duplicate_names(self):
        """Test that duplicate filenames get timestamped to avoid conflicts"""
        service = FileUploadService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create first file
            first_file = os.path.join(temp_dir, "test.txt")
            with open(first_file, "w") as f:
                f.write("first")
            
            # Try to save second file with same name
            content = b"second"
            mock_file = AsyncMock(spec=UploadFile)
            mock_file.filename = "test.txt"
            mock_file.read = AsyncMock(return_value=content)
            
            file_path, file_size = await service._save_uploaded_file_with_size(mock_file, temp_dir)
            
            # Should create a different file
            assert file_path != first_file
            assert os.path.exists(file_path)
            assert "test" in os.path.basename(file_path)
            assert ".txt" in os.path.basename(file_path)
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_creates_directory_if_not_exists(self):
        """Test that save operation creates directory if it doesn't exist"""
        service = FileUploadService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = os.path.join(temp_dir, "nested", "path")
            
            content = b"test"
            mock_file = AsyncMock(spec=UploadFile)
            mock_file.filename = "test.txt"
            mock_file.read = AsyncMock(return_value=content)
            
            file_path, file_size = await service._save_uploaded_file_with_size(mock_file, nested_dir)
            
            assert os.path.exists(nested_dir)
            assert os.path.exists(file_path)
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_sanitizes_filename(self):
        """Test that filenames are sanitized for security"""
        service = FileUploadService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            content = b"test"
            mock_file = AsyncMock(spec=UploadFile)
            mock_file.filename = "../../../etc/passwd"
            mock_file.read = AsyncMock(return_value=content)
            
            file_path, file_size = await service._save_uploaded_file_with_size(mock_file, temp_dir)
            
            # Should not escape the temp directory
            assert temp_dir in file_path
            assert "/etc/passwd" not in file_path
    
    def test_file_upload_service_initializes_directories(self):
        """Test that FileUploadService creates necessary directories on init"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"UPLOAD_DIR": temp_dir}):
                service = FileUploadService()
                
                assert os.path.exists(service.upload_dir)
                assert os.path.exists(service.knowledge_dir)
                assert os.path.exists(service.persona_dir)
    
    def test_file_upload_service_handles_relative_paths(self):
        """Test that FileUploadService handles relative paths correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            relative_path = "test_uploads"
            with patch.dict(os.environ, {"UPLOAD_DIR": relative_path}):
                service = FileUploadService()
                
                # Should prepend ./ to relative paths
                assert service.upload_dir.startswith("./") or service.upload_dir.startswith("/")


class TestFileErrorHandling:
    """Test error handling for corrupted files, missing files, permission errors, and disk space errors"""
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_handles_read_error(self):
        """Test handling of file read errors"""
        service = FileUploadService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = AsyncMock(spec=UploadFile)
            mock_file.filename = "test.txt"
            mock_file.read = AsyncMock(side_effect=Exception("Read error"))
            
            with pytest.raises(HTTPException) as exc_info:
                await service._save_uploaded_file(mock_file, temp_dir)
            
            assert exc_info.value.status_code == 500
            assert "文件保存失败" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_handles_write_error(self):
        """Test handling of file write errors (permission denied)"""
        service = FileUploadService()
        
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.read = AsyncMock(return_value=b"test")
        
        # Use a path that will cause write error
        invalid_path = "/root/no_permission"
        
        with pytest.raises(HTTPException) as exc_info:
            await service._save_uploaded_file(mock_file, invalid_path)
        
        assert exc_info.value.status_code == 500
        assert "文件保存失败" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_with_size_handles_errors(self):
        """Test that _save_uploaded_file_with_size handles errors properly"""
        service = FileUploadService()
        
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.read = AsyncMock(side_effect=IOError("Disk full"))
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(HTTPException) as exc_info:
                await service._save_uploaded_file_with_size(mock_file, temp_dir)
            
            assert exc_info.value.status_code == 500
            assert "文件保存失败" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_validate_file_content_handles_corrupted_file(self):
        """Test handling of corrupted files during content validation"""
        service = FileUploadService()
        
        mock_file = AsyncMock(spec=UploadFile)
        mock_file.read = AsyncMock(side_effect=Exception("Corrupted file"))
        
        with pytest.raises(Exception) as exc_info:
            await service._validate_file_content(mock_file)
        
        assert "Corrupted file" in str(exc_info.value)
    
    def test_create_metadata_file_handles_write_error(self):
        """Test handling of metadata file creation errors"""
        service = FileUploadService()
        
        metadata = {"test": "data"}
        invalid_path = "/root/no_permission"
        
        with pytest.raises(HTTPException) as exc_info:
            service._create_metadata_file(metadata, invalid_path, "test")
        
        assert exc_info.value.status_code == 500
        assert "元数据文件创建失败" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_save_file_handles_disk_space_error(self):
        """Test handling of disk space errors during file save"""
        service = FileUploadService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = AsyncMock(spec=UploadFile)
            mock_file.filename = "test.txt"
            mock_file.read = AsyncMock(return_value=b"test")
            
            # Mock open to raise disk space error
            with patch("builtins.open", side_effect=OSError(28, "No space left on device")):
                with pytest.raises(HTTPException) as exc_info:
                    await service._save_uploaded_file(mock_file, temp_dir)
                
                assert exc_info.value.status_code == 500
                assert "文件保存失败" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_save_file_handles_missing_directory(self):
        """Test that save creates missing directories instead of failing"""
        service = FileUploadService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use a non-existent nested directory
            missing_dir = os.path.join(temp_dir, "missing", "nested", "path")
            
            mock_file = AsyncMock(spec=UploadFile)
            mock_file.filename = "test.txt"
            mock_file.read = AsyncMock(return_value=b"test")
            
            # Should create the directory and save successfully
            file_path, file_size = await service._save_uploaded_file_with_size(mock_file, missing_dir)
            
            assert os.path.exists(file_path)
            assert os.path.exists(missing_dir)
    
    @pytest.mark.asyncio
    async def test_save_file_handles_empty_content(self):
        """Test handling of empty file content"""
        service = FileUploadService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file = AsyncMock(spec=UploadFile)
            mock_file.filename = "empty.txt"
            mock_file.read = AsyncMock(return_value=b"")
            
            file_path, file_size = await service._save_uploaded_file_with_size(mock_file, temp_dir)
            
            assert os.path.exists(file_path)
            assert file_size == 0
    
    def test_extract_version_from_toml_handles_invalid_data(self):
        """Test that version extraction handles invalid TOML data"""
        service = FileUploadService()
        
        # Test with non-dict data
        result = service._extract_version_from_toml("not a dict")
        assert result is None
        
        # Test with empty dict
        result = service._extract_version_from_toml({})
        assert result is None
        
        # Test with dict without version
        result = service._extract_version_from_toml({"name": "test", "description": "test"})
        assert result is None
    
    def test_extract_version_from_toml_finds_version(self):
        """Test that version extraction finds version in various locations"""
        service = FileUploadService()
        
        # Test direct version field
        result = service._extract_version_from_toml({"version": "1.0.0"})
        assert result == "1.0.0"
        
        # Test nested in meta
        result = service._extract_version_from_toml({"meta": {"version": "2.0.0"}})
        assert result == "2.0.0"
        
        # Test schema_version
        result = service._extract_version_from_toml({"schema_version": "3.0.0"})
        assert result == "3.0.0"
        
        # Test numeric version
        result = service._extract_version_from_toml({"version": 1.5})
        assert result == "1.5"
