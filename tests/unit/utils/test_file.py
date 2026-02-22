"""
app/utils/file.py 单元测试

测试文件工具函数，包括验证、保存和删除。
"""

import os
import pytest
from unittest.mock import Mock, AsyncMock, patch
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


class TestValidateFileType:
    """Tests for validate_file_type function"""

    def test_valid_file_type(self):
        """Test validation passes for allowed file types"""
        file = Mock(spec=UploadFile)
        file.filename = "document.txt"

        result = validate_file_type(file, [".txt", ".json"])
        assert result is True

    def test_invalid_file_type(self):
        """Test validation fails for disallowed file types"""
        file = Mock(spec=UploadFile)
        file.filename = "document.exe"

        result = validate_file_type(file, [".txt", ".json"])
        assert result is False

    def test_case_insensitive_extension(self):
        """Test file extension validation is case-insensitive"""
        file = Mock(spec=UploadFile)
        file.filename = "document.TXT"

        result = validate_file_type(file, [".txt"])
        assert result is True

    def test_no_filename(self):
        """Test validation fails when filename is None or empty"""
        file = Mock(spec=UploadFile)
        file.filename = None

        result = validate_file_type(file, [".txt"])
        assert result is False

        file.filename = ""
        result = validate_file_type(file, [".txt"])
        assert result is False

    def test_multiple_allowed_types(self):
        """Test validation with multiple allowed file types"""
        file = Mock(spec=UploadFile)
        file.filename = "data.json"

        result = validate_file_type(file, [".txt", ".json", ".csv", ".xml"])
        assert result is True


class TestValidateFileSize:
    """Tests for validate_file_size function"""

    def test_file_within_size_limit(self):
        """Test validation passes when file is within size limit"""
        file = Mock(spec=UploadFile)
        file.size = 5 * 1024 * 1024  # 5MB

        result = validate_file_size(file, 10 * 1024 * 1024)  # 10MB limit
        assert result is True

    def test_file_exceeds_size_limit(self):
        """Test validation fails when file exceeds size limit"""
        file = Mock(spec=UploadFile)
        file.size = 15 * 1024 * 1024  # 15MB

        result = validate_file_size(file, 10 * 1024 * 1024)  # 10MB limit
        assert result is False

    def test_file_exactly_at_limit(self):
        """Test validation passes when file is exactly at size limit"""
        file = Mock(spec=UploadFile)
        file.size = 10 * 1024 * 1024  # 10MB

        result = validate_file_size(file, 10 * 1024 * 1024)  # 10MB limit
        assert result is True

    def test_no_size_attribute(self):
        """Test validation passes when file size is None (cannot determine)"""
        file = Mock(spec=UploadFile)
        file.size = None

        result = validate_file_size(file, 10 * 1024 * 1024)
        assert result is True

    def test_zero_size_file(self):
        """Test validation passes for zero-size files"""
        file = Mock(spec=UploadFile)
        file.size = 0

        result = validate_file_size(file, 10 * 1024 * 1024)
        assert result is True


class TestValidateFileContentSize:
    """Tests for validate_file_content_size async function"""

    @pytest.mark.asyncio
    async def test_content_within_size_limit(self):
        """Test validation passes when content is within size limit"""
        content = b"Hello World" * 100
        file = Mock(spec=UploadFile)
        file.read = AsyncMock(return_value=content)
        file.seek = AsyncMock()

        result = await validate_file_content_size(file, 10 * 1024)
        assert result is True
        file.seek.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_content_exceeds_size_limit(self):
        """Test validation fails when content exceeds size limit"""
        content = b"X" * (11 * 1024)  # 11KB
        file = Mock(spec=UploadFile)
        file.read = AsyncMock(return_value=content)
        file.seek = AsyncMock()

        result = await validate_file_content_size(file, 10 * 1024)  # 10KB limit
        assert result is False
        file.seek.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_file_pointer_reset(self):
        """Test file pointer is reset to beginning after reading"""
        content = b"test content"
        file = Mock(spec=UploadFile)
        file.read = AsyncMock(return_value=content)
        file.seek = AsyncMock()

        await validate_file_content_size(file, 1024)

        # Verify seek was called to reset pointer
        file.seek.assert_called_once_with(0)


