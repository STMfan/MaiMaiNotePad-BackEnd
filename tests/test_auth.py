import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database_models import Base
from models import UserCreate
from user_management import UserManager

# 创建测试客户端
client = TestClient(app)

class TestAuthentication:
    """认证相关测试"""
    
    def test_register_user_success(self, test_db):
        """测试成功注册用户"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "password" not in data
    
    def test_register_user_duplicate_username(self, test_user, test_db):
        """测试注册重复用户名"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": test_user.username,
                "email": "another@example.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 400
        assert "用户名已存在" in response.json()["detail"]
    
    def test_register_user_duplicate_email(self, test_user, test_db):
        """测试注册重复邮箱"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "anotheruser",
                "email": test_user.email,
                "password": "password123"
            }
        )
        
        assert response.status_code == 400
        assert "邮箱已存在" in response.json()["detail"]
    
    def test_login_success(self, test_user, test_db):
        """测试成功登录"""
        response = client.post(
            "/api/auth/login",
            data={"username": test_user.username, "password": "testpassword123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_username(self, test_db):
        """测试无效用户名登录"""
        response = client.post(
            "/api/auth/login",
            data={"username": "nonexistent", "password": "password123"}
        )
        
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]
    
    def test_login_invalid_password(self, test_user, test_db):
        """测试无效密码登录"""
        response = client.post(
            "/api/auth/login",
            data={"username": test_user.username, "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]
    
    def test_get_current_user(self, authenticated_client, test_user, test_db):
        """测试获取当前用户信息"""
        response = authenticated_client.get("/api/users/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
    
    def test_get_current_user_unauthorized(self, test_db):
        """测试未授权获取当前用户信息"""
        response = client.get("/api/users/me")
        
        assert response.status_code == 401
        assert "令牌验证失败" in response.json()["detail"]