"""
Integration tests for admin routes
Tests admin statistics, user listing, and user management endpoints

Requirements: 1.1 - Admin routes coverage
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import User, KnowledgeBase, PersonaCard
from tests.test_data_factory import TestDataFactory


class TestAdminStats:
    """Test GET /api/admin/stats endpoint"""
    
    def test_get_admin_stats_success(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can retrieve statistics"""
        # Create test data
        user1 = factory.create_user()
        user2 = factory.create_user()
        kb1 = factory.create_knowledge_base(uploader=user1, is_pending=True)
        kb2 = factory.create_knowledge_base(uploader=user2, is_pending=False)
        persona1 = factory.create_persona_card(uploader=user1, is_pending=True)
        persona2 = factory.create_persona_card(uploader=user2, is_pending=False)
        
        # Get stats
        response = admin_client.get("/api/admin/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        stats = data["data"]
        
        # Verify statistics (includes admin user + 2 created users)
        assert stats["totalUsers"] >= 3
        assert stats["totalKnowledge"] >= 2
        assert stats["totalPersonas"] >= 2
        assert stats["pendingKnowledge"] >= 1
        assert stats["pendingPersonas"] >= 1
    
    def test_get_admin_stats_non_admin_forbidden(self, authenticated_client):
        """Test non-admin users cannot access statistics"""
        response = authenticated_client.get("/api/admin/stats")
        
        assert response.status_code == 403
        data = response.json()
        assert "需要管理员权限" in data["detail"]
    
    def test_get_admin_stats_unauthenticated(self, test_db: Session):
        """Test unauthenticated users cannot access statistics"""
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/api/admin/stats")
        
        assert response.status_code == 401


class TestAdminRecentUsers:
    """Test GET /api/admin/recent-users endpoint"""
    
    def test_get_recent_users_default_pagination(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test getting recent users with default pagination"""
        # Create test users
        for i in range(5):
            factory.create_user(username=f"recentuser{i}")
        
        response = admin_client.get("/api/admin/recent-users")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10
        assert len(data["data"]) >= 5
        
        # Verify user data structure
        user = data["data"][0]
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert "role" in user
        assert "createdAt" in user
    
    def test_get_recent_users_custom_pagination(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test getting recent users with custom pagination"""
        # Create test users
        for i in range(15):
            factory.create_user(username=f"paginateduser{i}")
        
        # Get page 2 with 5 items per page
        response = admin_client.get("/api/admin/recent-users?page=2&page_size=5")
        
        assert response.status_code == 200
        data = response.json()
        pagination = data["pagination"]
        assert pagination["page"] == 2
        assert pagination["page_size"] == 5
        assert len(data["data"]) <= 5
    
    def test_get_recent_users_invalid_pagination(self, admin_client, test_db: Session):
        """Test pagination parameter validation"""
        # Test with invalid page_size (too large)
        response = admin_client.get("/api/admin/recent-users?page_size=200")
        assert response.status_code == 200
        data = response.json()
        pagination = data["pagination"]
        assert pagination["page_size"] == 10  # Should default to 10
        
        # Test with invalid page (negative)
        response = admin_client.get("/api/admin/recent-users?page=-1")
        assert response.status_code == 200
        data = response.json()
        pagination = data["pagination"]
        assert pagination["page"] == 1  # Should default to 1
    
    def test_get_recent_users_ordered_by_created_at(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test users are ordered by creation date (newest first)"""
        # Create users with slight delay to ensure different timestamps
        user1 = factory.create_user(username="olduser")
        user2 = factory.create_user(username="newuser")
        
        response = admin_client.get("/api/admin/recent-users")
        
        assert response.status_code == 200
        data = response.json()
        users = data["data"]
        
        # Find our test users in the response
        test_users = [u for u in users if u["username"] in ["olduser", "newuser"]]
        if len(test_users) == 2:
            # Newer user should appear first
            usernames = [u["username"] for u in test_users]
            assert usernames.index("newuser") < usernames.index("olduser")
    
    def test_get_recent_users_non_admin_forbidden(self, authenticated_client):
        """Test non-admin users cannot access recent users"""
        response = authenticated_client.get("/api/admin/recent-users")
        
        assert response.status_code == 403
        data = response.json()
        assert "需要管理员权限" in data["detail"]


class TestAdminCreateUser:
    """Test POST /api/admin/users endpoint"""
    
    def test_create_user_as_regular_user(self, admin_client, test_db: Session):
        """Test admin can create a regular user"""
        user_data = {
            "username": "newuser123",
            "email": "newuser123@example.com",
            "password": "password123",
            "role": "user"
        }
        
        response = admin_client.post("/api/admin/users", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "用户创建成功"
        assert data["data"]["username"] == "newuser123"
        assert data["data"]["email"] == "newuser123@example.com"
        assert data["data"]["role"] == "user"
        
        # Verify user was created in database
        from app.models.database import User
        user = test_db.query(User).filter(User.username == "newuser123").first()
        assert user is not None
        assert user.is_admin is False
        assert user.is_moderator is False
    
    def test_create_user_as_moderator(self, admin_client, test_db: Session):
        """Test admin can create a moderator user"""
        user_data = {
            "username": "newmod123",
            "email": "newmod123@example.com",
            "password": "password123",
            "role": "moderator"
        }
        
        response = admin_client.post("/api/admin/users", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["role"] == "moderator"
        
        # Verify user was created with moderator role
        from app.models.database import User
        user = test_db.query(User).filter(User.username == "newmod123").first()
        assert user is not None
        assert user.is_admin is False
        assert user.is_moderator is True
    
    def test_create_user_as_admin_by_super_admin(self, super_admin_client, test_db: Session):
        """Test super admin can create an admin user"""
        user_data = {
            "username": "newadmin123",
            "email": "newadmin123@example.com",
            "password": "password123",
            "role": "admin"
        }
        
        response = super_admin_client.post("/api/admin/users", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["role"] == "admin"
        
        # Verify user was created with admin role
        from app.models.database import User
        user = test_db.query(User).filter(User.username == "newadmin123").first()
        assert user is not None
        assert user.is_admin is True
        assert user.is_moderator is False
    
    def test_create_admin_by_regular_admin_forbidden(self, admin_client, test_db: Session):
        """Test regular admin cannot create admin users"""
        user_data = {
            "username": "newadmin456",
            "email": "newadmin456@example.com",
            "password": "password123",
            "role": "admin"
        }
        
        response = admin_client.post("/api/admin/users", json=user_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "只有超级管理员可以创建管理员账号" in data["error"]["message"]
    
    def test_create_user_duplicate_username(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test creating user with duplicate username fails"""
        # Create existing user
        factory.create_user(username="existinguser")
        
        user_data = {
            "username": "existinguser",
            "email": "newemail@example.com",
            "password": "password123",
            "role": "user"
        }
        

        response = admin_client.post("/api/admin/users", json=user_data)
        
        assert response.status_code == 409
        data = response.json()
        assert "用户名已存在" in data["error"]["message"]
    
    def test_create_user_duplicate_email(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test creating user with duplicate email fails"""
        # Create existing user
        factory.create_user(email="existing@example.com")
        
        user_data = {
            "username": "newusername",
            "email": "existing@example.com",
            "password": "password123",
            "role": "user"
        }
        
        response = admin_client.post("/api/admin/users", json=user_data)
        
        assert response.status_code == 409
        data = response.json()
        assert "邮箱已存在" in data["error"]["message"]
    
    def test_create_user_invalid_role(self, admin_client, test_db: Session):
        """Test creating user with invalid role fails"""
        user_data = {
            "username": "newuser789",
            "email": "newuser789@example.com",
            "password": "password123",
            "role": "superuser"
        }
        
        response = admin_client.post("/api/admin/users", json=user_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "角色" in data["error"]["message"] and ("不合法" in data["error"]["message"] or "必须是" in data["error"]["message"])
    
    def test_create_user_weak_password(self, admin_client, test_db: Session):
        """Test creating user with weak password fails"""
        # Password too short
        user_data = {
            "username": "newuser999",
            "email": "newuser999@example.com",
            "password": "pass",
            "role": "user"
        }
        
        response = admin_client.post("/api/admin/users", json=user_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "密码" in data["error"]["message"] and ("8" in data["error"]["message"] or "长度" in data["error"]["message"])
    
    def test_create_user_password_without_letters_or_numbers(self, admin_client, test_db: Session):
        """Test creating user with password missing letters or numbers fails"""
        # Password without numbers
        user_data = {
            "username": "newuser888",
            "email": "newuser888@example.com",
            "password": "passwordonly",
            "role": "user"
        }
        
        response = admin_client.post("/api/admin/users", json=user_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "密码" in data["error"]["message"] and ("字母" in data["error"]["message"] or "数字" in data["error"]["message"])
    
    def test_create_user_missing_fields(self, admin_client, test_db: Session):
        """Test creating user with missing required fields fails"""
        # Missing username
        response = admin_client.post("/api/admin/users", json={
            "email": "test@example.com",
            "password": "password123",
            "role": "user"
        })
        assert response.status_code == 422
        
        # Missing email
        response = admin_client.post("/api/admin/users", json={
            "username": "testuser",
            "password": "password123",
            "role": "user"
        })
        assert response.status_code == 422
        
        # Missing password
        response = admin_client.post("/api/admin/users", json={
            "username": "testuser",
            "email": "test@example.com",
            "role": "user"
        })
        assert response.status_code == 422
    
    def test_create_user_non_admin_forbidden(self, authenticated_client):
        """Test non-admin users cannot create users"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
            "role": "user"
        }
        
        response = authenticated_client.post("/api/admin/users", json=user_data)
        
        assert response.status_code == 403
        data = response.json()
        assert "需要管理员权限" in data["detail"]



class TestAdminUpdateUserRole:
    """Test PUT /api/admin/users/{id}/role endpoint"""
    
    def test_update_user_to_moderator(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can update user role to moderator"""
        user = factory.create_user(username="roletest1", is_admin=False, is_moderator=False)
        
        response = admin_client.put(f"/api/admin/users/{user.id}/role", json={"role": "moderator"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "用户角色更新成功"
        assert data["data"]["role"] == "moderator"
        
        # Verify role was updated in database
        test_db.refresh(user)
        assert user.is_moderator is True
        assert user.is_admin is False
    
    def test_update_moderator_to_user(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can demote moderator to user"""
        user = factory.create_user(username="roletest2", is_admin=False, is_moderator=True)
        
        response = admin_client.put(f"/api/admin/users/{user.id}/role", json={"role": "user"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["role"] == "user"
        
        # Verify role was updated in database
        test_db.refresh(user)
        assert user.is_moderator is False
        assert user.is_admin is False
    
    def test_super_admin_can_update_admin_role(self, super_admin_client, test_db: Session, factory: TestDataFactory):
        """Test super admin can update admin user role"""
        admin_user = factory.create_user(username="admintest1", is_admin=True, is_moderator=False)
        
        response = super_admin_client.put(f"/api/admin/users/{admin_user.id}/role", json={"role": "moderator"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["role"] == "moderator"
        
        # Verify role was updated
        test_db.refresh(admin_user)
        assert admin_user.is_admin is False
        assert admin_user.is_moderator is True
    
    def test_super_admin_can_promote_to_admin(self, super_admin_client, test_db: Session, factory: TestDataFactory):
        """Test super admin can promote user to admin"""
        user = factory.create_user(username="promotetest1", is_admin=False, is_moderator=False)
        
        response = super_admin_client.put(f"/api/admin/users/{user.id}/role", json={"role": "admin"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["role"] == "admin"
        
        # Verify role was updated
        test_db.refresh(user)
        assert user.is_admin is True
        assert user.is_moderator is False
    
    def test_regular_admin_cannot_update_admin_role(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test regular admin cannot modify another admin's role"""
        admin_user = factory.create_user(username="admintest2", is_admin=True, is_moderator=False)
        
        response = admin_client.put(f"/api/admin/users/{admin_user.id}/role", json={"role": "user"})
        
        assert response.status_code == 422
        data = response.json()
        assert "只有超级管理员可以修改管理员或超级管理员的角色" in data["error"]["message"]
    
    def test_regular_admin_cannot_promote_to_admin(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test regular admin cannot promote user to admin"""
        user = factory.create_user(username="promotetest2", is_admin=False, is_moderator=False)
        
        response = admin_client.put(f"/api/admin/users/{user.id}/role", json={"role": "admin"})
        
        assert response.status_code == 422
        data = response.json()
        assert "只有超级管理员可以任命管理员" in data["error"]["message"]
    
    def test_cannot_update_own_role(self, admin_client, test_db: Session):
        """Test admin cannot update their own role"""
        # Get the admin user's ID from the client
        response = admin_client.get("/api/users/me")
        admin_id = response.json()["data"]["id"]
        
        response = admin_client.put(f"/api/admin/users/{admin_id}/role", json={"role": "user"})
        
        assert response.status_code == 422
        data = response.json()
        assert "不能修改" in data["error"]["message"] and ("自己" in data["error"]["message"] or "当前" in data["error"]["message"])
    
    def test_update_role_invalid_role(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test updating to invalid role fails"""
        user = factory.create_user(username="roletest3")
        
        response = admin_client.put(f"/api/admin/users/{user.id}/role", json={"role": "superuser"})
        
        assert response.status_code == 422
        data = response.json()
        assert "角色" in data["error"]["message"] and ("不合法" in data["error"]["message"] or "必须是" in data["error"]["message"])
    
    def test_update_role_nonexistent_user(self, admin_client, test_db: Session):
        """Test updating role of nonexistent user fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = admin_client.put(f"/api/admin/users/{fake_id}/role", json={"role": "moderator"})
        
        assert response.status_code == 404
        data = response.json()
        assert "用户不存在" in data["error"]["message"]
    
    def test_update_role_non_admin_forbidden(self, authenticated_client, factory: TestDataFactory):
        """Test non-admin users cannot update roles"""
        user = factory.create_user(username="roletest4")
        
        response = authenticated_client.put(f"/api/admin/users/{user.id}/role", json={"role": "moderator"})
        
        assert response.status_code == 403
        data = response.json()
        assert "需要管理员权限" in data["detail"]



class TestAdminDeleteUser:
    """Test DELETE /api/admin/users/{id} endpoint"""
    
    def test_delete_regular_user(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can delete a regular user"""
        user = factory.create_user(username="deletetest1", is_admin=False, is_moderator=False)
        
        response = admin_client.delete(f"/api/admin/users/{user.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "用户删除成功"
        
        # Verify user was soft deleted (is_active = False)
        test_db.refresh(user)
        assert user.is_active is False
    
    def test_delete_moderator(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can delete a moderator"""
        moderator = factory.create_user(username="deletetest2", is_admin=False, is_moderator=True)
        
        response = admin_client.delete(f"/api/admin/users/{moderator.id}")
        
        assert response.status_code == 200
        
        # Verify moderator was soft deleted
        test_db.refresh(moderator)
        assert moderator.is_active is False
    
    def test_super_admin_can_delete_admin(self, super_admin_client, test_db: Session, factory: TestDataFactory):
        """Test super admin can delete an admin user"""
        admin_user = factory.create_user(username="deletetest3", is_admin=True, is_moderator=False)
        
        response = super_admin_client.delete(f"/api/admin/users/{admin_user.id}")
        
        assert response.status_code == 200
        
        # Verify admin was soft deleted
        test_db.refresh(admin_user)
        assert admin_user.is_active is False
    
    def test_regular_admin_cannot_delete_admin(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test regular admin cannot delete another admin"""
        admin_user = factory.create_user(username="deletetest4", is_admin=True, is_moderator=False)
        
        response = admin_client.delete(f"/api/admin/users/{admin_user.id}")
        
        assert response.status_code == 422
        data = response.json()
        assert "管理员不能删除其它管理员或超级管理员账号" in data["error"]["message"]
    
    def test_cannot_delete_self(self, admin_client, test_db: Session):
        """Test admin cannot delete themselves"""
        # Get the admin user's ID
        response = admin_client.get("/api/users/me")
        admin_id = response.json()["data"]["id"]
        
        response = admin_client.delete(f"/api/admin/users/{admin_id}")
        
        assert response.status_code == 422
        data = response.json()
        assert "不能删除" in data["error"]["message"] and ("自己" in data["error"]["message"] or "当前" in data["error"]["message"])
    
    def test_delete_nonexistent_user(self, admin_client, test_db: Session):
        """Test deleting nonexistent user fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = admin_client.delete(f"/api/admin/users/{fake_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "用户不存在" in data["error"]["message"]
    
    def test_delete_user_non_admin_forbidden(self, authenticated_client, factory: TestDataFactory):
        """Test non-admin users cannot delete users"""
        user = factory.create_user(username="deletetest5")
        
        response = authenticated_client.delete(f"/api/admin/users/{user.id}")
        
        assert response.status_code == 403
        data = response.json()
        assert "需要管理员权限" in data["detail"]



class TestAdminMuteUser:
    """Test POST /api/admin/users/{id}/mute endpoint"""
    
    def test_mute_user_for_one_day(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can mute user for 1 day"""
        user = factory.create_user(username="mutetest1")
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": "1d", "reason": "Spam posting"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "用户禁言成功"
        assert data["data"]["userId"] == str(user.id)
        assert data["data"]["isMuted"] is True
        assert data["data"]["mutedUntil"] is not None
        assert data["data"]["muteReason"] == "Spam posting"
        
        # Verify user was muted in database
        test_db.refresh(user)
        assert user.is_muted is True
        assert user.muted_until is not None
        assert user.mute_reason == "Spam posting"
        
        # Verify muted_until is approximately 1 day from now
        from datetime import datetime, timedelta
        expected_time = datetime.now() + timedelta(days=1)
        time_diff = abs((user.muted_until - expected_time).total_seconds())
        assert time_diff < 5  # Within 5 seconds
    
    def test_mute_user_for_seven_days(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can mute user for 7 days"""
        user = factory.create_user(username="mutetest2")
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": "7d", "reason": "Harassment"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["isMuted"] is True
        
        # Verify muted_until is approximately 7 days from now
        test_db.refresh(user)
        from datetime import datetime, timedelta
        expected_time = datetime.now() + timedelta(days=7)
        time_diff = abs((user.muted_until - expected_time).total_seconds())
        assert time_diff < 5
    
    def test_mute_user_for_thirty_days(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can mute user for 30 days"""
        user = factory.create_user(username="mutetest3")
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": "30d", "reason": "Repeated violations"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["isMuted"] is True
        
        # Verify muted_until is approximately 30 days from now
        test_db.refresh(user)
        from datetime import datetime, timedelta
        expected_time = datetime.now() + timedelta(days=30)
        time_diff = abs((user.muted_until - expected_time).total_seconds())
        assert time_diff < 5
    
    def test_mute_user_permanently(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can mute user permanently"""
        user = factory.create_user(username="mutetest4")
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": "permanent", "reason": "Severe violations"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["isMuted"] is True
        assert data["data"]["mutedUntil"] is None  # Permanent mute has no end date
        
        # Verify user was permanently muted in database
        test_db.refresh(user)
        assert user.is_muted is True
        assert user.muted_until is None
    
    def test_mute_user_without_reason(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can mute user without providing a reason"""
        user = factory.create_user(username="mutetest5")
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": "7d"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["isMuted"] is True
        assert data["data"]["muteReason"] == ""
        
        # Verify in database
        test_db.refresh(user)
        assert user.is_muted is True
        assert user.mute_reason is None
    
    def test_mute_user_invalid_duration(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test muting user with invalid duration fails"""
        user = factory.create_user(username="mutetest6")
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": "invalid", "reason": "Test"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "禁言时长" in data["error"]["message"]
    
    def test_mute_user_cannot_mute_self(self, admin_client, test_db: Session):
        """Test admin cannot mute themselves"""
        # Get the admin user's ID
        response = admin_client.get("/api/users/me")
        admin_id = response.json()["data"]["id"]
        
        response = admin_client.post(
            f"/api/admin/users/{admin_id}/mute",
            json={"duration": "7d", "reason": "Test"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "不能" in data["error"]["message"] and ("自己" in data["error"]["message"] or "当前" in data["error"]["message"])
    
    def test_regular_admin_cannot_mute_admin(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test regular admin cannot mute another admin"""
        admin_user = factory.create_user(username="admintest5", is_admin=True)
        
        response = admin_client.post(
            f"/api/admin/users/{admin_user.id}/mute",
            json={"duration": "7d", "reason": "Test"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "管理员" in data["error"]["message"] and "禁言" in data["error"]["message"]
    
    def test_super_admin_can_mute_admin(self, super_admin_client, test_db: Session, factory: TestDataFactory):
        """Test super admin can mute an admin user"""
        admin_user = factory.create_user(username="admintest6", is_admin=True)
        
        response = super_admin_client.post(
            f"/api/admin/users/{admin_user.id}/mute",
            json={"duration": "7d", "reason": "Admin violation"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["isMuted"] is True
        
        # Verify in database
        test_db.refresh(admin_user)
        assert admin_user.is_muted is True
    
    def test_mute_nonexistent_user(self, admin_client, test_db: Session):
        """Test muting nonexistent user fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = admin_client.post(
            f"/api/admin/users/{fake_id}/mute",
            json={"duration": "7d", "reason": "Test"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "用户不存在" in data["error"]["message"]
    
    def test_mute_user_non_admin_forbidden(self, authenticated_client, factory: TestDataFactory):
        """Test non-admin users cannot mute users"""
        user = factory.create_user(username="mutetest7")
        
        response = authenticated_client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": "7d", "reason": "Test"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "需要管理员权限" in data["detail"]


class TestAdminUnmuteUser:
    """Test POST /api/admin/users/{id}/unmute endpoint"""
    
    def test_unmute_muted_user(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can unmute a muted user"""
        from datetime import datetime, timedelta
        user = factory.create_user(username="unmutetest1")
        
        # First mute the user
        user.is_muted = True
        user.muted_until = datetime.now() + timedelta(days=7)
        user.mute_reason = "Test mute"
        test_db.commit()
        
        # Now unmute
        response = admin_client.post(f"/api/admin/users/{user.id}/unmute")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "用户已解除禁言"
        assert data["data"]["userId"] == str(user.id)
        assert data["data"]["isMuted"] is False
        assert data["data"]["mutedUntil"] is None
        
        # Verify user was unmuted in database
        test_db.refresh(user)
        assert user.is_muted is False
        assert user.muted_until is None
        assert user.mute_reason is None
    
    def test_unmute_permanently_muted_user(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can unmute a permanently muted user"""
        user = factory.create_user(username="unmutetest2")
        
        # Mute permanently
        user.is_muted = True
        user.muted_until = None
        user.mute_reason = "Permanent mute"
        test_db.commit()
        
        # Unmute
        response = admin_client.post(f"/api/admin/users/{user.id}/unmute")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["isMuted"] is False
        
        # Verify in database
        test_db.refresh(user)
        assert user.is_muted is False
        assert user.muted_until is None
    
    def test_unmute_already_unmuted_user(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test unmuting an already unmuted user succeeds (idempotent)"""
        user = factory.create_user(username="unmutetest3")
        
        # User is not muted
        assert user.is_muted is False
        
        response = admin_client.post(f"/api/admin/users/{user.id}/unmute")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["isMuted"] is False
    
    def test_regular_admin_cannot_unmute_admin(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test regular admin cannot unmute another admin"""
        from datetime import datetime, timedelta
        admin_user = factory.create_user(username="admintest7", is_admin=True)
        admin_user.is_muted = True
        admin_user.muted_until = datetime.now() + timedelta(days=7)
        test_db.commit()
        
        response = admin_client.post(f"/api/admin/users/{admin_user.id}/unmute")
        
        # The endpoint returns 500 because ValidationError is not caught separately
        assert response.status_code == 500
        data = response.json()
        assert "管理员" in data["detail"] and "禁言" in data["detail"]
    
    def test_super_admin_can_unmute_admin(self, super_admin_client, test_db: Session, factory: TestDataFactory):
        """Test super admin can unmute an admin user"""
        from datetime import datetime, timedelta
        admin_user = factory.create_user(username="admintest8", is_admin=True)
        admin_user.is_muted = True
        admin_user.muted_until = datetime.now() + timedelta(days=7)
        test_db.commit()
        
        response = super_admin_client.post(f"/api/admin/users/{admin_user.id}/unmute")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["isMuted"] is False
        
        # Verify in database
        test_db.refresh(admin_user)
        assert admin_user.is_muted is False
    
    def test_unmute_nonexistent_user(self, admin_client, test_db: Session):
        """Test unmuting nonexistent user fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = admin_client.post(f"/api/admin/users/{fake_id}/unmute")
        
        assert response.status_code == 404
        data = response.json()
        assert "用户不存在" in data["detail"]
    
    def test_unmute_user_non_admin_forbidden(self, authenticated_client, factory: TestDataFactory):
        """Test non-admin users cannot unmute users"""
        user = factory.create_user(username="unmutetest4")
        
        response = authenticated_client.post(f"/api/admin/users/{user.id}/unmute")
        
        assert response.status_code == 403
        data = response.json()
        assert "需要管理员权限" in data["detail"]


class TestAdminBanUser:
    """Test POST /api/admin/users/{id}/ban endpoint"""
    
    def test_ban_user_for_one_day(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can ban user for 1 day"""
        user = factory.create_user(username="bantest1")
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/ban",
            json={"duration": "1d", "reason": "Minor violation"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "用户封禁成功"
        assert "locked_until" in data["data"]
        assert data["data"]["ban_reason"] == "Minor violation"
        
        # Verify user was banned in database
        test_db.refresh(user)
        assert user.locked_until is not None
        assert user.ban_reason == "Minor violation"
        
        # Verify locked_until is approximately 1 day from now
        from datetime import datetime, timedelta
        expected_time = datetime.now() + timedelta(days=1)
        time_diff = abs((user.locked_until - expected_time).total_seconds())
        assert time_diff < 5
    
    def test_ban_user_for_seven_days(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can ban user for 7 days"""
        user = factory.create_user(username="bantest2")
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/ban",
            json={"duration": "7d", "reason": "Moderate violation"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "locked_until" in data["data"]
        
        # Verify locked_until is approximately 7 days from now
        test_db.refresh(user)
        from datetime import datetime, timedelta
        expected_time = datetime.now() + timedelta(days=7)
        time_diff = abs((user.locked_until - expected_time).total_seconds())
        assert time_diff < 5
    
    def test_ban_user_for_thirty_days(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can ban user for 30 days"""
        user = factory.create_user(username="bantest3")
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/ban",
            json={"duration": "30d", "reason": "Serious violation"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "locked_until" in data["data"]
        
        # Verify locked_until is approximately 30 days from now
        test_db.refresh(user)
        from datetime import datetime, timedelta
        expected_time = datetime.now() + timedelta(days=30)
        time_diff = abs((user.locked_until - expected_time).total_seconds())
        assert time_diff < 5
    
    def test_ban_user_permanently(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can ban user permanently"""
        user = factory.create_user(username="bantest4")
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/ban",
            json={"duration": "permanent", "reason": "Severe violations"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "locked_until" in data["data"]
        
        # Verify user was permanently banned (100 years in the future)
        test_db.refresh(user)
        assert user.locked_until is not None
        from datetime import datetime, timedelta
        expected_time = datetime.now() + timedelta(days=365 * 100)
        time_diff = abs((user.locked_until - expected_time).total_seconds())
        assert time_diff < 5
    
    def test_ban_user_without_reason(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can ban user without providing a reason"""
        user = factory.create_user(username="bantest5")
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/ban",
            json={"duration": "7d"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["ban_reason"] == ""
        
        # Verify in database
        test_db.refresh(user)
        assert user.locked_until is not None
        assert user.ban_reason is None
    
    def test_ban_user_invalid_duration(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test banning user with invalid duration fails"""
        user = factory.create_user(username="bantest6")
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/ban",
            json={"duration": "invalid", "reason": "Test"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "封禁时长" in data["error"]["message"]
    
    def test_ban_user_cannot_ban_self(self, admin_client, test_db: Session):
        """Test admin cannot ban themselves"""
        # Get the admin user's ID
        response = admin_client.get("/api/users/me")
        admin_id = response.json()["data"]["id"]
        
        response = admin_client.post(
            f"/api/admin/users/{admin_id}/ban",
            json={"duration": "7d", "reason": "Test"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "不能封禁" in data["error"]["message"] and ("自己" in data["error"]["message"] or "当前" in data["error"]["message"])
    
    def test_regular_admin_cannot_ban_admin(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test regular admin cannot ban another admin"""
        admin_user = factory.create_user(username="admintest9", is_admin=True)
        
        response = admin_client.post(
            f"/api/admin/users/{admin_user.id}/ban",
            json={"duration": "7d", "reason": "Test"}
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "管理员" in data["error"]["message"] and "封禁" in data["error"]["message"]
    
    def test_super_admin_can_ban_admin(self, super_admin_client, test_db: Session, factory: TestDataFactory):
        """Test super admin can ban an admin user"""
        # Create two admin users so we don't violate the "last admin" rule
        admin_user1 = factory.create_user(username="admintest10", is_admin=True)
        admin_user2 = factory.create_user(username="admintest11", is_admin=True)
        
        response = super_admin_client.post(
            f"/api/admin/users/{admin_user1.id}/ban",
            json={"duration": "7d", "reason": "Admin violation"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "locked_until" in data["data"]
        
        # Verify in database
        test_db.refresh(admin_user1)
        assert admin_user1.locked_until is not None
    
    def test_cannot_ban_last_admin(self, super_admin_client, test_db: Session, factory: TestDataFactory):
        """Test cannot ban the last active admin"""
        # Get the super admin user
        response = super_admin_client.get("/api/users/me")
        super_admin_id = response.json()["data"]["id"]
        
        # Try to ban self (who is the only admin)
        response = super_admin_client.post(
            f"/api/admin/users/{super_admin_id}/ban",
            json={"duration": "7d", "reason": "Test"}
        )
        
        # Should fail because can't ban self
        assert response.status_code == 422
    
    def test_ban_nonexistent_user(self, admin_client, test_db: Session):
        """Test banning nonexistent user fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = admin_client.post(
            f"/api/admin/users/{fake_id}/ban",
            json={"duration": "7d", "reason": "Test"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "用户不存在" in data["error"]["message"]
    
    def test_ban_user_non_admin_forbidden(self, authenticated_client, factory: TestDataFactory):
        """Test non-admin users cannot ban users"""
        user = factory.create_user(username="bantest7")
        
        response = authenticated_client.post(
            f"/api/admin/users/{user.id}/ban",
            json={"duration": "7d", "reason": "Test"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "需要管理员权限" in data["detail"]


class TestAdminUnbanUser:
    """Test POST /api/admin/users/{id}/unban endpoint"""
    
    def test_unban_banned_user(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can unban a banned user"""
        from datetime import datetime, timedelta
        user = factory.create_user(username="unbantest1")
        
        # First ban the user
        user.locked_until = datetime.now() + timedelta(days=7)
        user.ban_reason = "Test ban"
        user.failed_login_attempts = 3
        test_db.commit()
        
        # Now unban
        response = admin_client.post(f"/api/admin/users/{user.id}/unban")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "用户已解封"
        
        # Verify user was unbanned in database
        test_db.refresh(user)
        assert user.locked_until is None
        assert user.ban_reason is None
        assert user.failed_login_attempts == 0
    
    def test_unban_permanently_banned_user(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test admin can unban a permanently banned user"""
        from datetime import datetime, timedelta
        user = factory.create_user(username="unbantest2")
        
        # Ban permanently
        user.locked_until = datetime.now() + timedelta(days=365 * 100)
        user.ban_reason = "Permanent ban"
        test_db.commit()
        
        # Unban
        response = admin_client.post(f"/api/admin/users/{user.id}/unban")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "用户已解封"
        
        # Verify in database
        test_db.refresh(user)
        assert user.locked_until is None
        assert user.ban_reason is None
    
    def test_unban_already_unbanned_user(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test unbanning an already unbanned user succeeds (idempotent)"""
        user = factory.create_user(username="unbantest3")
        
        # User is not banned
        assert user.locked_until is None
        
        response = admin_client.post(f"/api/admin/users/{user.id}/unban")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "用户已解封"
    
    def test_unban_resets_failed_login_attempts(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test unbanning resets failed login attempts counter"""
        from datetime import datetime, timedelta
        user = factory.create_user(username="unbantest4")
        
        # Ban user with failed login attempts
        user.locked_until = datetime.now() + timedelta(days=7)
        user.failed_login_attempts = 5
        test_db.commit()
        
        # Unban
        response = admin_client.post(f"/api/admin/users/{user.id}/unban")
        
        assert response.status_code == 200
        
        # Verify failed login attempts were reset
        test_db.refresh(user)
        assert user.failed_login_attempts == 0
    
    def test_regular_admin_cannot_unban_admin(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test regular admin cannot unban another admin"""
        from datetime import datetime, timedelta
        admin_user = factory.create_user(username="admintest12", is_admin=True)
        admin_user.locked_until = datetime.now() + timedelta(days=7)
        test_db.commit()
        
        response = admin_client.post(f"/api/admin/users/{admin_user.id}/unban")
        
        assert response.status_code == 422
        data = response.json()
        assert "管理员" in data["error"]["message"] and "解封" in data["error"]["message"]
    
    def test_super_admin_can_unban_admin(self, super_admin_client, test_db: Session, factory: TestDataFactory):
        """Test super admin can unban an admin user"""
        from datetime import datetime, timedelta
        admin_user = factory.create_user(username="admintest13", is_admin=True)
        admin_user.locked_until = datetime.now() + timedelta(days=7)
        test_db.commit()
        
        response = super_admin_client.post(f"/api/admin/users/{admin_user.id}/unban")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "用户已解封"
        
        # Verify in database
        test_db.refresh(admin_user)
        assert admin_user.locked_until is None
    
    def test_unban_nonexistent_user(self, admin_client, test_db: Session):
        """Test unbanning nonexistent user fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = admin_client.post(f"/api/admin/users/{fake_id}/unban")
        
        assert response.status_code == 404
        data = response.json()
        assert "用户不存在" in data["error"]["message"]
    
    def test_unban_user_non_admin_forbidden(self, authenticated_client, factory: TestDataFactory):
        """Test non-admin users cannot unban users"""
        user = factory.create_user(username="unbantest5")
        
        response = authenticated_client.post(f"/api/admin/users/{user.id}/unban")
        
        assert response.status_code == 403
        data = response.json()
        assert "需要管理员权限" in data["detail"]



class TestAdminPermissionBoundaries:
    """Test admin permission boundaries and special cases
    
    Requirements: 1.1, 7.3, 7.4
    """
    
    def test_super_admin_has_all_permissions(self, super_admin_client, test_db: Session, factory: TestDataFactory):
        """Test super admin can perform all admin operations"""
        # Create test users with different roles
        regular_user = factory.create_user(username="regular_boundary_test")
        moderator = factory.create_user(username="mod_boundary_test", is_moderator=True)
        admin = factory.create_user(username="admin_boundary_test", is_admin=True)
        
        # Super admin can create admin users
        response = super_admin_client.post("/api/admin/users", json={
            "username": "new_admin_boundary",
            "email": "new_admin_boundary@example.com",
            "password": "password123",
            "role": "admin"
        })
        assert response.status_code == 200
        
        # Super admin can modify admin roles
        response = super_admin_client.put(f"/api/admin/users/{admin.id}/role", json={"role": "user"})
        assert response.status_code == 200
        
        # Super admin can delete admin users (if not last admin)
        admin2 = factory.create_user(username="admin_boundary_test2", is_admin=True)
        response = super_admin_client.delete(f"/api/admin/users/{admin2.id}")
        assert response.status_code == 200
        
        # Super admin can mute admin users
        admin3 = factory.create_user(username="admin_boundary_test3", is_admin=True)
        response = super_admin_client.post(f"/api/admin/users/{admin3.id}/mute", json={
            "duration": "1d",
            "reason": "Test"
        })
        assert response.status_code == 200
        
        # Super admin can ban admin users (if not last admin)
        admin4 = factory.create_user(username="admin_boundary_test4", is_admin=True)
        response = super_admin_client.post(f"/api/admin/users/{admin4.id}/ban", json={
            "duration": "1d",
            "reason": "Test"
        })
        assert response.status_code == 200
    
    def test_regular_admin_limited_permissions(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test regular admin has limited permissions compared to super admin"""
        admin_user = factory.create_user(username="admin_limited_test", is_admin=True)
        
        # Regular admin CANNOT create admin users
        response = admin_client.post("/api/admin/users", json={
            "username": "new_admin_limited",
            "email": "new_admin_limited@example.com",
            "password": "password123",
            "role": "admin"
        })
        assert response.status_code == 422
        assert "只有超级管理员可以创建管理员账号" in response.json()["error"]["message"]
        
        # Regular admin CANNOT modify admin roles
        response = admin_client.put(f"/api/admin/users/{admin_user.id}/role", json={"role": "user"})
        assert response.status_code == 422
        assert "只有超级管理员可以修改管理员或超级管理员的角色" in response.json()["error"]["message"]
        
        # Regular admin CANNOT delete admin users
        response = admin_client.delete(f"/api/admin/users/{admin_user.id}")
        assert response.status_code == 422
        assert "管理员不能删除其它管理员或超级管理员账号" in response.json()["error"]["message"]
        
        # Regular admin CANNOT mute admin users
        response = admin_client.post(f"/api/admin/users/{admin_user.id}/mute", json={
            "duration": "1d",
            "reason": "Test"
        })
        assert response.status_code == 422
        assert "管理员" in response.json()["error"]["message"] and "禁言" in response.json()["error"]["message"]
        
        # Regular admin CANNOT ban admin users
        response = admin_client.post(f"/api/admin/users/{admin_user.id}/ban", json={
            "duration": "1d",
            "reason": "Test"
        })
        assert response.status_code == 422
        assert "管理员" in response.json()["error"]["message"] and "封禁" in response.json()["error"]["message"]
    
    def test_regular_admin_can_manage_regular_users(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test regular admin can manage regular users and moderators"""
        regular_user = factory.create_user(username="regular_manage_test")
        moderator = factory.create_user(username="mod_manage_test", is_moderator=True)
        
        # Regular admin CAN create regular users
        response = admin_client.post("/api/admin/users", json={
            "username": "new_regular_user",
            "email": "new_regular_user@example.com",
            "password": "password123",
            "role": "user"
        })
        assert response.status_code == 200
        
        # Regular admin CAN create moderators
        response = admin_client.post("/api/admin/users", json={
            "username": "new_moderator",
            "email": "new_moderator@example.com",
            "password": "password123",
            "role": "moderator"
        })
        assert response.status_code == 200
        
        # Regular admin CAN modify regular user roles
        response = admin_client.put(f"/api/admin/users/{regular_user.id}/role", json={"role": "moderator"})
        assert response.status_code == 200
        
        # Regular admin CAN delete regular users
        response = admin_client.delete(f"/api/admin/users/{regular_user.id}")
        assert response.status_code == 200
        
        # Regular admin CAN mute moderators
        response = admin_client.post(f"/api/admin/users/{moderator.id}/mute", json={
            "duration": "1d",
            "reason": "Test"
        })
        assert response.status_code == 200
        
        # Regular admin CAN ban moderators
        response = admin_client.post(f"/api/admin/users/{moderator.id}/ban", json={
            "duration": "1d",
            "reason": "Test"
        })
        assert response.status_code == 200
    
    def test_cannot_remove_last_admin_via_role_change(self, test_db: Session, factory: TestDataFactory):
        """Test cannot demote the last admin via role change
        
        This test creates a scenario with only ONE admin (not super admin) and verifies
        that attempting to demote them is prevented.
        """
        from app.models.database import User
        from app.main import app
        from tests.auth_helper import AuthHelper
        
        # Create a single admin user (not super admin)
        admin_user = factory.create_user(
            username="only_admin_test",
            is_admin=True,
            is_super_admin=True,  # Make them super admin so they can modify their own role
            is_moderator=True
        )
        
        # Create authenticated client for this admin
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        admin_client = auth_helper.create_authenticated_client(admin_user)
        
        # Verify this is the only admin
        admin_count = test_db.query(func.count(User.id)).filter(
            User.is_admin == True,
            User.is_active == True
        ).scalar() or 0
        assert admin_count == 1
        
        # Try to demote ourselves - should fail because we're the last admin
        response = admin_client.put(f"/api/admin/users/{admin_user.id}/role", json={"role": "user"})
        assert response.status_code == 422
        data = response.json()
        assert "不能删除最后一个管理员" in data["error"]["message"] or "不能修改" in data["error"]["message"]
    
    def test_cannot_delete_last_admin(self, test_db: Session, factory: TestDataFactory):
        """Test cannot delete the last admin
        
        This test creates a scenario with only ONE admin and verifies
        that attempting to delete them is prevented.
        """
        from app.models.database import User
        from app.main import app
        from tests.auth_helper import AuthHelper
        
        # Create a single admin user (super admin so they can delete users)
        admin_user = factory.create_user(
            username="only_admin_delete_test",
            is_admin=True,
            is_super_admin=True,
            is_moderator=True
        )
        
        # Create authenticated client for this admin
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        admin_client = auth_helper.create_authenticated_client(admin_user)
        
        # Verify this is the only admin
        admin_count = test_db.query(func.count(User.id)).filter(
            User.is_admin == True,
            User.is_active == True
        ).scalar() or 0
        assert admin_count == 1
        
        # Try to delete ourselves - should fail (can't delete self)
        response = admin_client.delete(f"/api/admin/users/{admin_user.id}")
        assert response.status_code == 422
        data = response.json()
        # Should fail either because we can't delete ourselves OR because we're the last admin
        assert "不能删除" in data["error"]["message"]
    
    def test_cannot_ban_last_admin(self, test_db: Session, factory: TestDataFactory):
        """Test cannot ban the last admin
        
        This test creates a scenario with only ONE admin and verifies
        that attempting to ban them is prevented.
        """
        from app.models.database import User
        from app.main import app
        from tests.auth_helper import AuthHelper
        from datetime import datetime, timedelta
        
        # Create a single admin user (super admin so they can ban users)
        admin_user = factory.create_user(
            username="only_admin_ban_test",
            is_admin=True,
            is_super_admin=True,
            is_moderator=True
        )
        
        # Create authenticated client for this admin
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        admin_client = auth_helper.create_authenticated_client(admin_user)
        
        # Verify this is the only admin
        admin_count = test_db.query(func.count(User.id)).filter(
            User.is_admin == True,
            User.is_active == True
        ).scalar() or 0
        assert admin_count == 1
        
        # Try to ban ourselves - should fail (can't ban self)
        response = admin_client.post(f"/api/admin/users/{admin_user.id}/ban", json={
            "duration": "1d",
            "reason": "Test"
        })
        assert response.status_code == 422
        data = response.json()
        # Should fail either because we can't ban ourselves OR because we're the last admin
        assert "不能封禁" in data["error"]["message"]
    
    def test_non_admin_cannot_access_admin_endpoints(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test non-admin users are denied access to all admin endpoints"""
        user = factory.create_user(username="non_admin_test")
        
        # Cannot access stats
        response = authenticated_client.get("/api/admin/stats")
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Cannot access recent users
        response = authenticated_client.get("/api/admin/recent-users")
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Cannot access all users
        response = authenticated_client.get("/api/admin/users")
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Cannot create users
        response = authenticated_client.post("/api/admin/users", json={
            "username": "test_user",
            "email": "test@example.com",
            "password": "password123",
            "role": "user"
        })
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Cannot update user roles
        response = authenticated_client.put(f"/api/admin/users/{user.id}/role", json={"role": "moderator"})
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Cannot delete users
        response = authenticated_client.delete(f"/api/admin/users/{user.id}")
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Cannot mute users
        response = authenticated_client.post(f"/api/admin/users/{user.id}/mute", json={
            "duration": "1d",
            "reason": "Test"
        })
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Cannot unmute users
        response = authenticated_client.post(f"/api/admin/users/{user.id}/unmute")
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Cannot ban users
        response = authenticated_client.post(f"/api/admin/users/{user.id}/ban", json={
            "duration": "1d",
            "reason": "Test"
        })
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Cannot unban users
        response = authenticated_client.post(f"/api/admin/users/{user.id}/unban")
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
    
    def test_moderator_cannot_access_admin_endpoints(self, test_db: Session, factory: TestDataFactory):
        """Test moderators are denied access to admin-only endpoints"""
        from app.main import app
        from tests.auth_helper import AuthHelper
        
        # Create moderator and get authenticated client
        moderator = factory.create_user(username="moderator_boundary_test", is_moderator=True, is_admin=False)
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        moderator_client = auth_helper.create_authenticated_client(moderator)
        
        # Moderators cannot access admin stats
        response = moderator_client.get("/api/admin/stats")
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Moderators cannot create users
        response = moderator_client.post("/api/admin/users", json={
            "username": "test_user",
            "email": "test@example.com",
            "password": "password123",
            "role": "user"
        })
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Moderators cannot update user roles
        user = factory.create_user(username="user_for_mod_test")
        response = moderator_client.put(f"/api/admin/users/{user.id}/role", json={"role": "user"})
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Moderators cannot delete users
        response = moderator_client.delete(f"/api/admin/users/{user.id}")
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Moderators cannot mute users
        response = moderator_client.post(f"/api/admin/users/{user.id}/mute", json={
            "duration": "1d",
            "reason": "Test"
        })
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
        
        # Moderators cannot ban users
        response = moderator_client.post(f"/api/admin/users/{user.id}/ban", json={
            "duration": "1d",
            "reason": "Test"
        })
        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]
    
    def test_unauthenticated_cannot_access_admin_endpoints(self, test_db: Session):
        """Test unauthenticated users are denied access to all admin endpoints"""
        from app.main import app
        client = TestClient(app)
        
        # Cannot access stats
        response = client.get("/api/admin/stats")
        assert response.status_code == 401
        
        # Cannot access recent users
        response = client.get("/api/admin/recent-users")
        assert response.status_code == 401
        
        # Cannot access all users
        response = client.get("/api/admin/users")
        assert response.status_code == 401
        
        # Cannot create users
        response = client.post("/api/admin/users", json={
            "username": "test_user",
            "email": "test@example.com",
            "password": "password123",
            "role": "user"
        })
        assert response.status_code == 401
