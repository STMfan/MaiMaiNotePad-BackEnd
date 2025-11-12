import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from io import BytesIO

from main import app
from database_models import Base

# 创建测试客户端
client = TestClient(app)

class TestKnowledgeBase:
    """知识库相关测试"""
    
    def test_upload_knowledge_success(self, authenticated_client, test_db):
        """测试成功上传知识库"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"这是一个测试知识库文件内容")
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, "rb") as f:
                response = authenticated_client.post(
                    "/api/knowledge/upload",
                    files={"file": ("test.txt", f, "text/plain")},
                    data={"name": "测试知识库", "description": "测试描述", "is_public": "true"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "测试知识库"
            assert data["description"] == "测试描述"
            assert data["is_public"] == True
            assert "id" in data
        finally:
            os.unlink(tmp_path)
    
    def test_upload_knowledge_no_file(self, authenticated_client, test_db):
        """测试没有文件上传知识库"""
        response = authenticated_client.post(
            "/api/knowledge/upload",
            data={"name": "测试知识库", "description": "测试描述", "is_public": "true"}
        )
        
        assert response.status_code == 400
        assert "没有上传文件" in response.json()["detail"]
    
    def test_upload_knowledge_invalid_file_type(self, authenticated_client, test_db):
        """测试上传无效文件类型"""
        # 创建临时exe文件
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
            tmp.write(b"fake exe content")
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, "rb") as f:
                response = authenticated_client.post(
                    "/api/knowledge/upload",
                    files={"file": ("test.exe", f, "application/octet-stream")},
                    data={"name": "测试知识库", "description": "测试描述", "is_public": "true"}
                )
            
            assert response.status_code == 400
            assert "不支持的文件类型" in response.json()["detail"]
        finally:
            os.unlink(tmp_path)
    
    def test_get_public_knowledge_bases(self, test_db):
        """测试获取公开知识库列表"""
        response = client.get("/api/knowledge/public")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_knowledge_by_id(self, test_db):
        """测试根据ID获取知识库"""
        # 首先创建一个知识库
        user_manager = UserManager()
        user = user_manager.get_user_by_username("testuser")
        
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"测试内容")
            tmp_path = tmp.name
        
        try:
            # 直接通过数据库管理器创建知识库
            from database_models import DatabaseManager
            db_manager = DatabaseManager()
            kb = db_manager.create_knowledge_base(
                user_id=user.id,
                name="测试知识库",
                description="测试描述",
                file_path=tmp_path,
                is_public=True
            )
            
            # 测试获取知识库
            response = client.get(f"/api/knowledge/{kb.id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "测试知识库"
            assert data["description"] == "测试描述"
        finally:
            os.unlink(tmp_path)
    
    def test_get_knowledge_by_id_not_found(self, test_db):
        """测试获取不存在的知识库"""
        response = client.get("/api/knowledge/nonexistent_id")
        
        assert response.status_code == 404
        assert "知识库不存在" in response.json()["detail"]
    
    def test_get_user_knowledge_bases(self, authenticated_client, test_user, test_db):
        """测试获取用户的知识库列表"""
        response = authenticated_client.get(f"/api/knowledge/user/{test_user.id}")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_star_knowledge_base(self, authenticated_client, test_db):
        """测试Star知识库"""
        # 首先创建一个知识库
        user_manager = UserManager()
        user = user_manager.get_user_by_username("testuser")
        
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"测试内容")
            tmp_path = tmp.name
        
        try:
            # 直接通过数据库管理器创建知识库
            from database_models import DatabaseManager
            db_manager = DatabaseManager()
            kb = db_manager.create_knowledge_base(
                user_id=user.id,
                name="测试知识库",
                description="测试描述",
                file_path=tmp_path,
                is_public=True
            )
            
            # 测试Star知识库
            response = authenticated_client.post(f"/api/star/knowledge/{kb.id}")
            
            assert response.status_code == 200
            assert "Star成功" in response.json()["message"]
        finally:
            os.unlink(tmp_path)
    
    def test_unstar_knowledge_base(self, authenticated_client, test_db):
        """测试取消Star知识库"""
        # 首先创建一个知识库并Star它
        user_manager = UserManager()
        user = user_manager.get_user_by_username("testuser")
        
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"测试内容")
            tmp_path = tmp.name
        
        try:
            # 直接通过数据库管理器创建知识库
            from database_models import DatabaseManager
            db_manager = DatabaseManager()
            kb = db_manager.create_knowledge_base(
                user_id=user.id,
                name="测试知识库",
                description="测试描述",
                file_path=tmp_path,
                is_public=True
            )
            
            # Star知识库
            db_manager.add_star(user.id, kb.id, "knowledge")
            
            # 测试取消Star知识库
            response = authenticated_client.delete(f"/api/star/knowledge/{kb.id}")
            
            assert response.status_code == 200
            assert "取消Star成功" in response.json()["message"]
        finally:
            os.unlink(tmp_path)
    
    def test_get_user_stars(self, authenticated_client, test_user, test_db):
        """测试获取用户的Star记录"""
        response = authenticated_client.get("/api/stars/user")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)