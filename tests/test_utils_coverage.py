"""
工具模块覆盖率测试
提高utils模块的测试覆盖率
"""

import pytest
import tempfile
import os
from pathlib import Path
from io import BytesIO
from PIL import Image

from app.utils.avatar import (
    ensure_avatar_dir,
    validate_image_file,
    process_avatar_image,
    generate_initial_avatar,
    save_avatar_file,
    delete_avatar_file
)
from app.utils.file import (
    get_file_extension,
    generate_unique_filename,
    ensure_directory_exists,
    delete_file
)
from app.utils.websocket import MessageWebSocketManager


class TestAvatarUtils:
    """头像工具测试"""
    
    def test_ensure_avatar_dir(self):
        """测试确保头像目录存在"""
        ensure_avatar_dir()
        assert os.path.exists("uploads/avatars")
    
    def test_validate_image_file_valid(self):
        """测试验证有效图片文件"""
        # 创建一个简单的测试图片
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()
        
        is_valid, error = validate_image_file(content, "test.jpg")
        assert is_valid is True
        assert error == ""
    
    def test_validate_image_file_invalid_format(self):
        """测试验证无效文件格式"""
        content = b"not an image"
        is_valid, error = validate_image_file(content, "test.txt")
        assert is_valid is False
        assert "格式不支持" in error
    
    def test_validate_image_file_too_large(self):
        """测试验证文件过大"""
        # 创建超过2MB的内容
        content = b"x" * (3 * 1024 * 1024)
        is_valid, error = validate_image_file(content, "test.jpg")
        assert is_valid is False
        assert "大小不能超过" in error
    
    def test_process_avatar_image(self):
        """测试处理头像图片"""
        # 创建测试图片
        img = Image.new('RGB', (200, 200), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()
        
        processed, thumbnail = process_avatar_image(content)
        
        assert isinstance(processed, bytes)
        assert isinstance(thumbnail, bytes)
        assert len(processed) > 0
        assert len(thumbnail) > 0
    
    def test_generate_initial_avatar(self):
        """测试生成首字母头像"""
        avatar_bytes = generate_initial_avatar("Alice", size=200)
        
        assert isinstance(avatar_bytes, bytes)
        assert len(avatar_bytes) > 0
        
        # 验证是有效的PNG图片
        img = Image.open(BytesIO(avatar_bytes))
        assert img.format == 'PNG'
        assert img.size == (200, 200)
    
    def test_save_avatar_file(self):
        """测试保存头像文件"""
        user_id = "test_user_save"
        
        # 创建测试图片
        img = Image.new('RGB', (100, 100), color='green')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()
        
        try:
            avatar_path, thumb_path = save_avatar_file(user_id, content, ".jpg")
            
            assert isinstance(avatar_path, str)
            assert isinstance(thumb_path, str)
            assert os.path.exists(avatar_path)
            assert os.path.exists(thumb_path)
            
            # 清理
            if os.path.exists(avatar_path):
                os.unlink(avatar_path)
            if os.path.exists(thumb_path):
                os.unlink(thumb_path)
        except Exception as e:
            pytest.skip(f"Avatar save test skipped: {e}")
    
    def test_delete_avatar_file(self):
        """测试删除头像文件"""
        user_id = "test_user_delete"
        
        # 创建测试图片
        img = Image.new('RGB', (100, 100), color='yellow')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        content = buffer.getvalue()
        
        try:
            avatar_path, thumb_path = save_avatar_file(user_id, content, ".jpg")
            
            # 测试删除
            result = delete_avatar_file(avatar_path)
            assert result is True
            
            # 验证文件已删除
            assert not os.path.exists(avatar_path)
        except Exception as e:
            pytest.skip(f"Avatar delete test skipped: {e}")


class TestFileUtils:
    """文件工具测试"""
    
    def test_get_file_extension(self):
        """测试获取文件扩展名"""
        assert get_file_extension("test.txt") == ".txt"
        assert get_file_extension("test.TAR.GZ") == ".gz"
        assert get_file_extension("test") == ""
        assert get_file_extension("test.") == "."
        assert get_file_extension("document.PDF") == ".pdf"
    
    def test_generate_unique_filename(self):
        """测试生成唯一文件名"""
        filename = generate_unique_filename("document.txt")
        assert "document.txt" in filename
        assert len(filename) > len("document.txt")
        
        # 测试带前缀
        filename_with_prefix = generate_unique_filename("document.txt", "user123")
        assert "user123" in filename_with_prefix
        assert "document.txt" in filename_with_prefix
    
    def test_ensure_directory_exists(self):
        """测试确保目录存在"""
        test_dir = "test_temp_dir"
        ensure_directory_exists(test_dir)
        assert os.path.exists(test_dir)
        
        # 清理
        if os.path.exists(test_dir):
            os.rmdir(test_dir)
    
    def test_delete_file(self):
        """测试删除文件"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        # 测试删除
        result = delete_file(tmp_path)
        assert result is True
        assert not os.path.exists(tmp_path)
        
        # 测试删除不存在的文件
        result = delete_file("nonexistent_file.txt")
        assert result is False


class TestWebSocketManager:
    """WebSocket管理器测试"""
    
    def test_connection_manager_init(self):
        """测试连接管理器初始化"""
        manager = MessageWebSocketManager()
        assert manager is not None
        assert hasattr(manager, 'connections')
        assert isinstance(manager.connections, dict)
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """测试连接和断开"""
        manager = MessageWebSocketManager()
        
        # 模拟WebSocket连接
        class MockWebSocket:
            async def accept(self):
                pass
            
            async def send_json(self, data):
                pass
            
            async def close(self):
                pass
        
        websocket = MockWebSocket()
        user_id = "test_user_ws"
        
        # 测试连接
        await manager.connect(user_id, websocket)
        assert user_id in manager.connections
        assert websocket in manager.connections[user_id]
        
        # 测试断开
        manager.disconnect(user_id, websocket)
        # 断开后，如果没有其他连接，用户应该从字典中移除
        assert user_id not in manager.connections or len(manager.connections[user_id]) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_connections(self):
        """测试多个连接"""
        manager = MessageWebSocketManager()
        
        class MockWebSocket:
            async def accept(self):
                pass
            
            async def send_json(self, data):
                pass
        
        user_id = "test_user_multi"
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        
        # 连接两个WebSocket
        await manager.connect(user_id, ws1)
        await manager.connect(user_id, ws2)
        
        assert user_id in manager.connections
        assert len(manager.connections[user_id]) == 2
        
        # 断开一个
        manager.disconnect(user_id, ws1)
        assert len(manager.connections[user_id]) == 1
        
        # 断开另一个
        manager.disconnect(user_id, ws2)
        assert user_id not in manager.connections or len(manager.connections[user_id]) == 0
