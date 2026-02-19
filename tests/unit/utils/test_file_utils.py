"""
Unit tests for file utility functions

Tests file type detection, size calculation, async operations,
directory creation, and filename sanitization.
"""

import os
import pytest
from io import BytesIO
from fastapi import UploadFile, HTTPException
from app.utils.file import (
    validate_file_type,
    validate_file_size,
    validate_file_content_size,
    save_uploaded_file,
    save_uploaded_file_with_size,
    ensure_directory_exists,
    delete_file,
    get_file_extension,
    generate_unique_filename,
)


class TestFileTypeDetection:
    """Test file type validation"""
    
    def test_validate_file_type_allowed(self):
        """Test file type validation with allowed types"""
        file = UploadFile(filename="test.txt", file=BytesIO(b"content"))
        assert validate_file_type(file, ['.txt', '.json']) is True
    
    def test_validate_file_type_disallowed(self):
        """Test file type validation with disallowed types"""
        file = UploadFile(filename="test.exe", file=BytesIO(b"content"))
        assert validate_file_type(file, ['.txt', '.json']) is False
    
    def test_validate_file_type_case_insensitive(self):
        """Test file type validation is case insensitive"""
        file = UploadFile(filename="test.TXT", file=BytesIO(b"content"))
        assert validate_file_type(file, ['.txt', '.json']) is True
    
    def test_validate_file_type_no_filename(self):
        """Test file type validation with no filename"""
        file = UploadFile(filename=None, file=BytesIO(b"content"))
        assert validate_file_type(file, ['.txt', '.json']) is False
    
    def test_validate_file_type_empty_filename(self):
        """Test file type validation with empty filename"""
        file = UploadFile(filename="", file=BytesIO(b"content"))
        assert validate_file_type(file, ['.txt', '.json']) is False


class TestFileSizeCalculation:
    """Test file size validation"""
    
    def test_validate_file_size_within_limit(self):
        """Test file size validation within limit"""
        file = UploadFile(filename="test.txt", file=BytesIO(b"content"))
        file.size = 1024  # 1KB
        assert validate_file_size(file, 10 * 1024) is True  # 10KB limit
    
    def test_validate_file_size_exceeds_limit(self):
        """Test file size validation exceeding limit"""
        file = UploadFile(filename="test.txt", file=BytesIO(b"content"))
        file.size = 20 * 1024  # 20KB
        assert validate_file_size(file, 10 * 1024) is False  # 10KB limit
    
    def test_validate_file_size_exact_limit(self):
        """Test file size validation at exact limit"""
        file = UploadFile(filename="test.txt", file=BytesIO(b"content"))
        file.size = 10 * 1024  # 10KB
        assert validate_file_size(file, 10 * 1024) is True  # 10KB limit
    
    def test_validate_file_size_no_size(self):
        """Test file size validation with no size attribute"""
        file = UploadFile(filename="test.txt", file=BytesIO(b"content"))
        file.size = None
        assert validate_file_size(file, 10 * 1024) is True  # Allow if size unknown
    
    @pytest.mark.asyncio
    async def test_validate_file_content_size_within_limit(self):
        """Test file content size validation within limit"""
        content = b"Hello World"
        file = UploadFile(filename="test.txt", file=BytesIO(content))
        assert await validate_file_content_size(file, 1024) is True
    
    @pytest.mark.asyncio
    async def test_validate_file_content_size_exceeds_limit(self):
        """Test file content size validation exceeding limit"""
        content = b"x" * 2000
        file = UploadFile(filename="test.txt", file=BytesIO(content))
        assert await validate_file_content_size(file, 1024) is False
    
    @pytest.mark.asyncio
    async def test_validate_file_content_size_resets_pointer(self):
        """Test that file pointer is reset after validation"""
        content = b"Hello World"
        file = UploadFile(filename="test.txt", file=BytesIO(content))
        await validate_file_content_size(file, 1024)
        # Read again to verify pointer was reset
        data = await file.read()
        assert data == content


