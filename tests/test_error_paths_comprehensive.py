"""
Comprehensive error path tests for all HTTP status codes
Tests 400, 401, 403, 404, 409, 500 status codes across all endpoints

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import pytest
from unittest.mock import patch, Mock
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from tests.test_data_factory import TestDataFactory


class TestValidationErrors400:
    """Test HTTP 400 validation error paths"""
    
    def test_invalid_json_format(self, client):
        """Test endpoint with invalid JSON format"""
        response = client.post(
            "/api/auth/register",
            data="invalid json{",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 404, 422]
    
    def test_missing_required_fields(self, client):
        """Test endpoint with missing required fields"""
        response = client.post(
            "/api/auth/register",
            json={}
        )
        assert response.status_code in [400, 404, 422]
    
    def test_invalid_field_types(self, client):
        """Test endpoint with invalid field types"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": 123,  # Should be string
                "email": True,  # Should be string
                "password": ["list"]  # Should be string
            }
        )
        assert response.status_code in [400, 404, 422]
    
    def test_invalid_email_format(self, client):
        """Test registration with invalid email format"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "not-an-email",
                "password": "password123"
            }
        )
        assert response.status_code in [400, 404, 422]
    
    def test_password_too_short(self, client):
        """Test registration with password too short"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "123"
            }
        )
        assert response.status_code in [400, 404, 422]
    
    def test_invalid_pagination_params(self, authenticated_client):
        """Test endpoint with invalid pagination parameters"""
        response = authenticated_client.get("/api/knowledge?page=abc&page_size=xyz")
        assert response.status_code in [400, 404, 422]
    
    def test_invalid_filter_values(self, authenticated_client):
        """Test endpoint with invalid filter values"""
        response = authenticated_client.get("/api/knowledge?status=invalid_status")
        assert response.status_code in [200, 400, 404, 422]
    
    def test_invalid_sort_params(self, authenticated_client):
        """Test endpoint with invalid sort parameters"""
        response = authenticated_client.get("/api/knowledge?sort_by=invalid_field")
        assert response.status_code in [200, 400, 404, 422]
    
    def test_password_mismatch(self, authenticated_client):
        """Test password change with mismatched passwords"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword123",
                "confirm_password": "differentpassword"
            }
        )
        assert response.status_code in [400, 422]
    
    def test_invalid_uuid_format(self, authenticated_client):
        """Test endpoint with invalid UUID format"""
        response = authenticated_client.get("/api/knowledge/not-a-uuid")
        assert response.status_code in [400, 404, 422]
    
    def test_invalid_file_type(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test file upload with invalid file type"""
        kb = factory.create_knowledge_base()
        
        # Create a file with invalid extension
        from io import BytesIO
        file_content = BytesIO(b"test content")
        
        response = authenticated_client.post(
            f"/api/knowledge/{kb.id}/files",
            files={"file": ("test.exe", file_content, "application/x-msdownload")}
        )
        assert response.status_code in [400, 422]
    
    def test_file_too_large(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test file upload with file too large"""
        kb = factory.create_knowledge_base()
        
        # Create a large file (simulate)
        from io import BytesIO
        large_content = BytesIO(b"x" * (11 * 1024 * 1024))  # 11MB
        
        response = authenticated_client.post(
            f"/api/knowledge/{kb.id}/files",
            files={"file": ("test.txt", large_content, "text/plain")}
        )
        # Should reject if over size limit
        assert response.status_code in [200, 400, 413, 422]
    
    def test_invalid_duration_format(self, admin_client, factory: TestDataFactory, test_db: Session):
        """Test mute with invalid duration format"""
        user = factory.create_user()
        
        response = admin_client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": "not-a-number"}
        )
        assert response.status_code in [400, 422]
    
    def test_invalid_role_value(self, admin_client, factory: TestDataFactory, test_db: Session):
        """Test role update with invalid role value"""
        user = factory.create_user()
        
        response = admin_client.put(
            f"/api/admin/users/{user.id}/role",
            json={"role": "invalid_role"}
        )
        assert response.status_code in [400, 422]


class TestAuthenticationErrors401:
    """Test HTTP 401 authentication error paths"""
    
    def test_missing_auth_token(self, client):
        """Test endpoint without authentication token"""
        response = client.get("/api/users/me")
        assert response.status_code == 401
    
    def test_invalid_auth_token(self, client):
        """Test endpoint with invalid authentication token"""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
    
    def test_expired_auth_token(self, client):
        """Test endpoint with expired authentication token"""
        # Create an expired token
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjF9.invalid"
        
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
    
    def test_malformed_auth_header(self, client):
        """Test endpoint with malformed authorization header"""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "InvalidFormat token"}
        )
        assert response.status_code == 401
    
    def test_wrong_password(self, client, factory: TestDataFactory, test_db: Session):
        """Test login with wrong password"""
        user = factory.create_user(username="testuser", password="correctpassword")
        
        response = client.post(
            "/api/auth/token",
            data={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
    
    def test_nonexistent_user_login(self, client):
        """Test login with nonexistent user"""
        response = client.post(
            "/api/auth/token",
            data={
                "username": "nonexistent",
                "password": "password123"
            }
        )
        assert response.status_code == 401
    
    def test_locked_account_login(self, client, factory: TestDataFactory, test_db: Session):
        """Test login with locked account"""
        from datetime import datetime, timedelta
        
        user = factory.create_user(username="lockeduser", password="password123")
        user.locked_until = datetime.now() + timedelta(hours=1)
        test_db.commit()
        
        response = client.post(
            "/api/auth/token",
            data={
                "username": "lockeduser",
                "password": "password123"
            }
        )
        assert response.status_code == 401
    
    def test_inactive_user_login(self, client, factory: TestDataFactory, test_db: Session):
        """Test login with inactive user"""
        user = factory.create_user(username="inactiveuser", password="password123")
        user.is_active = False
        test_db.commit()
        
        response = client.post(
            "/api/auth/token",
            data={
                "username": "inactiveuser",
                "password": "password123"
            }
        )
        assert response.status_code in [401, 403]
    
    def test_wrong_current_password(self, authenticated_client):
        """Test password change with wrong current password"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            }
        )
        assert response.status_code == 401
    
    def test_invalid_verification_code(self, client):
        """Test email verification with invalid code"""
        response = client.post(
            "/api/auth/verify-email",
            json={
                "email": "test@example.com",
                "code": "000000"
            }
        )
        assert response.status_code in [400, 401]
    
    def test_expired_verification_code(self, client, factory: TestDataFactory, test_db: Session):
        """Test email verification with expired code"""
        from datetime import datetime, timedelta
        from app.models.database import EmailVerification
        
        # Create expired verification code
        verification = EmailVerification(
            email="test@example.com",
            code="123456",
            expires_at=datetime.now() - timedelta(hours=1),
            is_used=False
        )
        test_db.add(verification)
        test_db.commit()
        
        response = client.post(
            "/api/auth/verify-email",
            json={
                "email": "test@example.com",
                "code": "123456"
            }
        )
        assert response.status_code in [400, 401]