class TestSaveUploadedFile:
    """Tests for save_uploaded_file async function"""

    @pytest.mark.asyncio
    async def test_successful_file_save(self, tmp_path):
        """Test file is saved successfully with timestamp prefix"""
        target_dir = str(tmp_path)
        content = b"test file content"

        file = Mock(spec=UploadFile)
        file.filename = "test.txt"
        file.read = AsyncMock(return_value=content)

        with patch("app.utils.file.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"

            file_path = await save_uploaded_file(file, target_dir)

            assert file_path.startswith(target_dir)
            assert "20240101_120000_test.txt" in file_path
            assert os.path.exists(file_path)

            # Verify content
            with open(file_path, "rb") as f:
                assert f.read() == content

    @pytest.mark.asyncio
    async def test_save_file_exception_handling(self):
        """Test HTTPException is raised when file save fails"""
        file = Mock(spec=UploadFile)
        file.filename = "test.txt"
        file.read = AsyncMock(side_effect=Exception("Read error"))

        with pytest.raises(HTTPException) as exc_info:
            await save_uploaded_file(file, "/invalid/path")

        assert exc_info.value.status_code == 500
        assert "文件保存失败" in exc_info.value.detail


class TestSaveUploadedFileWithSize:
    """Tests for save_uploaded_file_with_size async function"""

    @pytest.mark.asyncio
    async def test_save_file_returns_path_and_size(self, tmp_path):
        """Test file is saved and returns path and size"""
        target_dir = str(tmp_path)
        content = b"test content with some data"

        file = Mock(spec=UploadFile)
        file.filename = "document.txt"
        file.read = AsyncMock(return_value=content)

        file_path, file_size = await save_uploaded_file_with_size(file, target_dir)

        assert os.path.exists(file_path)
        assert file_size == len(content)
        assert "document.txt" in file_path

    @pytest.mark.asyncio
    async def test_save_file_creates_directory(self, tmp_path):
        """Test directory is created if it doesn't exist"""
        target_dir = str(tmp_path / "new_dir" / "nested")
        content = b"test"

        file = Mock(spec=UploadFile)
        file.filename = "test.txt"
        file.read = AsyncMock(return_value=content)

        file_path, _ = await save_uploaded_file_with_size(file, target_dir)

        assert os.path.exists(target_dir)
        assert os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_save_file_handles_existing_file(self, tmp_path):
        """Test timestamp is added when file already exists"""
        target_dir = str(tmp_path)
        content = b"test"

        # Create existing file
        existing_file = tmp_path / "existing.txt"
        existing_file.write_bytes(b"old content")

        file = Mock(spec=UploadFile)
        file.filename = "existing.txt"
        file.read = AsyncMock(return_value=content)

        with patch("app.utils.file.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"

            file_path, _ = await save_uploaded_file_with_size(file, target_dir)

            # Should have timestamp in filename
            assert "existing_20240101_120000.txt" in file_path
            assert os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_save_file_with_size_exception(self):
        """Test HTTPException is raised on save failure"""
        file = Mock(spec=UploadFile)
        file.filename = "test.txt"
        file.read = AsyncMock(side_effect=Exception("IO error"))

        with pytest.raises(HTTPException) as exc_info:
            await save_uploaded_file_with_size(file, "/invalid/path")

        assert exc_info.value.status_code == 500
        assert "文件保存失败" in exc_info.value.detail


class TestEnsureDirectoryExists:
    """Tests for ensure_directory_exists function"""

    def test_creates_new_directory(self, tmp_path):
        """Test creates directory when it doesn't exist"""
        new_dir = tmp_path / "new_directory"

        ensure_directory_exists(str(new_dir))

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_creates_nested_directories(self, tmp_path):
        """Test creates nested directory structure"""
        nested_dir = tmp_path / "level1" / "level2" / "level3"

        ensure_directory_exists(str(nested_dir))

        assert nested_dir.exists()
        assert nested_dir.is_dir()

    def test_does_not_fail_if_exists(self, tmp_path):
        """Test does not raise error if directory already exists"""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        # Should not raise exception
        ensure_directory_exists(str(existing_dir))

        assert existing_dir.exists()


class TestDeleteFile:
    """Tests for delete_file function"""

    def test_deletes_existing_file(self, tmp_path):
        """Test successfully deletes existing file"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = delete_file(str(test_file))

        assert result is True
        assert not test_file.exists()

    def test_returns_false_for_nonexistent_file(self, tmp_path):
        """Test returns False when file doesn't exist"""
        nonexistent = tmp_path / "nonexistent.txt"

        result = delete_file(str(nonexistent))

        assert result is False

    def test_returns_false_for_none_path(self):
        """Test returns False when path is None"""
        result = delete_file(None)
        assert result is False

    def test_returns_false_for_empty_path(self):
        """Test returns False when path is empty string"""
        result = delete_file("")
        assert result is False

    def test_handles_deletion_exception(self, tmp_path):
        """Test handles exception during deletion gracefully"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with patch("os.remove", side_effect=PermissionError("Access denied")):
            result = delete_file(str(test_file))
            assert result is False


class TestGetFileExtension:
    """Tests for get_file_extension function"""

    def test_returns_lowercase_extension(self):
        """Test returns extension in lowercase"""
        assert get_file_extension("document.TXT") == ".txt"
        assert get_file_extension("image.PNG") == ".png"

    def test_handles_multiple_dots(self):
        """Test handles filenames with multiple dots"""
        assert get_file_extension("archive.tar.gz") == ".gz"
        assert get_file_extension("my.file.name.txt") == ".txt"

    def test_handles_no_extension(self):
        """Test handles filenames without extension"""
        assert get_file_extension("README") == ""
        assert get_file_extension("Makefile") == ""

    def test_handles_hidden_files(self):
        """Test handles hidden files (starting with dot)"""
        assert get_file_extension(".gitignore") == ""
        assert get_file_extension(".env.local") == ".local"


class TestGenerateUniqueFilename:
    """Tests for generate_unique_filename function"""

    def test_generates_filename_with_timestamp(self):
        """Test generates filename with timestamp"""
        with patch("app.utils.file.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"

            result = generate_unique_filename("document.txt")

            assert result == "20240101_120000_document.txt"

    def test_generates_filename_with_prefix(self):
        """Test generates filename with prefix and timestamp"""
        with patch("app.utils.file.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"

            result = generate_unique_filename("document.txt", "user123")

            assert result == "user123_20240101_120000_document.txt"

    def test_generates_filename_without_prefix(self):
        """Test generates filename without prefix when empty string provided"""
        with patch("app.utils.file.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"

            result = generate_unique_filename("document.txt", "")

            assert result == "20240101_120000_document.txt"

    def test_preserves_original_filename(self):
        """Test preserves original filename structure"""
        with patch("app.utils.file.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"

            result = generate_unique_filename("my.complex.file.name.txt", "prefix")

            assert "my.complex.file.name.txt" in result
            assert result.startswith("prefix_20240101_120000_")