class TestAsyncFileOperations:
    """Test async file save and read operations"""
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file(self, tmp_path):
        """Test saving uploaded file"""
        content = b"Test content"
        file = UploadFile(filename="test.txt", file=BytesIO(content))
        
        target_dir = str(tmp_path / "uploads")
        os.makedirs(target_dir, exist_ok=True)
        
        file_path = await save_uploaded_file(file, target_dir)
        
        assert os.path.exists(file_path)
        assert file_path.startswith(target_dir)
        assert "test.txt" in file_path
        
        # Verify content
        with open(file_path, "rb") as f:
            assert f.read() == content
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_with_timestamp(self, tmp_path):
        """Test that saved file has timestamp prefix"""
        content = b"Test content"
        file = UploadFile(filename="test.txt", file=BytesIO(content))
        
        target_dir = str(tmp_path / "uploads")
        os.makedirs(target_dir, exist_ok=True)
        
        file_path = await save_uploaded_file(file, target_dir)
        filename = os.path.basename(file_path)
        
        # Should have timestamp prefix (YYYYMMDD_HHMMSS_)
        assert len(filename.split("_")) >= 3
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_error_handling(self, tmp_path):
        """Test error handling when file save fails"""
        content = b"Test content"
        file = UploadFile(filename="test.txt", file=BytesIO(content))
        
        # Use invalid directory path
        invalid_dir = "/invalid/path/that/does/not/exist"
        
        with pytest.raises(HTTPException) as exc_info:
            await save_uploaded_file(file, invalid_dir)
        
        assert exc_info.value.status_code == 500
        assert "文件保存失败" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_with_size(self, tmp_path):
        """Test saving file and getting size"""
        content = b"Test content with some data"
        file = UploadFile(filename="test.txt", file=BytesIO(content))
        
        target_dir = str(tmp_path / "uploads")
        
        file_path, file_size = await save_uploaded_file_with_size(file, target_dir)
        
        assert os.path.exists(file_path)
        assert file_size == len(content)
        
        # Verify actual file size matches
        assert os.path.getsize(file_path) == file_size
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_with_size_creates_directory(self, tmp_path):
        """Test that directory is created if it doesn't exist"""
        content = b"Test content"
        file = UploadFile(filename="test.txt", file=BytesIO(content))
        
        target_dir = str(tmp_path / "new" / "nested" / "directory")
        
        file_path, file_size = await save_uploaded_file_with_size(file, target_dir)
        
        assert os.path.exists(target_dir)
        assert os.path.exists(file_path)
    
    @pytest.mark.asyncio
    async def test_save_uploaded_file_with_size_handles_duplicates(self, tmp_path):
        """Test that duplicate filenames get timestamp suffix"""
        content1 = b"First file"
        content2 = b"Second file"
        file1 = UploadFile(filename="test.txt", file=BytesIO(content1))
        file2 = UploadFile(filename="test.txt", file=BytesIO(content2))
        
        target_dir = str(tmp_path / "uploads")
        
        path1, _ = await save_uploaded_file_with_size(file1, target_dir)
        path2, _ = await save_uploaded_file_with_size(file2, target_dir)
        
        # Paths should be different
        assert path1 != path2
        assert os.path.exists(path1)
        assert os.path.exists(path2)


class TestDirectoryCreation:
    """Test directory management"""
    
    def test_ensure_directory_exists_creates_new(self, tmp_path):
        """Test creating new directory"""
        new_dir = str(tmp_path / "new_directory")
        assert not os.path.exists(new_dir)
        
        ensure_directory_exists(new_dir)
        
        assert os.path.exists(new_dir)
        assert os.path.isdir(new_dir)
    
    def test_ensure_directory_exists_already_exists(self, tmp_path):
        """Test with existing directory"""
        existing_dir = str(tmp_path / "existing")
        os.makedirs(existing_dir)
        
        # Should not raise error
        ensure_directory_exists(existing_dir)
        
        assert os.path.exists(existing_dir)
    
    def test_ensure_directory_exists_nested(self, tmp_path):
        """Test creating nested directories"""
        nested_dir = str(tmp_path / "level1" / "level2" / "level3")
        
        ensure_directory_exists(nested_dir)
        
        assert os.path.exists(nested_dir)
        assert os.path.isdir(nested_dir)


class TestFilenameSanitization:
    """Test filename generation and sanitization"""
    
    def test_get_file_extension(self):
        """Test getting file extension"""
        assert get_file_extension("document.txt") == ".txt"
        assert get_file_extension("image.PNG") == ".png"
        assert get_file_extension("archive.tar.gz") == ".gz"
    
    def test_get_file_extension_no_extension(self):
        """Test file with no extension"""
        assert get_file_extension("README") == ""
    
    def test_get_file_extension_hidden_file(self):
        """Test hidden file (Unix-style)"""
        assert get_file_extension(".gitignore") == ""
    
    def test_generate_unique_filename_no_prefix(self):
        """Test generating unique filename without prefix"""
        filename = generate_unique_filename("document.txt")
        
        assert "document.txt" in filename
        # Should have timestamp (YYYYMMDD_HHMMSS_)
        parts = filename.split("_")
        assert len(parts) >= 3
    
    def test_generate_unique_filename_with_prefix(self):
        """Test generating unique filename with prefix"""
        filename = generate_unique_filename("document.txt", prefix="user123")
        
        assert "user123" in filename
        assert "document.txt" in filename
        # Should have format: prefix_timestamp_filename
        assert filename.startswith("user123_")
    
    def test_generate_unique_filename_multiple_calls_different(self):
        """Test that multiple calls generate different filenames"""
        import time
        
        filename1 = generate_unique_filename("test.txt")
        time.sleep(1.1)  # Wait to ensure different timestamp
        filename2 = generate_unique_filename("test.txt")
        
        assert filename1 != filename2


class TestFileDeletion:
    """Test file deletion"""
    
    def test_delete_file_existing(self, tmp_path):
        """Test deleting existing file"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        assert test_file.exists()
        result = delete_file(str(test_file))
        
        assert result is True
        assert not test_file.exists()
    
    def test_delete_file_nonexistent(self, tmp_path):
        """Test deleting non-existent file"""
        test_file = tmp_path / "nonexistent.txt"
        
        result = delete_file(str(test_file))
        
        assert result is False
    
    def test_delete_file_empty_path(self):
        """Test deleting with empty path"""
        result = delete_file("")
        assert result is False
    
    def test_delete_file_none_path(self):
        """Test deleting with None path"""
        result = delete_file(None)
        assert result is False
