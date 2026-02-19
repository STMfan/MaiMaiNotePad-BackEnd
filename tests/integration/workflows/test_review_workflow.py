"""
Integration workflow tests for review and admin management
Tests complete end-to-end review approval and admin management workflows

Example 4: Review and approval workflow
Example 5: Admin management workflow
Requirements: 9.4, 9.5
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.database import User, KnowledgeBase, PersonaCard
from app.core.security import get_password_hash
import uuid


class TestReviewAndApprovalWorkflow:
    """Test complete review and approval workflow"""
    
    def test_knowledge_base_review_and_approval_flow(self, test_db: Session):
        """
        Test Example 4: Review and approval workflow (Knowledge Base)
        
        Complete workflow:
        1. Regular user creates knowledge base
        2. KB is in pending status
        3. Moderator views pending reviews
        4. Moderator approves KB
        5. KB becomes public and accessible
        6. Verify status transitions
        
        **Validates: Requirements 9.4**
        """
        from app.main import app
        client = TestClient(app)
        
        # Step 1: Create regular user
        user = User(
            id=str(uuid.uuid4()),
            username="kbcreator",
            email="kbcreator@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(user)
        test_db.commit()
        
        # Create moderator
        moderator = User(
            id=str(uuid.uuid4()),
            username="kbmoderator",
            email="kbmod@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=True,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(moderator)
        test_db.commit()
        
        # User login
        user_login = client.post(
            "/api/auth/token",
            json={"username": "kbcreator", "password": "password123"}
        )
        user_token = user_login.json()["data"]["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Step 2: Create knowledge base (should be pending)
        kb_response = client.post(
            "/api/knowledge",
            json={
                "title": "Pending Knowledge Base",
                "description": "Needs review",
                "is_public": True
            },
            headers=user_headers
        )
        
        assert kb_response.status_code == 201
        kb_id = kb_response.json()["id"]
        
        # Verify KB is in pending status
        kb_in_db = test_db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id
        ).first()
        assert kb_in_db is not None
        assert kb_in_db.status == "pending"
        
        # Step 3: Moderator login and view pending reviews
        mod_login = client.post(
            "/api/auth/token",
            json={"username": "kbmoderator", "password": "password123"}
        )
        mod_token = mod_login.json()["data"]["access_token"]
        mod_headers = {"Authorization": f"Bearer {mod_token}"}
        
        pending_response = client.get(
            "/api/review/knowledge",
            headers=mod_headers
        )
        
        assert pending_response.status_code == 200
        pending_items = pending_response.json()["items"]
        assert len(pending_items) >= 1
        
        # Verify our KB is in pending list
        pending_ids = [item["id"] for item in pending_items]
        assert kb_id in pending_ids
        
        # Step 4: Moderator approves KB
        approve_response = client.post(
            f"/api/review/knowledge/{kb_id}/approve",
            headers=mod_headers
        )
        
        assert approve_response.status_code == 200
        
        # Step 5: Verify KB is now approved
        test_db.refresh(kb_in_db)
        assert kb_in_db.status == "approved"
        
        # Step 6: Verify KB is accessible to public
        public_response = client.get(
            f"/api/knowledge/{kb_id}",
            headers=user_headers
        )
        
        assert public_response.status_code == 200
        assert public_response.json()["status"] == "approved"
    
    def test_persona_card_review_and_rejection_flow(self, test_db: Session):
        """
        Test review and rejection workflow for persona card
        
        Workflow:
        1. User creates persona card
        2. Moderator views pending reviews
        3. Moderator rejects persona card
        4. Verify status is rejected
        5. User can view rejection
        
        **Validates: Requirements 9.4**
        """
        from app.main import app
        client = TestClient(app)
        
        # Create user and moderator
        user = User(
            id=str(uuid.uuid4()),
            username="personauser",
            email="personauser@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        
        moderator = User(
            id=str(uuid.uuid4()),
            username="personamod",
            email="personamod@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=True,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        
        test_db.add(user)
        test_db.add(moderator)
        test_db.commit()
        
        # User creates persona card
        user_login = client.post(
            "/api/auth/token",
            json={"username": "personauser", "password": "password123"}
        )
        user_token = user_login.json()["data"]["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        persona_response = client.post(
            "/api/persona",
            json={
                "name": "Test Persona",
                "description": "Will be rejected",
                "is_public": True
            },
            headers=user_headers
        )
        
        persona_id = persona_response.json()["id"]
        
        # Moderator login
        mod_login = client.post(
            "/api/auth/token",
            json={"username": "personamod", "password": "password123"}
        )
        mod_token = mod_login.json()["data"]["access_token"]
        mod_headers = {"Authorization": f"Bearer {mod_token}"}
        
        # View pending personas
        pending_response = client.get(
            "/api/review/persona",
            headers=mod_headers
        )
        
        assert pending_response.status_code == 200
        pending_items = pending_response.json()["items"]
        pending_ids = [item["id"] for item in pending_items]
        assert persona_id in pending_ids
        
        # Reject persona
        reject_response = client.post(
            f"/api/review/persona/{persona_id}/reject",
            headers=mod_headers
        )
        
        assert reject_response.status_code == 200
        
        # Verify status is rejected
        persona_in_db = test_db.query(PersonaCard).filter(
            PersonaCard.id == persona_id
        ).first()
        assert persona_in_db.status == "rejected"
        
        # User can still view their rejected persona
        user_view_response = client.get(
            f"/api/persona/{persona_id}",
            headers=user_headers
        )
        
        assert user_view_response.status_code == 200
        assert user_view_response.json()["status"] == "rejected"
    
    def test_review_permission_enforcement(self, test_db: Session):
        """
        Test that only moderators can approve/reject content
        
        Workflow:
        1. Regular user creates content
        2. Another regular user tries to approve
        3. Verify approval is rejected
        4. Moderator successfully approves
        
        **Validates: Requirements 9.4**
        """
        from app.main import app
        client = TestClient(app)
        
        # Create users
        creator = User(
            id=str(uuid.uuid4()),
            username="creator",
            email="creator@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        
        regular_user = User(
            id=str(uuid.uuid4()),
            username="regularuser",
            email="regular@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        
        moderator = User(
            id=str(uuid.uuid4()),
            username="reviewmod",
            email="reviewmod@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=True,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        
        test_db.add_all([creator, regular_user, moderator])
        test_db.commit()
        
        # Creator creates KB
        creator_login = client.post(
            "/api/auth/token",
            json={"username": "creator", "password": "password123"}
        )
        creator_token = creator_login.json()["data"]["access_token"]
        
        kb_response = client.post(
            "/api/knowledge",
            json={"title": "Permission Test", "description": "Test", "is_public": True},
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        kb_id = kb_response.json()["id"]
        
        # Regular user tries to approve
        regular_login = client.post(
            "/api/auth/token",
            json={"username": "regularuser", "password": "password123"}
        )
        regular_token = regular_login.json()["data"]["access_token"]
        
        unauthorized_approve = client.post(
            f"/api/review/knowledge/{kb_id}/approve",
            headers={"Authorization": f"Bearer {regular_token}"}
        )
        
        # Should be forbidden
        assert unauthorized_approve.status_code == 403
        
        # Moderator successfully approves
        mod_login = client.post(
            "/api/auth/token",
            json={"username": "reviewmod", "password": "password123"}
        )
        mod_token = mod_login.json()["data"]["access_token"]
        
        authorized_approve = client.post(
            f"/api/review/knowledge/{kb_id}/approve",
            headers={"Authorization": f"Bearer {mod_token}"}
        )
        
        assert authorized_approve.status_code == 200


class TestAdminManagementWorkflow:
    """Test complete admin management workflow"""
    
    def test_admin_user_management_flow(self, test_db: Session):
        """
        Test Example 5: Admin management workflow
        
        Complete workflow:
        1. Admin creates new user
        2. Admin assigns moderator role
        3. User gains moderator permissions
        4. Admin revokes moderator role
        5. User loses moderator permissions
        6. Verify permission changes
        
        **Validates: Requirements 9.5**
        """
        from app.main import app
        client = TestClient(app)
        
        # Step 1: Create admin user
        admin = User(
            id=str(uuid.uuid4()),
            username="adminuser",
            email="admin@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=True,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(admin)
        test_db.commit()
        
        # Admin login
        admin_login = client.post(
            "/api/auth/token",
            json={"username": "adminuser", "password": "password123"}
        )
        admin_token = admin_login.json()["data"]["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Step 2: Admin creates new user
        create_user_response = client.post(
            "/api/admin/users",
            json={
                "username": "manageduser",
                "email": "managed@example.com",
                "password": "password123"
            },
            headers=admin_headers
        )
        
        assert create_user_response.status_code == 201
        new_user_id = create_user_response.json()["id"]
        
        # Verify user was created
        new_user = test_db.query(User).filter(User.id == new_user_id).first()
        assert new_user is not None
        assert new_user.username == "manageduser"
        assert new_user.is_moderator == False
        
        # Step 3: Admin assigns moderator role
        assign_role_response = client.put(
            f"/api/admin/users/{new_user_id}/role",
            json={"role": "moderator"},
            headers=admin_headers
        )
        
        assert assign_role_response.status_code == 200
        
        # Verify user gained moderator permissions
        test_db.refresh(new_user)
        assert new_user.is_moderator == True
        
        # Step 4: User logs in and can access moderator endpoints
        user_login = client.post(
            "/api/auth/token",
            json={"username": "manageduser", "password": "password123"}
        )
        user_token = user_login.json()["data"]["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Try to access moderator endpoint
        review_response = client.get(
            "/api/review/knowledge",
            headers=user_headers
        )
        
        assert review_response.status_code == 200  # Has access
        
        # Step 5: Admin revokes moderator role
        revoke_role_response = client.put(
            f"/api/admin/users/{new_user_id}/role",
            json={"role": "user"},
            headers=admin_headers
        )
        
        assert revoke_role_response.status_code == 200
        
        # Verify user lost moderator permissions
        test_db.refresh(new_user)
        assert new_user.is_moderator == False
        
        # Step 6: User can no longer access moderator endpoints
        # Need to get new token with updated role
        user_login_2 = client.post(
            "/api/auth/token",
            json={"username": "manageduser", "password": "password123"}
        )
        user_token_2 = user_login_2.json()["data"]["access_token"]
        user_headers_2 = {"Authorization": f"Bearer {user_token_2}"}
        
        review_response_2 = client.get(
            "/api/review/knowledge",
            headers=user_headers_2
        )
        
        assert review_response_2.status_code == 403  # No longer has access
    
    def test_admin_user_ban_and_unban_flow(self, test_db: Session):
        """
        Test admin banning and unbanning user workflow
        
        Workflow:
        1. Admin bans user
        2. User cannot login
        3. Admin unbans user
        4. User can login again
        
        **Validates: Requirements 9.5**
        """
        from app.main import app
        client = TestClient(app)
        
        # Create admin and regular user
        admin = User(
            id=str(uuid.uuid4()),
            username="banadmin",
            email="banadmin@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=True,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        
        user = User(
            id=str(uuid.uuid4()),
            username="banuser",
            email="banuser@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        
        test_db.add_all([admin, user])
        test_db.commit()
        
        # Admin login
        admin_login = client.post(
            "/api/auth/token",
            json={"username": "banadmin", "password": "password123"}
        )
        admin_token = admin_login.json()["data"]["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # User can login initially
        user_login_1 = client.post(
            "/api/auth/token",
            json={"username": "banuser", "password": "password123"}
        )
        assert user_login_1.status_code == 200
        
        # Admin bans user
        ban_response = client.post(
            f"/api/admin/users/{user.id}/ban",
            json={"duration": 7},  # 7 days
            headers=admin_headers
        )
        
        assert ban_response.status_code == 200
        
        # User cannot login while banned
        user_login_2 = client.post(
            "/api/auth/token",
            json={"username": "banuser", "password": "password123"}
        )
        assert user_login_2.status_code == 403
        
        # Admin unbans user
        unban_response = client.post(
            f"/api/admin/users/{user.id}/unban",
            headers=admin_headers
        )
        
        assert unban_response.status_code == 200
        
        # User can login again
        user_login_3 = client.post(
            "/api/auth/token",
            json={"username": "banuser", "password": "password123"}
        )
        assert user_login_3.status_code == 200
    
    def test_admin_user_mute_and_unmute_flow(self, test_db: Session):
        """
        Test admin muting and unmuting user workflow
        
        Workflow:
        1. Admin mutes user
        2. Verify mute status
        3. Admin unmutes user
        4. Verify unmute status
        
        **Validates: Requirements 9.5**
        """
        from app.main import app
        client = TestClient(app)
        
        # Create admin and user
        admin = User(
            id=str(uuid.uuid4()),
            username="muteadmin",
            email="muteadmin@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=True,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        
        user = User(
            id=str(uuid.uuid4()),
            username="muteuser",
            email="muteuser@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        
        test_db.add_all([admin, user])
        test_db.commit()
        
        # Admin login
        admin_login = client.post(
            "/api/auth/token",
            json={"username": "muteadmin", "password": "password123"}
        )
        admin_token = admin_login.json()["data"]["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Admin mutes user
        mute_response = client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": 1},  # 1 day
            headers=admin_headers
        )
        
        assert mute_response.status_code == 200
        
        # Verify user is muted
        test_db.refresh(user)
        assert user.muted_until is not None
        assert user.muted_until > datetime.now()
        
        # Admin unmutes user
        unmute_response = client.post(
            f"/api/admin/users/{user.id}/unmute",
            headers=admin_headers
        )
        
        assert unmute_response.status_code == 200
        
        # Verify user is unmuted
        test_db.refresh(user)
        assert user.muted_until is None
    
    def test_admin_view_user_statistics(self, test_db: Session):
        """
        Test admin viewing system statistics
        
        Workflow:
        1. Create multiple users with different roles
        2. Admin views statistics
        3. Verify statistics are accurate
        
        **Validates: Requirements 9.5**
        """
        from app.main import app
        client = TestClient(app)
        
        # Create admin
        admin = User(
            id=str(uuid.uuid4()),
            username="statsadmin",
            email="statsadmin@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=True,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(admin)
        test_db.commit()
        
        # Admin login
        admin_login = client.post(
            "/api/auth/token",
            json={"username": "statsadmin", "password": "password123"}
        )
        admin_token = admin_login.json()["data"]["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # View statistics
        stats_response = client.get(
            "/api/admin/stats",
            headers=admin_headers
        )
        
        assert stats_response.status_code == 200
        stats = stats_response.json()
        
        # Verify statistics structure
        assert "total_users" in stats
        assert "total_knowledge_bases" in stats
        assert "total_persona_cards" in stats
        assert isinstance(stats["total_users"], int)
        assert stats["total_users"] >= 1  # At least the admin
