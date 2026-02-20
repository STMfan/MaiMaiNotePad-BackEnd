"""
字典路由集成测试
测试翻译字典检索和错误处理

需求: 3.7
"""

import pytest
import json
import os
from unittest.mock import patch, mock_open, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestGetTranslationDictionary:
    """测试 GET /api/dictionary/translation 端点"""
    
    def test_get_translation_dictionary_success(self, test_db: Session):
        """测试成功检索翻译字典
        
        验证：
        - 返回 200 状态码
        - 返回包含 blocks 和 tokens 的数据
        - 数据格式正确
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/api/dictionary/translation")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "blocks" in data["data"]
        assert "tokens" in data["data"]
        assert isinstance(data["data"]["blocks"], dict)
        assert isinstance(data["data"]["tokens"], dict)
    
    def test_get_translation_dictionary_content(self, test_db: Session):
        """测试翻译字典包含预期内容
        
        验证：
        - blocks 包含预期的翻译条目
        - tokens 包含预期的翻译条目
        - 翻译内容正确
        """
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/api/dictionary/translation")
        
        assert response.status_code == 200
        data = response.json()["data"]
        
        # Verify some expected translations exist
        blocks = data["blocks"]
        tokens = data["tokens"]
        
        # Check if common translations exist
        assert "bot" in blocks or "bot" in tokens
        assert "personality" in blocks or "personality" in tokens
    
    @patch('app.api.routes.dictionary.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_translation_dictionary_file_not_found(
        self, mock_file, mock_exists, test_db: Session
    ):
        """测试文件不存在时的翻译字典
        
        验证：
        - 文件不存在时返回空字典
        - 返回 200 状态码
        - 返回默认结构（空 blocks 和 tokens）
        """
        from app.main import app
        client = TestClient(app)
        
        # Mock file not existing
        mock_exists.return_value = False
        
        response = client.get("/api/dictionary/translation")
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data == {"blocks": {}, "tokens": {}}
    
    @patch('app.api.routes.dictionary.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    def test_get_translation_dictionary_invalid_json(
        self, mock_file, mock_exists, test_db: Session
    ):
        """测试包含无效 JSON 的翻译字典
        
        验证：
        - JSON 解析失败时返回空字典
        - 返回 200 状态码
        - 返回默认结构
        """
        from app.main import app
        client = TestClient(app)
        
        # Mock file exists but contains invalid JSON
        mock_exists.return_value = True
        
        response = client.get("/api/dictionary/translation")
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data == {"blocks": {}, "tokens": {}}
    
    @patch('app.api.routes.dictionary.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_translation_dictionary_missing_blocks(
        self, mock_file, mock_exists, test_db: Session
    ):
        """测试缺少 blocks 字段的翻译字典
        
        验证：
        - 缺少 blocks 字段时使用空字典
        - tokens 字段正常返回
        """
        from app.main import app
        client = TestClient(app)
        
        # Mock file with missing blocks
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps({
            "tokens": {"test": "测试"}
        })
        
        response = client.get("/api/dictionary/translation")
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["blocks"] == {}
        assert data["tokens"] == {"test": "测试"}
    
    @patch('app.api.routes.dictionary.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_translation_dictionary_missing_tokens(
        self, mock_file, mock_exists, test_db: Session
    ):
        """测试缺少 tokens 字段的翻译字典
        
        验证：
        - 缺少 tokens 字段时使用空字典
        - blocks 字段正常返回
        """
        from app.main import app
        client = TestClient(app)
        
        # Mock file with missing tokens
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps({
            "blocks": {"test": "测试"}
        })
        
        response = client.get("/api/dictionary/translation")
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["blocks"] == {"test": "测试"}
        assert data["tokens"] == {}
    
    @patch('app.api.routes.dictionary.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_translation_dictionary_invalid_blocks_type(
        self, mock_file, mock_exists, test_db: Session
    ):
        """测试 blocks 类型无效的翻译字典
        
        验证：
        - blocks 不是字典时使用空字典
        - 系统不会崩溃
        """
        from app.main import app
        client = TestClient(app)
        
        # Mock file with invalid blocks type (array instead of dict)
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps({
            "blocks": ["not", "a", "dict"],
            "tokens": {"test": "测试"}
        })
        
        response = client.get("/api/dictionary/translation")
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["blocks"] == {}
        assert data["tokens"] == {"test": "测试"}
    
    @patch('app.api.routes.dictionary.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_translation_dictionary_invalid_tokens_type(
        self, mock_file, mock_exists, test_db: Session
    ):
        """测试 tokens 类型无效的翻译字典
        
        验证：
        - tokens 不是字典时使用空字典
        - 系统不会崩溃
        """
        from app.main import app
        client = TestClient(app)
        
        # Mock file with invalid tokens type
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps({
            "blocks": {"test": "测试"},
            "tokens": "not a dict"
        })
        
        response = client.get("/api/dictionary/translation")
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["blocks"] == {"test": "测试"}
        assert data["tokens"] == {}
    
    @patch('app.api.routes.dictionary.os.path.exists')
    @patch('builtins.open')
    def test_get_translation_dictionary_file_read_error(
        self, mock_file, mock_exists, test_db: Session
    ):
        """测试文件读取失败时的翻译字典
        
        验证：
        - 文件读取失败时返回空字典
        - 系统不会崩溃
        - 返回 200 状态码
        """
        from app.main import app
        client = TestClient(app)
        
        # Mock file exists but read fails
        mock_exists.return_value = True
        mock_file.side_effect = IOError("File read error")
        
        response = client.get("/api/dictionary/translation")
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data == {"blocks": {}, "tokens": {}}


class TestDictionaryPermissions:
    """测试字典端点权限"""
    
    def test_get_translation_dictionary_no_auth_required(self, test_db: Session):
        """测试翻译字典不需要身份验证
        
        验证：
        - 未认证用户可以访问
        - 返回正常数据
        """
        from app.main import app
        client = TestClient(app)
        
        # Access without authentication
        response = client.get("/api/dictionary/translation")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "blocks" in data["data"]
        assert "tokens" in data["data"]