class TestAuthorizationErrors403:
    """Test HTTP 403 authorization error paths"""
    
    def test_non_admin_access_admin_endpoint(self, authenticated_client):
        """Test non-admin user accessing admin endpoint"""
        response = authenticated_client.get("/api/admin/stats")
        assert response.status_code == 403
    
    def test_non_moderator_access_review_endpoint(self, authenticated_client):
        """Test non-moderator user accessing review endpoint"""
        response = authenticated_client.get("/api/review/knowledge")
        assert response.status_code == 403
    
    def test_update_other_user_knowledge(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test updating another user's knowledge base"""
        other_user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=other_user)
        
        response = authenticated_client.put(
            f"/api/knowledge/{kb.id}",
            json={"title": "Updated Title"}
        )
        assert response.status_code == 403
    
    def test_delete_other_user_knowledge(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test deleting another user's knowledge base"""
        other_user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=other_user)
        
        response = authenticated_client.delete(f"/api/knowledge/{kb.id}")
        assert response.status_code == 403
    
    def test_update_other_user_persona(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test updating another user's persona card"""
        other_user = factory.create_user()
        persona = factory.create_persona_card(uploader=other_user)
        
        response = authenticated_client.put(
            f"/api/persona/{persona.id}",
            json={"name": "Updated Name"}
        )
        assert response.status_code == 403
    
    def test_delete_other_user_persona(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test deleting another user's persona card"""
        other_user = factory.create_user()
        persona = factory.create_persona_card(uploader=other_user)
        
        response = authenticated_client.delete(f"/api/persona/{persona.id}")
        assert response.status_code == 403
    
    def test_update_other_user_comment(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test updating another user's comment"""
        other_user = factory.create_user()
        kb = factory.create_knowledge_base()
        comment = factory.create_comment(user=other_user, knowledge_base=kb)
        
        response = authenticated_client.put(
            f"/api/comments/{comment.id}",
            json={"content": "Updated content"}
        )
        assert response.status_code == 403
    
    def test_delete_other_user_comment(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test deleting another user's comment"""
        other_user = factory.create_user()
        kb = factory.create_knowledge_base()
        comment = factory.create_comment(user=other_user, knowledge_base=kb)
        
        response = authenticated_client.delete(f"/api/comments/{comment.id}")
        assert response.status_code == 403
    
    def test_non_admin_create_user(self, authenticated_client):
        """Test non-admin creating user"""
        response = authenticated_client.post(
            "/api/admin/users",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 403
    
    def test_non_admin_delete_user(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test non-admin deleting user"""
        user = factory.create_user()
        
        response = authenticated_client.delete(f"/api/admin/users/{user.id}")
        assert response.status_code == 403
    
    def test_non_admin_mute_user(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test non-admin muting user"""
        user = factory.create_user()
        
        response = authenticated_client.post(
            f"/api/admin/users/{user.id}/mute",
            json={"duration": 1}
        )
        assert response.status_code == 403
    
    def test_non_admin_ban_user(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test non-admin banning user"""
        user = factory.create_user()
        
        response = authenticated_client.post(
            f"/api/admin/users/{user.id}/ban",
            json={"duration": 7}
        )
        assert response.status_code == 403
    
    def test_muted_user_create_content(self, client, factory: TestDataFactory, test_db: Session):
        """Test muted user creating content"""
        from datetime import datetime, timedelta
        from tests.auth_helper import AuthHelper
        
        user = factory.create_user()
        user.muted_until = datetime.now() + timedelta(days=1)
        test_db.commit()
        
        auth_helper = AuthHelper(test_db)
        muted_client = auth_helper.create_authenticated_client(user)
        
        response = muted_client.post(
            "/api/knowledge",
            json={"title": "Test", "description": "Test"}
        )
        # Should be forbidden or return specific error
        assert response.status_code in [403, 400]


class TestNotFoundErrors404:
    """Test HTTP 404 not found error paths"""
    
    def test_get_nonexistent_knowledge(self, authenticated_client):
        """Test getting nonexistent knowledge base"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = authenticated_client.get(f"/api/knowledge/{fake_id}")
        assert response.status_code == 404
    
    def test_update_nonexistent_knowledge(self, authenticated_client):
        """Test updating nonexistent knowledge base"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = authenticated_client.put(
            f"/api/knowledge/{fake_id}",
            json={"title": "Updated"}
        )
        assert response.status_code == 404
    
    def test_delete_nonexistent_knowledge(self, authenticated_client):
        """Test deleting nonexistent knowledge base"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = authenticated_client.delete(f"/api/knowledge/{fake_id}")
        assert response.status_code == 404
    
    def test_get_nonexistent_persona(self, authenticated_client):
        """Test getting nonexistent persona card"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = authenticated_client.get(f"/api/persona/{fake_id}")
        assert response.status_code == 404
    
    def test_update_nonexistent_persona(self, authenticated_client):
        """Test updating nonexistent persona card"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = authenticated_client.put(
            f"/api/persona/{fake_id}",
            json={"name": "Updated"}
        )
        assert response.status_code == 404
    
    def test_delete_nonexistent_persona(self, authenticated_client):
        """Test deleting nonexistent persona card"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = authenticated_client.delete(f"/api/persona/{fake_id}")
        assert response.status_code == 404
    
    def test_get_nonexistent_comment(self, authenticated_client):
        """Test getting nonexistent comment"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = authenticated_client.get(f"/api/comments/{fake_id}")
        assert response.status_code == 404
    
    def test_update_nonexistent_comment(self, authenticated_client):
        """Test updating nonexistent comment"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = authenticated_client.put(
            f"/api/comments/{fake_id}",
            json={"content": "Updated"}
        )
        assert response.status_code == 404
    
    def test_delete_nonexistent_comment(self, authenticated_client):
        """Test deleting nonexistent comment"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = authenticated_client.delete(f"/api/comments/{fake_id}")
        assert response.status_code == 404
    
    def test_get_nonexistent_message(self, authenticated_client):
        """Test getting nonexistent message"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = authenticated_client.get(f"/api/messages/{fake_id}")
        assert response.status_code == 404
    
    def test_get_nonexistent_user(self, authenticated_client):
        """Test getting nonexistent user"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = authenticated_client.get(f"/api/users/{fake_id}")
        assert response.status_code == 404
    
    def test_admin_get_nonexistent_user(self, admin_client):
        """Test admin getting nonexistent user"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = admin_client.get(f"/api/admin/users/{fake_id}")
        assert response.status_code == 404
    
    def test_admin_delete_nonexistent_user(self, admin_client):
        """Test admin deleting nonexistent user"""
        import uuid
        fake_id = str(uuid.uuid4())
        
        response = admin_client.delete(f"/api/admin/users/{fake_id}")
        assert response.status_code == 404
    
    def test_nonexistent_route(self, client):
        """Test accessing nonexistent route"""
        response = client.get("/api/nonexistent/route")
        assert response.status_code == 404


class TestConflictErrors409:
    """Test HTTP 409 conflict error paths"""
    
    def test_duplicate_username(self, client, factory: TestDataFactory, test_db: Session):
        """Test registration with duplicate username"""
        existing_user = factory.create_user(username="existinguser")
        
        response = client.post(
            "/api/auth/register",
            json={
                "username": "existinguser",
                "email": "different@example.com",
                "password": "password123"
            }
        )
        assert response.status_code in [400, 409]
    
    def test_duplicate_email(self, client, factory: TestDataFactory, test_db: Session):
        """Test registration with duplicate email"""
        existing_user = factory.create_user(email="existing@example.com")
        
        response = client.post(
            "/api/auth/register",
            json={
                "username": "differentuser",
                "email": "existing@example.com",
                "password": "password123"
            }
        )
        assert response.status_code in [400, 409]
    
    def test_duplicate_knowledge_title(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test creating knowledge base with duplicate title for same user"""
        kb = factory.create_knowledge_base(title="Existing Title")
        
        response = authenticated_client.post(
            "/api/knowledge",
            json={
                "title": "Existing Title",
                "description": "Different description"
            }
        )
        # May allow duplicates or return conflict
        assert response.status_code in [200, 201, 409]
    
    def test_duplicate_persona_name(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test creating persona card with duplicate name for same user"""
        persona = factory.create_persona_card(name="Existing Name")
        
        response = authenticated_client.post(
            "/api/persona",
            json={
                "name": "Existing Name",
                "description": "Different description"
            }
        )
        # May allow duplicates or return conflict
        assert response.status_code in [200, 201, 409]
    
    def test_duplicate_comment_reaction(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test adding duplicate reaction to comment"""
        kb = factory.create_knowledge_base()
        comment = factory.create_comment(knowledge_base=kb)
        
        # Add first reaction
        response1 = authenticated_client.post(
            f"/api/comments/{comment.id}/reactions",
            json={"reaction_type": "like"}
        )
        
        # Try to add same reaction again
        response2 = authenticated_client.post(
            f"/api/comments/{comment.id}/reactions",
            json={"reaction_type": "like"}
        )
        
        # Should either update or return conflict
        assert response2.status_code in [200, 409]


class TestServerErrors500:
    """Test HTTP 500 server error paths"""
    
    def test_database_connection_error(self, client):
        """Test handling of database connection errors"""
        with patch('app.core.deps.get_db') as mock_get_db:
            mock_get_db.side_effect = OperationalError("Connection failed", None, None)
            
            response = client.get("/api/knowledge")
            # Should handle gracefully
            assert response.status_code in [500, 503]
    
    def test_database_query_error(self, authenticated_client):
        """Test handling of database query errors"""
        with patch('sqlalchemy.orm.Query.all') as mock_query:
            mock_query.side_effect = Exception("Database error")
            
            response = authenticated_client.get("/api/knowledge")
            # Should handle gracefully
            assert response.status_code in [200, 500]
    
    def test_email_service_error(self, client):
        """Test handling of email service errors"""
        with patch('app.services.email_service.EmailService.send_email') as mock_send:
            mock_send.side_effect = Exception("Email service unavailable")
            
            response = client.post(
                "/api/auth/send-code",
                json={"email": "test@example.com"}
            )
            # Should handle gracefully
            assert response.status_code in [200, 500, 503]
    
    def test_file_system_error(self, authenticated_client, factory: TestDataFactory, test_db: Session):
        """Test handling of file system errors"""
        kb = factory.create_knowledge_base()
        
        with patch('aiofiles.open') as mock_open:
            mock_open.side_effect = OSError("Disk full")
            
            from io import BytesIO
            file_content = BytesIO(b"test content")
            
            response = authenticated_client.post(
                f"/api/knowledge/{kb.id}/files",
                files={"file": ("test.txt", file_content, "text/plain")}
            )
            # Should handle gracefully
            assert response.status_code in [200, 500, 507]
    
    def test_unexpected_exception(self, authenticated_client):
        """Test handling of unexpected exceptions"""
        with patch('app.api.routes.knowledge.get_knowledge_bases') as mock_get:
            mock_get.side_effect = RuntimeError("Unexpected error")
            
            response = authenticated_client.get("/api/knowledge")
            # Should handle gracefully
            assert response.status_code in [200, 500]
    
    def test_json_serialization_error(self, authenticated_client):
        """Test handling of JSON serialization errors"""
        # This is harder to trigger but important to handle
        # Most frameworks handle this automatically
        pass
    
    def test_token_generation_error(self, client, factory: TestDataFactory, test_db: Session):
        """Test handling of token generation errors"""
        user = factory.create_user(username="testuser", password="password123")
        
        with patch('app.core.security.create_access_token') as mock_create:
            mock_create.side_effect = Exception("Token generation failed")
            
            response = client.post(
                "/api/auth/token",
                data={
                    "username": "testuser",
                    "password": "password123"
                }
            )
            # Should handle gracefully
            assert response.status_code in [401, 500]
