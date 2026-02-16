import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database_models import Base, sqlite_db_manager
from models import UserCreate
from user_management import UserManager

# 创建测试客户端
client = TestClient(app)

class TestAuthentication:
    """认证相关测试（按当前后端接口设计）"""

    def test_register_user_success(self, test_db):
        """测试成功注册用户"""
        unique_suffix = str(uuid.uuid4())
        email = f"newuser_{unique_suffix}@example.com"
        username = f"newuser_{unique_suffix}"
        sqlite_db_manager.save_verification_code(email, "123456")
        response = client.post(
            "/api/user/register",
            data={
                "username": username,
                "email": email,
                "password": "password123",
                "verification_code": "123456"
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "注册成功"
        assert data["data"] is None
    
    def test_register_user_duplicate_username(self, test_user, test_db):
        """测试注册重复用户名"""
        response = client.post(
            "/api/user/register",
            data={
                "username": test_user.username,
                "email": "another@example.com",
                "password": "password123",
                "verification_code": "123456"
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "用户名已存在" in data["error"]["message"]
    
    def test_register_user_duplicate_email(self, test_user, test_db):
        """测试注册重复邮箱"""
        response = client.post(
            "/api/user/register",
            data={
                "username": "anotheruser",
                "email": test_user.email,
                "password": "password123",
                "verification_code": "123456"
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "该邮箱已被注册" in data["error"]["message"]
    
    def test_login_success(self, test_user, test_db):
        """测试成功登录"""
        response = client.post(
            "/api/token",
            data={"username": test_user.username, "password": "testpassword123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
    
    def test_login_invalid_username(self, test_db):
        """测试无效用户名登录"""
        response = client.post(
            "/api/token",
            data={"username": "nonexistent", "password": "password123"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "用户名或密码错误" in data["error"]["message"]
    
    def test_login_invalid_password(self, test_user, test_db):
        """测试无效密码登录"""
        response = client.post(
            "/api/token",
            data={"username": test_user.username, "password": "wrongpassword"}
        )

        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "用户名或密码错误" in data["error"]["message"]
    
    def test_get_current_user(self, authenticated_client, test_user, test_db):
        """测试获取当前用户信息"""
        response = authenticated_client.get("/api/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        user = data["data"]
        assert user["username"] == test_user.username
        assert user["email"] == test_user.email
    
    def test_get_current_user_unauthorized(self, test_db):
        """测试未授权获取当前用户信息"""
        response = client.get("/api/users/me")

        assert response.status_code == 401
        body = response.json()
        # 当前实现返回默认未认证错误
        assert body.get("detail") == "Not authenticated"
