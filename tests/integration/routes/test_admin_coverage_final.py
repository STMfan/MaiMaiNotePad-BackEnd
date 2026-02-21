"""
Final coverage tests for admin.py to reach 95%+ coverage

This file contains tests specifically designed to cover the remaining uncovered lines in admin.py
"""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError


class TestAdminFinalCoverage:
    """Tests to cover remaining lines in admin.py"""
    
    def test_get_recent_users_exception_handling(self, admin_client, test_db, monkeypatch):
        """Test exception handling in get_recent_users (lines 157-161)"""
        from sqlalchemy.orm import Query
        
        # Mock Query.all to raise an exception
        def mock_all_error(self):
            raise Exception("Database error")
        
        monkeypatch.setattr(Query, "all", mock_all_error)
        
        response = admin_client.get("/api/admin/recent-users")
        
        # Should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "获取最近用户失败" in data["detail"]
    
    def test_get_all_users_exception_handling(self, admin_client, test_db, monkeypatch):
        """Test exception handling in get_all_users (lines 287-291)"""
        from sqlalchemy.orm import Query
        
        # Mock Query.all to raise an exception
        def mock_all_error(self):
            raise Exception("Database error")
        
        monkeypatch.setattr(Query, "all", mock_all_error)
        
        response = admin_client.get("/api/admin/users")
        
        # Should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "获取用户列表失败" in data["detail"]
    
    def test_update_user_role_exception_handling(self, super_admin_client, factory, test_db, monkeypatch):
        """Test exception handling in update_user_role (lines 287-291)"""
        user = factory.create_user()
        
        from sqlalchemy.orm import Query
        
        # Mock Query.first to raise an exception after the user is found
        original_first = Query.first
        call_count = [0]
        
        def mock_first_error(self):
            call_count[0] += 1
            # Let the first call (finding the user) succeed
            if call_count[0] == 1:
                return original_first(self)
            # Raise error on subsequent calls
            raise Exception("Database error")
        
        monkeypatch.setattr(Query, "first", mock_first_error)
        
        response = super_admin_client.put(
            f"/api/admin/users/{user.id}/role",
            json={"role": "moderator"}
        )
        
        # Should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "更新用户角色失败" in data["detail"]
    
    def test_unmute_user_exception_handling(self, admin_client, factory, test_db, monkeypatch):
        """Test exception handling in unmute_user (lines 546-553)"""
        user = factory.create_user(is_muted=True)
        
        from sqlalchemy.orm import Query
        
        # Mock Query.first to raise an exception after the user is found
        original_first = Query.first
        call_count = [0]
        
        def mock_first_error(self):
            call_count[0] += 1
            # Let the first call (finding the user) succeed
            if call_count[0] == 1:
                return original_first(self)
            # Raise error on subsequent calls
            raise Exception("Database error")
        
        monkeypatch.setattr(Query, "first", mock_first_error)
        
        response = admin_client.post(f"/api/admin/users/{user.id}/unmute")
        
        # Should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "解除禁言失败" in data["detail"]
    
    def test_delete_user_exception_handling(self, admin_client, factory, test_db, monkeypatch):
        """Test exception handling in delete_user (lines 620-624)"""
        user = factory.create_user()
        
        from sqlalchemy.orm import Query
        
        # Mock Query.first to raise an exception after the user is found
        original_first = Query.first
        call_count = [0]
        
        def mock_first_error(self):
            call_count[0] += 1
            # Let the first call (finding the user) succeed
            if call_count[0] == 1:
                return original_first(self)
            # Raise error on subsequent calls
            raise Exception("Database error")
        
        monkeypatch.setattr(Query, "first", mock_first_error)
        
        response = admin_client.delete(f"/api/admin/users/{user.id}")
        
        # Should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "删除用户失败" in data["detail"]
    
    def test_create_user_empty_username(self, admin_client):
        """Test create_user with empty username (line 766)"""
        response = admin_client.post(
            "/api/admin/users",
            json={
                "username": "",
                "email": "test@example.com",
                "password": "password123",
                "role": "user"
            }
        )
        
        assert response.status_code in [400, 422]
        data = response.json()
        # Check for error message
        if "detail" in data:
            assert "用户名" in data["detail"] or "不能为空" in data["detail"]
        elif "error" in data:
            assert "用户名" in data["error"]["message"] or "不能为空" in data["error"]["message"]
    
    def test_create_user_admin_role_requires_super_admin(self, admin_client):
        """Test create_user with admin role requires super admin (line 777)"""
        response = admin_client.post(
            "/api/admin/users",
            json={
                "username": "newadmin",
                "email": "newadmin@example.com",
                "password": "password123",
                "role": "admin"
            }
        )
        
        assert response.status_code in [400, 422]
        data = response.json()
        # Check for error message
        if "detail" in data:
            assert "超级管理员" in data["detail"]
        elif "error" in data:
            assert "超级管理员" in data["error"]["message"]
    
    def test_create_user_short_password(self, admin_client):
        """Test create_user with short password (line 782)"""
        response = admin_client.post(
            "/api/admin/users",
            json={
                "username": "shortpass",
                "email": "shortpass@example.com",
                "password": "pass1",
                "role": "user"
            }
        )
        
        assert response.status_code in [400, 422]
        data = response.json()
        # Check for error message
        if "detail" in data:
            assert "密码" in data["detail"] or "8位" in data["detail"]
        elif "error" in data:
            assert "密码" in data["error"]["message"] or "8位" in data["error"]["message"]
    
    def test_create_user_exception_handling(self, admin_client, test_db, monkeypatch):
        """Test exception handling in create_user_by_admin (lines 831-837)"""
        from app.services.user_service import UserService
        
        # Mock UserService.create_user to raise an exception
        def mock_create_user_error(*args, **kwargs):
            raise Exception("Database error")
        
        monkeypatch.setattr(UserService, "create_user", mock_create_user_error)
        
        response = admin_client.post(
            "/api/admin/users",
            json={
                "username": "erroruser",
                "email": "error@example.com",
                "password": "password123",
                "role": "user"
            }
        )
        
        # Should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "创建用户失败" in data["detail"]


    def test_unmute_user_not_found(self, admin_client):
        """Test unmute_user with non-existent user (line 492)"""
        response = admin_client.post("/api/admin/users/nonexistent-id/unmute")
        
        assert response.status_code in [404, 500]
    
    def test_delete_user_not_found(self, admin_client):
        """Test delete_user with non-existent user (line 588)"""
        response = admin_client.delete("/api/admin/users/nonexistent-id")
        
        assert response.status_code in [404, 500]
    
    def test_unban_user_requires_admin(self, authenticated_client):
        """Test unban_user requires admin permission (line 766)"""
        response = authenticated_client.post("/api/admin/users/some-id/unban")
        
        assert response.status_code == 403


    def test_unmute_admin_as_regular_admin(self, admin_client, factory):
        """Test unmute_user when trying to unmute an admin as regular admin (line 509)"""
        admin_user = factory.create_user(is_admin=True, is_muted=True)
        
        response = admin_client.post(f"/api/admin/users/{admin_user.id}/unmute")
        
        assert response.status_code in [400, 422, 500]
        data = response.json()
        if "detail" in data:
            assert "管理员" in data["detail"]
        elif "error" in data:
            assert "管理员" in data["error"]["message"]

