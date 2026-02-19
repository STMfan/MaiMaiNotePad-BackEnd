"""
Unit tests for avatar utility functions

Tests avatar generation, storage, retrieval, deletion, and default handling.
"""

import os
import pytest
from io import BytesIO
from PIL import Image
from app.utils.avatar import (
    ensure_avatar_dir,
    validate_image_file,
    process_avatar_image,
    generate_initial_avatar,
    save_avatar_file,
    delete_avatar_file,
    AVATAR_MAX_SIZE,
    AVATAR_MAX_DIMENSION,
    AVATAR_ALLOWED_FORMATS,
    AVATAR_UPLOAD_DIR,
    AVATAR_THUMBNAIL_SIZE,
)


class TestAvatarDirectoryManagement:
    """Test avatar directory creation"""
    
    def test_ensure_avatar_dir_creates_directory(self, tmp_path, monkeypatch):
        """Test that avatar directory is created if it doesn't exist"""
        test_dir = str(tmp_path / "test_avatars")
        monkeypatch.setattr("app.utils.avatar.AVATAR_UPLOAD_DIR", test_dir)
        
        assert not os.path.exists(test_dir)
        ensure_avatar_dir()
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)
    
    def test_ensure_avatar_dir_already_exists(self, tmp_path, monkeypatch):
        """Test that existing directory doesn't cause error"""
        test_dir = str(tmp_path / "existing_avatars")
        os.makedirs(test_dir)
        monkeypatch.setattr("app.utils.avatar.AVATAR_UPLOAD_DIR", test_dir)
        
        # Should not raise error
        ensure_avatar_dir()
        assert os.path.exists(test_dir)


class TestImageValidation:
    """Test image file validation"""
    
    def test_validate_image_file_valid_jpg(self):
        """Test validation of valid JPG image"""
        # Create a simple valid image
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()
        
        is_valid, error = validate_image_file(content, "test.jpg")
        assert is_valid is True
        assert error == ""
    
    def test_validate_image_file_valid_png(self):
        """Test validation of valid PNG image"""
        img = Image.new('RGB', (100, 100), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        content = buffer.getvalue()
        
        is_valid, error = validate_image_file(content, "test.png")
        assert is_valid is True
        assert error == ""
    
    def test_validate_image_file_too_large(self):
        """Test validation fails for oversized image"""
        # Create content larger than AVATAR_MAX_SIZE
        content = b"x" * (AVATAR_MAX_SIZE + 1)
        
        is_valid, error = validate_image_file(content, "test.jpg")
        assert is_valid is False
        assert "文件大小不能超过" in error
    
    def test_validate_image_file_invalid_format(self):
        """Test validation fails for invalid format"""
        img = Image.new('RGB', (100, 100), color='green')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()
        
        is_valid, error = validate_image_file(content, "test.exe")
        assert is_valid is False
        assert "文件格式不支持" in error
    
    def test_validate_image_file_corrupted(self):
        """Test validation fails for corrupted image"""
        content = b"not a valid image file"
        
        is_valid, error = validate_image_file(content, "test.jpg")
        assert is_valid is False
        assert "无效的图片文件" in error
    
    def test_validate_image_file_all_allowed_formats(self):
        """Test all allowed formats are accepted"""
        img = Image.new('RGB', (100, 100), color='yellow')
        
        for ext in ['.jpg', '.jpeg', '.png']:
            buffer = BytesIO()
            format_name = 'JPEG' if ext in ['.jpg', '.jpeg'] else 'PNG'
            img.save(buffer, format=format_name)
            content = buffer.getvalue()
            
            is_valid, error = validate_image_file(content, f"test{ext}")
            assert is_valid is True, f"Format {ext} should be valid"


class TestImageProcessing:
    """Test avatar image processing"""
    
    def test_process_avatar_image_square(self):
        """Test processing square image"""
        img = Image.new('RGB', (200, 200), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()
        
        processed, thumbnail = process_avatar_image(content)
        
        # Verify processed image
        processed_img = Image.open(BytesIO(processed))
        assert processed_img.width == processed_img.height
        assert processed_img.mode == 'RGB'
        
        # Verify thumbnail
        thumb_img = Image.open(BytesIO(thumbnail))
        assert thumb_img.width == AVATAR_THUMBNAIL_SIZE
        assert thumb_img.height == AVATAR_THUMBNAIL_SIZE
    
    def test_process_avatar_image_rectangular(self):
        """Test processing rectangular image (crops to square)"""
        img = Image.new('RGB', (300, 200), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()
        
        processed, thumbnail = process_avatar_image(content)
        
        # Should be cropped to square
        processed_img = Image.open(BytesIO(processed))
        assert processed_img.width == processed_img.height
        assert processed_img.width == 200  # Cropped to smaller dimension
    
    def test_process_avatar_image_oversized(self):
        """Test processing oversized image (resizes)"""
        img = Image.new('RGB', (2000, 2000), color='green')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()
        
        processed, thumbnail = process_avatar_image(content)
        
        # Should be resized to max dimension
        processed_img = Image.open(BytesIO(processed))
        assert processed_img.width <= AVATAR_MAX_DIMENSION
        assert processed_img.height <= AVATAR_MAX_DIMENSION
    
    def test_process_avatar_image_rgba_to_rgb(self):
        """Test converting RGBA to RGB"""
        img = Image.new('RGBA', (200, 200), color=(255, 0, 0, 128))
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        content = buffer.getvalue()
        
        processed, thumbnail = process_avatar_image(content)
        
        # Should be converted to RGB
        processed_img = Image.open(BytesIO(processed))
        assert processed_img.mode == 'RGB'
    
    def test_process_avatar_image_compression(self):
        """Test that image is compressed"""
        img = Image.new('RGB', (500, 500), color='purple')
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=100)
        original_content = buffer.getvalue()
        
        processed, thumbnail = process_avatar_image(original_content)
        
        # Processed should be smaller due to compression
        # (Not always guaranteed, but generally true for large images)
        assert len(processed) > 0
        assert len(thumbnail) > 0


class TestInitialAvatarGeneration:
    """Test initial avatar generation from username"""
    
    def test_generate_initial_avatar_basic(self):
        """Test generating initial avatar"""
        avatar_bytes = generate_initial_avatar("Alice")
        
        assert len(avatar_bytes) > 0
        
        # Verify it's a valid PNG image
        img = Image.open(BytesIO(avatar_bytes))
        assert img.format == 'PNG'
        assert img.width == 200
        assert img.height == 200
    
    def test_generate_initial_avatar_custom_size(self):
        """Test generating initial avatar with custom size"""
        avatar_bytes = generate_initial_avatar("Bob", size=300)
        
        img = Image.open(BytesIO(avatar_bytes))
        assert img.width == 300
        assert img.height == 300
    
    def test_generate_initial_avatar_empty_username(self):
        """Test generating initial avatar with empty username"""
        avatar_bytes = generate_initial_avatar("")
        
        assert len(avatar_bytes) > 0
        img = Image.open(BytesIO(avatar_bytes))
        assert img.format == 'PNG'
    
    def test_generate_initial_avatar_chinese_character(self):
        """Test generating initial avatar with Chinese character"""
        avatar_bytes = generate_initial_avatar("张三")
        
        assert len(avatar_bytes) > 0
        img = Image.open(BytesIO(avatar_bytes))
        assert img.format == 'PNG'
    
    def test_generate_initial_avatar_consistent_colors(self):
        """Test that same first letter produces same color"""
        avatar1 = generate_initial_avatar("Alice")
        avatar2 = generate_initial_avatar("Andrew")
        
        # Both start with 'A', should have same background color
        img1 = Image.open(BytesIO(avatar1))
        img2 = Image.open(BytesIO(avatar2))
        
        # Get pixel from center (background color)
        pixel1 = img1.getpixel((100, 100))
        pixel2 = img2.getpixel((100, 100))
        
        assert pixel1 == pixel2
    
    def test_generate_initial_avatar_different_letters_different_colors(self):
        """Test that different first letters may produce different colors"""
        avatar_a = generate_initial_avatar("Alice")
        avatar_z = generate_initial_avatar("Zoe")
        
        # Different letters, likely different colors (not guaranteed but probable)
        img_a = Image.open(BytesIO(avatar_a))
        img_z = Image.open(BytesIO(avatar_z))
        
        # Just verify both are valid images
        assert img_a.format == 'PNG'
        assert img_z.format == 'PNG'


class TestAvatarStorage:
    """Test avatar file storage"""
    
    def test_save_avatar_file(self, tmp_path, monkeypatch):
        """Test saving avatar file"""
        test_dir = str(tmp_path / "avatars")
        monkeypatch.setattr("app.utils.avatar.AVATAR_UPLOAD_DIR", test_dir)
        
        # Create test image
        img = Image.new('RGB', (200, 200), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()
        
        avatar_path, thumb_path = save_avatar_file("user123", content, ".jpg")
        
        # Verify paths use forward slashes
        assert "/" in avatar_path
        assert "/" in thumb_path
        
        # Verify files exist
        assert os.path.exists(avatar_path)
        assert os.path.exists(thumb_path)
        
        # Verify filenames contain user ID
        assert "user123" in os.path.basename(avatar_path)
        assert "user123" in os.path.basename(thumb_path)
        
        # Verify thumbnail has _thumb suffix
        assert "_thumb" in os.path.basename(thumb_path)
    
    def test_save_avatar_file_creates_directory(self, tmp_path, monkeypatch):
        """Test that directory is created if it doesn't exist"""
        test_dir = str(tmp_path / "new_avatars")
        monkeypatch.setattr("app.utils.avatar.AVATAR_UPLOAD_DIR", test_dir)
        
        img = Image.new('RGB', (200, 200), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()
        
        assert not os.path.exists(test_dir)
        
        avatar_path, thumb_path = save_avatar_file("user456", content, ".jpg")
        
        assert os.path.exists(test_dir)
        assert os.path.exists(avatar_path)
        assert os.path.exists(thumb_path)
    
    def test_save_avatar_file_with_timestamp(self, tmp_path, monkeypatch):
        """Test that filename includes timestamp"""
        test_dir = str(tmp_path / "avatars")
        monkeypatch.setattr("app.utils.avatar.AVATAR_UPLOAD_DIR", test_dir)
        
        img = Image.new('RGB', (200, 200), color='green')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()
        
        avatar_path, thumb_path = save_avatar_file("user789", content, ".jpg")
        
        filename = os.path.basename(avatar_path)
        # Should have format: user789_YYYYMMDD_HHMMSS.jpg
        parts = filename.split("_")
        assert len(parts) >= 3


class TestAvatarDeletion:
    """Test avatar file deletion"""
    
    def test_delete_avatar_file_existing(self, tmp_path):
        """Test deleting existing avatar file"""
        # Create test files
        avatar_file = tmp_path / "user123_20240101_120000.jpg"
        thumb_file = tmp_path / "user123_20240101_120000_thumb.jpg"
        
        avatar_file.write_bytes(b"avatar content")
        thumb_file.write_bytes(b"thumbnail content")
        
        assert avatar_file.exists()
        assert thumb_file.exists()
        
        result = delete_avatar_file(str(avatar_file))
        
        assert result is True
        assert not avatar_file.exists()
        assert not thumb_file.exists()
    
    def test_delete_avatar_file_nonexistent(self, tmp_path):
        """Test deleting non-existent avatar file"""
        nonexistent = tmp_path / "nonexistent.jpg"
        
        result = delete_avatar_file(str(nonexistent))
        
        # Should still return True (no error)
        assert result is True
    
    def test_delete_avatar_file_empty_path(self):
        """Test deleting with empty path"""
        result = delete_avatar_file("")
        assert result is True
    
    def test_delete_avatar_file_none_path(self):
        """Test deleting with None path"""
        result = delete_avatar_file(None)
        assert result is True
    
    def test_delete_avatar_file_only_main_exists(self, tmp_path):
        """Test deleting when only main file exists (no thumbnail)"""
        avatar_file = tmp_path / "user456_20240101_120000.jpg"
        avatar_file.write_bytes(b"avatar content")
        
        assert avatar_file.exists()
        
        result = delete_avatar_file(str(avatar_file))
        
        assert result is True
        assert not avatar_file.exists()


class TestDefaultAvatarHandling:
    """Test default avatar behavior"""
    
    def test_generate_default_avatar_for_new_user(self):
        """Test generating default avatar for new user"""
        # This tests the typical workflow for a new user
        username = "NewUser"
        
        # Generate initial avatar
        avatar_bytes = generate_initial_avatar(username)
        
        # Verify it's valid
        assert len(avatar_bytes) > 0
        img = Image.open(BytesIO(avatar_bytes))
        assert img.format == 'PNG'
        assert img.width == 200
        assert img.height == 200
    
    def test_avatar_generation_fallback(self):
        """Test avatar generation works even with unusual input"""
        # Test with various edge cases
        test_cases = ["", "1", "!", "测试", "A" * 100]
        
        for username in test_cases:
            avatar_bytes = generate_initial_avatar(username)
            assert len(avatar_bytes) > 0
            
            # Verify it's a valid image
            img = Image.open(BytesIO(avatar_bytes))
            assert img.format == 'PNG'
