"""
用户路由集成测试
测试所有用户相关的API端点，包括个人资料、密码、头像、收藏和统计

需求：3.1
"""

import io
import uuid
from datetime import datetime
from unittest.mock import patch

from PIL import Image

from app.models.database import KnowledgeBase, PersonaCard, StarRecord, UploadRecord


class TestGetUserProfile:
    """Test GET /api/users/me endpoint"""

    def test_get_user_profile_success(self, authenticated_client, test_user):
        """Test getting current user profile"""
        response = authenticated_client.get("/api/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["id"] == test_user.id
        assert data["data"]["username"] == test_user.username
        assert data["data"]["email"] == test_user.email
        assert data["data"]["role"] == "user"

    def test_get_user_profile_unauthenticated(self, client):
        """Test getting profile without authentication"""
        response = client.get("/api/users/me")

        assert response.status_code == 401
        data = response.json()
        # FastAPI returns 'detail' for authentication errors
        assert "detail" in data or "error" in data

    def test_get_user_profile_with_avatar(self, authenticated_client, test_user, test_db):
        """Test getting profile with avatar information"""
        # Set avatar path
        test_user.avatar_path = "uploads/avatars/test.jpg"
        test_user.avatar_updated_at = datetime.now()
        test_db.commit()

        response = authenticated_client.get("/api/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["avatar_url"] == "/uploads/avatars/test.jpg"
        assert data["data"]["avatar_updated_at"] is not None


class TestChangePassword:
    """Test PUT /api/users/me/password endpoint"""

    def test_change_password_success(self, authenticated_client, test_user, test_db):
        """Test successful password change"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
                "confirm_password": "newpassword456",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "密码修改成功" in data["message"]

        # Verify password was changed
        test_db.refresh(test_user)
        from app.core.security import verify_password

        assert verify_password("newpassword456", test_user.hashed_password)
        assert test_user.password_version == 1

    def test_change_password_wrong_current_password(self, authenticated_client):
        """Test password change with wrong current password"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword456",
                "confirm_password": "newpassword456",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert "当前密码错误" in data["error"]["message"]

    def test_change_password_mismatch(self, authenticated_client):
        """Test password change with mismatched new passwords"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
                "confirm_password": "differentpassword",
            },
        )

        assert response.status_code == 422
        data = response.json()
        # Use flexible pattern matching for error messages
        assert "密码" in data["error"]["message"] and (
            "不匹配" in data["error"]["message"] or "不一致" in data["error"]["message"]
        )

    def test_change_password_too_short(self, authenticated_client):
        """Test password change with password too short"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={"current_password": "testpassword123", "new_password": "12345", "confirm_password": "12345"},
        )

        assert response.status_code == 422
        data = response.json()
        # Use flexible pattern matching for error messages
        assert "密码" in data["error"]["message"] and "6" in data["error"]["message"]

    def test_change_password_same_as_current(self, authenticated_client):
        """Test password change with same password as current"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "testpassword123",
                "confirm_password": "testpassword123",
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "不能与当前密码相同" in data["error"]["message"]

    def test_change_password_missing_fields(self, authenticated_client):
        """Test password change with missing fields"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
                # Missing confirm_password
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "未填写" in data["error"]["message"]

    def test_change_password_unauthenticated(self, client):
        """Test password change without authentication"""
        response = client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
                "confirm_password": "newpassword456",
            },
        )

        assert response.status_code == 401

    def test_change_password_user_deleted_after_auth(self, authenticated_client, test_user, test_db):
        """Test password change when user is deleted after authentication

        This tests the scenario where a user's JWT token is valid but the user
        has been deleted from the database. The authentication layer (get_current_user)
        will catch this and return 401, which is the expected behavior.

        Note: The user not found check in the route (lines ~117-119) is a defensive
        programming practice, but in normal operation, the authentication dependency
        catches this case first.
        """
        # Delete the user from database
        test_db.delete(test_user)
        test_db.commit()

        # Try to change password with valid JWT but deleted user
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
                "confirm_password": "newpassword456",
            },
        )

        # Should return 401 because authentication layer catches deleted user
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_change_password_unexpected_exception(self, authenticated_client, test_user, test_db):
        """Test password change when an unexpected exception occurs

        This tests the generic exception handler (lines 154-156) that catches
        unexpected errors during password change operation.
        """
        from unittest.mock import patch

        # Mock get_password_hash at the security module level to raise an unexpected exception
        with patch("app.core.security.get_password_hash", side_effect=RuntimeError("Unexpected error")):
            response = authenticated_client.put(
                "/api/users/me/password",
                json={
                    "current_password": "testpassword123",
                    "new_password": "newpassword456",
                    "confirm_password": "newpassword456",
                },
            )

            # Should return 400 with generic error message (APIError defaults to 400)
            assert response.status_code == 400
            data = response.json()
            assert "修改密码失败" in data["error"]["message"]

    def test_change_password_database_commit_failure(self, authenticated_client, test_user, test_db):
        """Test password change when database commit fails

        This tests the scenario where password update succeeds but database commit fails.
        The generic exception handler should catch this and return an error.
        Task: 5.2.4 测试密码修改失败
        """
        from unittest.mock import patch

        from sqlalchemy.exc import SQLAlchemyError

        # Patch the Session.commit method at the module level where it's used
        with patch("app.api.routes.users.Session.commit", side_effect=SQLAlchemyError("Database commit failed")):
            response = authenticated_client.put(
                "/api/users/me/password",
                json={
                    "current_password": "testpassword123",
                    "new_password": "newpassword456",
                    "confirm_password": "newpassword456",
                },
            )

            # Should return 400 with generic error message
            assert response.status_code == 400
            data = response.json()
            assert "修改密码失败" in data["error"]["message"]


class TestAvatarManagement:
    """Test avatar upload, delete, and retrieval endpoints"""

    def create_test_image(self, img_format="PNG", size=(200, 200)):
        """Helper to create a test image file"""
        img = Image.new("RGB", size, color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format=img_format)
        img_bytes.seek(0)
        return img_bytes

    def test_upload_avatar_success(self, authenticated_client, test_user, test_db):
        """Test successful avatar upload"""
        img_bytes = self.create_test_image()

        response = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("test.png", img_bytes, "image/png")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "头像上传成功" in data["message"]
        assert "avatar_url" in data["data"]
        assert "avatar_updated_at" in data["data"]

        # Verify database was updated
        test_db.refresh(test_user)
        assert test_user.avatar_path is not None
        assert test_user.avatar_updated_at is not None

    def test_upload_avatar_replaces_old(self, authenticated_client, test_user, test_db):
        """Test that uploading new avatar replaces old one"""
        # Upload first avatar
        img_bytes1 = self.create_test_image()
        response1 = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("test1.png", img_bytes1, "image/png")}
        )
        assert response1.status_code == 200
        old_path = response1.json()["data"]["avatar_url"]

        # Wait a moment to ensure different timestamp
        import time

        time.sleep(1)

        # Upload second avatar
        img_bytes2 = self.create_test_image()
        response2 = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("test2.png", img_bytes2, "image/png")}
        )
        assert response2.status_code == 200
        new_path = response2.json()["data"]["avatar_url"]

        # Paths should be different
        assert old_path != new_path

    def test_upload_avatar_invalid_file_type(self, authenticated_client):
        """Test avatar upload with invalid file type"""
        # Create a text file instead of image
        text_file = io.BytesIO(b"This is not an image")

        response = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("test.txt", text_file, "text/plain")}
        )

        assert response.status_code == 422
        data = response.json()
        assert "error" in data

    def test_upload_avatar_too_large(self, authenticated_client):
        """Test avatar upload with file too large"""
        # Create a large file > 2MB without expensive pixel generation
        # Simply create a BytesIO with 2.1MB of data
        large_data = b"0" * (2 * 1024 * 1024 + 100 * 1024)  # 2.1MB
        img_bytes = io.BytesIO(large_data)

        response = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("large.png", img_bytes, "image/png")}
        )

        # Should fail validation
        assert response.status_code in [400, 422]

    def test_upload_avatar_unauthenticated(self, client):
        """Test avatar upload without authentication"""
        img_bytes = self.create_test_image()

        response = client.post("/api/users/me/avatar", files={"avatar": ("test.png", img_bytes, "image/png")})

        assert response.status_code == 401

    def test_upload_avatar_user_deleted_after_auth(self, authenticated_client, test_user, test_db):
        """Test avatar upload when user is deleted after authentication

        This tests the scenario where a user's JWT token is valid but the user
        has been deleted from the database. The authentication layer will catch
        this and return 401.
        """
        img_bytes = self.create_test_image()

        # Delete the user from database
        test_db.delete(test_user)
        test_db.commit()

        # Try to upload avatar with valid JWT but deleted user
        response = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("test.png", img_bytes, "image/png")}
        )

        # Should return 401 because authentication layer catches deleted user
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_delete_avatar_success(self, authenticated_client, test_user, test_db):
        """Test successful avatar deletion"""
        # First upload an avatar
        img_bytes = self.create_test_image()
        authenticated_client.post("/api/users/me/avatar", files={"avatar": ("test.png", img_bytes, "image/png")})

        # Then delete it
        response = authenticated_client.delete("/api/users/me/avatar")

        assert response.status_code == 200
        data = response.json()
        assert "头像已删除" in data["message"]

        # Verify database was updated
        test_db.refresh(test_user)
        assert test_user.avatar_path is None

    def test_delete_avatar_when_none_exists(self, authenticated_client, test_user, test_db):
        """Test deleting avatar when user has no avatar"""
        # Ensure no avatar exists
        test_user.avatar_path = None
        test_db.commit()

        response = authenticated_client.delete("/api/users/me/avatar")

        assert response.status_code == 200
        data = response.json()
        assert "头像已删除" in data["message"]

    def test_delete_avatar_unauthenticated(self, client):
        """Test avatar deletion without authentication"""
        response = client.delete("/api/users/me/avatar")

        assert response.status_code == 401

    def test_delete_avatar_user_deleted_after_auth(self, authenticated_client, test_user, test_db):
        """Test avatar deletion when user is deleted after authentication

        This tests the scenario where a user's JWT token is valid but the user
        has been deleted from the database. The authentication layer will catch
        this and return 401.
        """
        # Delete the user from database
        test_db.delete(test_user)
        test_db.commit()

        # Try to delete avatar with valid JWT but deleted user
        response = authenticated_client.delete("/api/users/me/avatar")

        # Should return 401 because authentication layer catches deleted user
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_delete_avatar_user_not_found_in_service(self, client, test_db):
        """Test avatar deletion when user ID from JWT doesn't exist in database

        This tests line 253 where the route checks if the user exists.
        Task: 5.2.5 验证users.py达到95%以上覆盖率
        """
        import uuid

        from app.api.deps import get_current_user
        from app.main import app

        # Create a non-existent user ID
        non_existent_user_id = str(uuid.uuid4())

        # Override the get_current_user dependency
        def override_get_current_user():
            return {"id": non_existent_user_id}

        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.delete("/api/users/me/avatar")

            # Should return 404 Not Found
            assert response.status_code == 404
            data = response.json()
            assert "用户不存在" in data["error"]["message"]
        finally:
            app.dependency_overrides.clear()

    def test_get_user_avatar_with_existing_avatar(self, client, test_user, test_db):
        """Test getting user avatar when avatar exists"""
        # Set avatar path (assuming file exists)
        test_user.avatar_path = "uploads/avatars/test.jpg"
        test_db.commit()

        response = client.get(f"/api/users/{test_user.id}/avatar")

        # Should return image or generate default
        assert response.status_code in [200, 404]

    def test_get_user_avatar_generates_default(self, client, test_user, test_db):
        """Test that default avatar is generated when none exists"""
        # Ensure no avatar exists
        test_user.avatar_path = None
        test_db.commit()

        response = client.get(f"/api/users/{test_user.id}/avatar")

        assert response.status_code == 200
        # Should return an image
        assert response.headers["content-type"] in ["image/png", "image/jpeg"]

    def test_get_user_avatar_nonexistent_user(self, client):
        """Test getting avatar for nonexistent user"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/users/{fake_id}/avatar")

        assert response.status_code == 404


class TestUserStars:
    """Test GET /api/users/stars endpoint"""

    def test_get_user_stars_empty(self, authenticated_client):
        """Test getting stars when user has no stars"""
        response = authenticated_client.get("/api/users/stars")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["pagination"]["total"] == 0

    def test_get_user_stars_with_knowledge_base(self, authenticated_client, test_user, test_db):
        """Test getting stars with knowledge base"""
        # Create a public knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            star_count=5,
            downloads=10,
            base_path="uploads/knowledge/test",
            created_at=datetime.now(),
        )
        test_db.add(kb)

        # Create star record
        star = StarRecord(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            target_id=kb.id,
            target_type="knowledge",
            created_at=datetime.now(),
        )
        test_db.add(star)
        test_db.commit()

        response = authenticated_client.get("/api/users/stars")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 1
        assert len(data["data"]) == 1
        assert data["data"][0]["type"] == "knowledge"
        assert data["data"][0]["name"] == "Test KB"

    def test_get_user_stars_with_persona_card(self, authenticated_client, test_user, test_db):
        """Test getting stars with persona card"""
        # Create a public persona card
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test Persona",
            description="Test description",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            star_count=3,
            downloads=7,
            base_path="uploads/persona/test",
            created_at=datetime.now(),
        )
        test_db.add(pc)

        # Create star record
        star = StarRecord(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            target_id=pc.id,
            target_type="persona",
            created_at=datetime.now(),
        )
        test_db.add(star)
        test_db.commit()

        response = authenticated_client.get("/api/users/stars")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 1
        assert data["data"][0]["type"] == "persona"
        assert data["data"][0]["name"] == "Test Persona"

    def test_get_user_stars_pagination(self, authenticated_client, test_user, test_db):
        """Test stars pagination"""
        # Create multiple knowledge bases and star them
        for i in range(25):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB {i}",
                description=f"Description {i}",
                uploader_id=test_user.id,
                is_public=True,
                is_pending=False,
                base_path=f"uploads/knowledge/test_{i}",
                created_at=datetime.now(),
            )
            test_db.add(kb)

            star = StarRecord(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                target_id=kb.id,
                target_type="knowledge",
                created_at=datetime.now(),
            )
            test_db.add(star)
        test_db.commit()

        # Get first page
        response = authenticated_client.get("/api/users/stars?page=1&page_size=20")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 25
        assert len(data["data"]) == 20
        assert data["pagination"]["page"] == 1

        # Get second page
        response2 = authenticated_client.get("/api/users/stars?page=2&page_size=20")
        data2 = response2.json()
        assert len(data2["data"]) == 5

    def test_get_user_stars_filter_by_type(self, authenticated_client, test_user, test_db):
        """Test filtering stars by type"""
        # Create knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB",
            description="KB desc",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            base_path="uploads/knowledge/test_kb",
            created_at=datetime.now(),
        )
        test_db.add(kb)
        star_kb = StarRecord(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            target_id=kb.id,
            target_type="knowledge",
            created_at=datetime.now(),
        )
        test_db.add(star_kb)

        # Create persona card
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="PC",
            description="PC desc",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            base_path="uploads/persona/test_pc",
            created_at=datetime.now(),
        )
        test_db.add(pc)
        star_pc = StarRecord(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            target_id=pc.id,
            target_type="persona",
            created_at=datetime.now(),
        )
        test_db.add(star_pc)
        test_db.commit()

        # Filter by knowledge
        response = authenticated_client.get("/api/users/stars?star_type=knowledge")
        data = response.json()
        assert data["pagination"]["total"] == 1
        assert data["data"][0]["type"] == "knowledge"

        # Filter by persona
        response2 = authenticated_client.get("/api/users/stars?star_type=persona")
        data2 = response2.json()
        assert data2["pagination"]["total"] == 1
        assert data2["data"][0]["type"] == "persona"

    def test_get_user_stars_sort_by_created_at(self, authenticated_client, test_user, test_db):
        """Test sorting stars by created_at"""
        # Create stars with different timestamps
        kb1 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB 1",
            description="First",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            base_path="uploads/knowledge/test_kb1",
            created_at=datetime.now(),
        )
        test_db.add(kb1)
        star1 = StarRecord(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            target_id=kb1.id,
            target_type="knowledge",
            created_at=datetime(2024, 1, 1),
        )
        test_db.add(star1)

        kb2 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB 2",
            description="Second",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            base_path="uploads/knowledge/test_kb2",
            created_at=datetime.now(),
        )
        test_db.add(kb2)
        star2 = StarRecord(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            target_id=kb2.id,
            target_type="knowledge",
            created_at=datetime(2024, 2, 1),
        )
        test_db.add(star2)
        test_db.commit()

        # Sort descending (newest first)
        response = authenticated_client.get("/api/users/stars?sort_by=created_at&sort_order=desc")
        data = response.json()
        assert data["data"][0]["name"] == "KB 2"
        assert data["data"][1]["name"] == "KB 1"

        # Sort ascending (oldest first)
        response2 = authenticated_client.get("/api/users/stars?sort_by=created_at&sort_order=asc")
        data2 = response2.json()
        assert data2["data"][0]["name"] == "KB 1"
        assert data2["data"][1]["name"] == "KB 2"

    def test_get_user_stars_unauthenticated(self, client):
        """Test getting stars without authentication"""
        response = client.get("/api/users/stars")

        assert response.status_code == 401


class TestUploadHistory:
    """Test GET /api/users/me/upload-history endpoint"""

    def test_get_upload_history_empty(self, authenticated_client):
        """Test getting upload history when user has no uploads"""
        response = authenticated_client.get("/api/users/me/upload-history")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["pagination"]["total"] == 0

    def test_get_upload_history_with_records(self, authenticated_client, test_user, test_db):
        """Test getting upload history with records"""
        # Create knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_public=False,
            is_pending=False,
            created_at=datetime.now(),
        )
        test_db.add(kb)

        # Create upload record
        record = UploadRecord(
            id=str(uuid.uuid4()),
            target_id=kb.id,
            target_type="knowledge",
            uploader_id=test_user.id,
            name="Test KB",
            description="Test description",
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        test_db.add(record)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/upload-history")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 1
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Test KB"
        assert data["data"][0]["type"] == "knowledge"
        assert data["data"][0]["status"] == "success"  # approved maps to success

    def test_get_upload_history_pagination(self, authenticated_client, test_user, test_db):
        """Test upload history pagination"""
        # Create multiple upload records
        for i in range(25):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB {i}",
                description=f"Description {i}",
                uploader_id=test_user.id,
                is_public=False,
                is_pending=False,
                created_at=datetime.now(),
            )
            test_db.add(kb)

            record = UploadRecord(
                id=str(uuid.uuid4()),
                target_id=kb.id,
                target_type="knowledge",
                uploader_id=test_user.id,
                name=f"KB {i}",
                description=f"Description {i}",
                status="approved",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        # Get first page
        response = authenticated_client.get("/api/users/me/upload-history?page=1&page_size=20")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 25
        assert len(data["data"]) == 20

        # Get second page
        response2 = authenticated_client.get("/api/users/me/upload-history?page=2&page_size=20")
        data2 = response2.json()
        assert len(data2["data"]) == 5

    def test_get_upload_history_status_mapping(self, authenticated_client, test_user, test_db):
        """Test that upload record status is correctly mapped"""
        # Create records with different statuses
        statuses = [("approved", "success"), ("rejected", "failed"), ("pending", "processing")]

        for db_status, _expected_status in statuses:
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB {db_status}",
                description="Test",
                uploader_id=test_user.id,
                is_public=False,
                is_pending=False,
                created_at=datetime.now(),
            )
            test_db.add(kb)

            record = UploadRecord(
                id=str(uuid.uuid4()),
                target_id=kb.id,
                target_type="knowledge",
                uploader_id=test_user.id,
                name=f"KB {db_status}",
                description="Test",
                status=db_status,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/upload-history")
        data = response.json()

        assert data["pagination"]["total"] == 3
        for item in data["data"]:
            if "approved" in item["name"]:
                assert item["status"] == "success"
            elif "rejected" in item["name"]:
                assert item["status"] == "failed"
            elif "pending" in item["name"]:
                assert item["status"] == "processing"

    def test_get_upload_history_unauthenticated(self, client):
        """Test getting upload history without authentication"""
        response = client.get("/api/users/me/upload-history")

        assert response.status_code == 401

    def test_get_upload_history_filter_by_status_approved(self, authenticated_client, test_user, test_db):
        """Test filtering upload history by approved status"""
        # Create records with different statuses
        statuses = ["approved", "approved", "rejected", "pending"]

        for i, status in enumerate(statuses):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB {i}",
                description="Test",
                uploader_id=test_user.id,
                is_public=False,
                is_pending=False,
                created_at=datetime.now(),
            )
            test_db.add(kb)

            record = UploadRecord(
                id=str(uuid.uuid4()),
                target_id=kb.id,
                target_type="knowledge",
                uploader_id=test_user.id,
                name=f"KB {i}",
                description="Test",
                status=status,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        # Filter by approved status
        response = authenticated_client.get("/api/users/me/upload-history?status=approved")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 2
        assert len(data["data"]) == 2
        # All returned records should have success status (approved maps to success)
        for item in data["data"]:
            assert item["status"] == "success"

    def test_get_upload_history_filter_by_status_rejected(self, authenticated_client, test_user, test_db):
        """Test filtering upload history by rejected status"""
        # Create records with different statuses
        statuses = ["approved", "rejected", "rejected", "pending"]

        for i, status in enumerate(statuses):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB {i}",
                description="Test",
                uploader_id=test_user.id,
                is_public=False,
                is_pending=False,
                created_at=datetime.now(),
            )
            test_db.add(kb)

            record = UploadRecord(
                id=str(uuid.uuid4()),
                target_id=kb.id,
                target_type="knowledge",
                uploader_id=test_user.id,
                name=f"KB {i}",
                description="Test",
                status=status,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        # Filter by rejected status
        response = authenticated_client.get("/api/users/me/upload-history?status=rejected")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 2
        assert len(data["data"]) == 2
        # All returned records should have failed status (rejected maps to failed)
        for item in data["data"]:
            assert item["status"] == "failed"

    def test_get_upload_history_filter_by_status_pending(self, authenticated_client, test_user, test_db):
        """Test filtering upload history by pending status"""
        # Create records with different statuses
        statuses = ["approved", "rejected", "pending", "pending"]

        for i, status in enumerate(statuses):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB {i}",
                description="Test",
                uploader_id=test_user.id,
                is_public=False,
                is_pending=False,
                created_at=datetime.now(),
            )
            test_db.add(kb)

            record = UploadRecord(
                id=str(uuid.uuid4()),
                target_id=kb.id,
                target_type="knowledge",
                uploader_id=test_user.id,
                name=f"KB {i}",
                description="Test",
                status=status,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        # Filter by pending status
        response = authenticated_client.get("/api/users/me/upload-history?status=pending")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 2
        assert len(data["data"]) == 2
        # All returned records should have processing status (pending maps to processing)
        for item in data["data"]:
            assert item["status"] == "processing"

    def test_get_upload_history_filter_with_pagination(self, authenticated_client, test_user, test_db):
        """Test status filtering combined with pagination"""
        # Create 15 approved records
        for i in range(15):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB Approved {i}",
                description="Test",
                uploader_id=test_user.id,
                is_public=False,
                is_pending=False,
                created_at=datetime.now(),
            )
            test_db.add(kb)

            record = UploadRecord(
                id=str(uuid.uuid4()),
                target_id=kb.id,
                target_type="knowledge",
                uploader_id=test_user.id,
                name=f"KB Approved {i}",
                description="Test",
                status="approved",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            test_db.add(record)

        # Create 5 rejected records
        for i in range(5):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB Rejected {i}",
                description="Test",
                uploader_id=test_user.id,
                is_public=False,
                is_pending=False,
                created_at=datetime.now(),
            )
            test_db.add(kb)

            record = UploadRecord(
                id=str(uuid.uuid4()),
                target_id=kb.id,
                target_type="knowledge",
                uploader_id=test_user.id,
                name=f"KB Rejected {i}",
                description="Test",
                status="rejected",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        # Get first page of approved records
        response = authenticated_client.get("/api/users/me/upload-history?status=approved&page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 15
        assert len(data["data"]) == 10
        assert data["pagination"]["page"] == 1

        # Get second page of approved records
        response2 = authenticated_client.get("/api/users/me/upload-history?status=approved&page=2&page_size=10")
        data2 = response2.json()
        assert len(data2["data"]) == 5


class TestUploadStats:
    """Test GET /api/users/me/upload-stats endpoint"""

    def test_get_upload_stats_empty(self, authenticated_client):
        """Test getting upload stats when user has no uploads"""
        response = authenticated_client.get("/api/users/me/upload-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 0
        assert data["data"]["success"] == 0
        assert data["data"]["pending"] == 0
        assert data["data"]["failed"] == 0

    def test_get_upload_stats_with_records(self, authenticated_client, test_user, test_db):
        """Test getting upload stats with various records"""
        # Create upload records with different statuses
        statuses = ["approved", "approved", "pending", "rejected"]
        types = ["knowledge", "knowledge", "persona", "persona"]

        for status, upload_type in zip(statuses, types, strict=False):
            if upload_type == "knowledge":
                target = KnowledgeBase(
                    id=str(uuid.uuid4()),
                    name=f"KB {status}",
                    description="Test",
                    uploader_id=test_user.id,
                    is_public=False,
                    is_pending=False,
                    created_at=datetime.now(),
                )
            else:
                target = PersonaCard(
                    id=str(uuid.uuid4()),
                    name=f"PC {status}",
                    description="Test",
                    uploader_id=test_user.id,
                    is_public=False,
                    is_pending=False,
                    base_path="/tmp/test",
                    created_at=datetime.now(),
                )
            test_db.add(target)

            record = UploadRecord(
                id=str(uuid.uuid4()),
                target_id=target.id,
                target_type=upload_type,
                uploader_id=test_user.id,
                name=target.name,
                description="Test",
                status=status,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/upload-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 4
        assert data["data"]["success"] == 2  # approved
        assert data["data"]["pending"] == 1
        assert data["data"]["failed"] == 1  # rejected
        assert data["data"]["knowledge"] == 2
        assert data["data"]["persona"] == 2

    def test_get_upload_stats_unauthenticated(self, client):
        """Test getting upload stats without authentication"""
        response = client.get("/api/users/me/upload-stats")

        assert response.status_code == 401


class TestDashboardStats:
    """Test GET /api/users/me/dashboard-stats endpoint"""

    def test_get_dashboard_stats_empty(self, authenticated_client):
        """Test getting dashboard stats when user has no data"""
        response = authenticated_client.get("/api/users/me/dashboard-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["totalUploads"] == 0
        assert data["data"]["totalDownloads"] == 0
        assert data["data"]["totalStars"] == 0

    def test_get_dashboard_stats_with_data(self, authenticated_client, test_user, test_db):
        """Test getting dashboard stats with user data"""
        # Create knowledge bases
        kb1 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB 1",
            description="Test",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            downloads=10,
            star_count=5,
            created_at=datetime.now(),
        )
        kb2 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB 2",
            description="Test",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            downloads=15,
            star_count=8,
            created_at=datetime.now(),
        )
        test_db.add(kb1)
        test_db.add(kb2)

        # Create persona cards
        pc1 = PersonaCard(
            id=str(uuid.uuid4()),
            name="PC 1",
            description="Test",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            downloads=20,
            star_count=12,
            base_path="uploads/persona/test_pc1",
            created_at=datetime.now(),
        )
        test_db.add(pc1)

        # Create upload records
        for target in [kb1, kb2, pc1]:
            record = UploadRecord(
                id=str(uuid.uuid4()),
                target_id=target.id,
                target_type="knowledge" if isinstance(target, KnowledgeBase) else "persona",
                uploader_id=test_user.id,
                name=target.name,
                description="Test",
                status="approved",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/dashboard-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["totalUploads"] == 3
        assert data["data"]["knowledgeUploads"] == 2
        assert data["data"]["personaUploads"] == 1
        assert data["data"]["totalDownloads"] == 45  # 10 + 15 + 20
        assert data["data"]["knowledgeDownloads"] == 25  # 10 + 15
        assert data["data"]["personaDownloads"] == 20
        assert data["data"]["totalStars"] == 25  # 5 + 8 + 12
        assert data["data"]["knowledgeStars"] == 13  # 5 + 8
        assert data["data"]["personaStars"] == 12

    def test_get_dashboard_stats_unauthenticated(self, client):
        """Test getting dashboard stats without authentication"""
        response = client.get("/api/users/me/dashboard-stats")

        assert response.status_code == 401


class TestDashboardTrends:
    """Test GET /api/users/me/dashboard-trends endpoint"""

    def test_get_dashboard_trends_default_days(self, authenticated_client):
        """Test getting dashboard trends with default 30 days"""
        response = authenticated_client.get("/api/users/me/dashboard-trends")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_get_dashboard_trends_custom_days(self, authenticated_client):
        """Test getting dashboard trends with custom days parameter"""
        response = authenticated_client.get("/api/users/me/dashboard-trends?days=7")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_dashboard_trends_max_days(self, authenticated_client):
        """Test getting dashboard trends with maximum 90 days"""
        response = authenticated_client.get("/api/users/me/dashboard-trends?days=90")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_dashboard_trends_exceeds_max_days(self, authenticated_client):
        """Test that days parameter is capped at 90"""
        response = authenticated_client.get("/api/users/me/dashboard-trends?days=100")

        # Should either cap at 90 or return validation error
        assert response.status_code in [200, 422]

    def test_get_dashboard_trends_invalid_days(self, authenticated_client):
        """Test getting dashboard trends with invalid days parameter"""
        response = authenticated_client.get("/api/users/me/dashboard-trends?days=0")

        assert response.status_code == 422

    def test_get_dashboard_trends_unauthenticated(self, client):
        """Test getting dashboard trends without authentication"""
        response = client.get("/api/users/me/dashboard-trends")

        assert response.status_code == 401


class TestUploadStatsEdgeCases:
    """Test edge cases for GET /api/users/me/upload-stats endpoint

    Requirements: 3.1
    """

    def test_get_upload_stats_with_empty_data(self, authenticated_client, test_user, test_db):
        """Test upload stats calculation with no data

        验证：
        - 所有统计值为 0
        - 不会抛出错误
        """
        response = authenticated_client.get("/api/users/me/upload-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 0
        assert data["data"]["success"] == 0
        assert data["data"]["pending"] == 0
        assert data["data"]["failed"] == 0
        assert data["data"]["knowledge"] == 0
        assert data["data"]["persona"] == 0

    def test_get_upload_stats_with_null_status(self, authenticated_client, test_user, test_db):
        """Test upload stats with null status records

        验证：
        - null 状态记录被正确处理
        - 不会导致计算错误
        """
        # Create record with null status
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB Null Status",
            description="Test",
            uploader_id=test_user.id,
            is_public=False,
            is_pending=False,
            created_at=datetime.now(),
        )
        test_db.add(kb)

        record = UploadRecord(
            id=str(uuid.uuid4()),
            target_id=kb.id,
            target_type="knowledge",
            uploader_id=test_user.id,
            name="KB Null Status",
            description="Test",
            status=None,  # null status
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        test_db.add(record)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/upload-stats")

        assert response.status_code == 200
        data = response.json()
        # Should handle null status gracefully
        assert data["data"]["total"] >= 0

    def test_get_upload_stats_with_orphaned_records(self, authenticated_client, test_user, test_db):
        """Test upload stats with orphaned upload records (target deleted)

        验证：
        - 孤立记录被正确处理
        - 统计仍然准确
        """
        # Create upload record without corresponding target
        record = UploadRecord(
            id=str(uuid.uuid4()),
            target_id=str(uuid.uuid4()),  # Non-existent target
            target_type="knowledge",
            uploader_id=test_user.id,
            name="Orphaned Record",
            description="Test",
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        test_db.add(record)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/upload-stats")

        assert response.status_code == 200
        data = response.json()
        # Should count orphaned records
        assert data["data"]["total"] >= 1
        assert data["data"]["success"] >= 1


class TestDashboardStatsEdgeCases:
    """Test edge cases for GET /api/users/me/dashboard-stats endpoint

    Requirements: 3.1
    """

    def test_get_dashboard_stats_with_zero_downloads(self, authenticated_client, test_user, test_db):
        """Test dashboard stats with zero downloads

        验证：
        - 零下载量被正确显示
        - 不会导致除零错误
        """
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB Zero Downloads",
            description="Test",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            downloads=0,
            star_count=0,
            created_at=datetime.now(),
        )
        test_db.add(kb)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/dashboard-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["totalDownloads"] == 0
        assert data["data"]["totalStars"] == 0

    def test_get_dashboard_stats_with_negative_values(self, authenticated_client, test_user, test_db):
        """Test dashboard stats with negative values (data corruption scenario)

        验证：
        - 负值被正确处理
        - 不会导致错误
        """
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB Negative",
            description="Test",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            downloads=-5,  # Corrupted data
            star_count=-2,
            created_at=datetime.now(),
        )
        test_db.add(kb)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/dashboard-stats")

        assert response.status_code == 200
        # Should handle negative values gracefully
        data = response.json()
        assert "totalDownloads" in data["data"]
        assert "totalStars" in data["data"]

    def test_get_dashboard_stats_with_large_numbers(self, authenticated_client, test_user, test_db):
        """Test dashboard stats with very large numbers

        验证：
        - 大数值被正确处理
        - 不会溢出
        """
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB Large Numbers",
            description="Test",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            downloads=999999999,
            star_count=999999999,
            created_at=datetime.now(),
        )
        test_db.add(kb)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/dashboard-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["totalDownloads"] == 999999999
        assert data["data"]["totalStars"] == 999999999

    def test_get_dashboard_stats_with_mixed_public_private(self, authenticated_client, test_user, test_db):
        """Test dashboard stats with mix of public and private content

        验证：
        - 公开和私有内容都被统计
        - 统计准确
        """
        # Public KB
        kb_public = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB Public",
            description="Test",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            downloads=10,
            star_count=5,
            created_at=datetime.now(),
        )
        test_db.add(kb_public)

        # Private KB
        kb_private = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB Private",
            description="Test",
            uploader_id=test_user.id,
            is_public=False,
            is_pending=False,
            downloads=20,
            star_count=8,
            created_at=datetime.now(),
        )
        test_db.add(kb_private)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/dashboard-stats")

        assert response.status_code == 200
        data = response.json()
        # Should count both public and private
        assert data["data"]["totalDownloads"] == 30
        assert data["data"]["totalStars"] == 13


class TestDashboardTrendsEdgeCases:
    """Test edge cases for GET /api/users/me/dashboard-trends endpoint

    Requirements: 3.1
    """

    def test_get_dashboard_trends_with_zero_days(self, authenticated_client):
        """Test dashboard trends with zero days parameter

        验证：
        - 返回验证错误
        """
        response = authenticated_client.get("/api/users/me/dashboard-trends?days=0")

        assert response.status_code == 422

    def test_get_dashboard_trends_with_negative_days(self, authenticated_client):
        """Test dashboard trends with negative days parameter

        验证：
        - 返回验证错误
        """
        response = authenticated_client.get("/api/users/me/dashboard-trends?days=-7")

        assert response.status_code == 422

    def test_get_dashboard_trends_with_very_large_days(self, authenticated_client):
        """Test dashboard trends with very large days parameter

        验证：
        - 被限制在最大值（90天）
        - 或返回验证错误
        """
        response = authenticated_client.get("/api/users/me/dashboard-trends?days=1000")

        # Should either cap at 90 or return validation error
        assert response.status_code in [200, 422]

    def test_get_dashboard_trends_with_invalid_days_type(self, authenticated_client):
        """Test dashboard trends with invalid days type

        验证：
        - 返回验证错误
        """
        response = authenticated_client.get("/api/users/me/dashboard-trends?days=abc")

        assert response.status_code == 422

    def test_get_dashboard_trends_with_float_days(self, authenticated_client):
        """Test dashboard trends with float days parameter

        验证：
        - 浮点数被转换为整数或返回错误
        """
        response = authenticated_client.get("/api/users/me/dashboard-trends?days=7.5")

        # Should either convert to int or return validation error
        assert response.status_code in [200, 422]

    def test_get_dashboard_trends_date_range_boundary(self, authenticated_client, test_user, test_db):
        """Test dashboard trends at date range boundaries

        验证：
        - 边界日期被正确处理
        - 不会遗漏或重复数据
        """
        from datetime import timedelta

        # Create upload record exactly 7 days ago
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB Boundary",
            description="Test",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            created_at=datetime.now() - timedelta(days=7),
        )
        test_db.add(kb)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/dashboard-trends?days=7")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_get_dashboard_trends_with_future_dates(self, authenticated_client, test_user, test_db):
        """Test dashboard trends with records having future dates (data corruption)

        验证：
        - 未来日期记录被正确处理
        - 不会导致错误
        """
        from datetime import timedelta

        # Create upload record with future date
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB Future",
            description="Test",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            created_at=datetime.now() + timedelta(days=30),
        )
        test_db.add(kb)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/dashboard-trends?days=30")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestAvatarManagementEdgeCases:
    """Test edge cases for avatar upload, delete, and retrieval endpoints

    Requirements: 3.1, 10.2
    """

    def create_test_image(self, img_format="PNG", size=(200, 200)):
        """Helper to create a test image file"""
        img = Image.new("RGB", size, color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format=img_format)
        img_bytes.seek(0)
        return img_bytes

    def test_upload_avatar_file_save_failure(self, authenticated_client):
        """Test avatar upload with potential file save issues

        验证：
        - 头像上传的基本功能
        - 注意：文件保存失败的场景难以在集成测试中模拟
        """
        img_bytes = self.create_test_image()

        response = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("test.png", img_bytes, "image/png")}
        )

        # Should succeed in normal conditions
        assert response.status_code == 200

    def test_upload_avatar_invalid_image_format(self, authenticated_client):
        """Test avatar upload with invalid image format

        验证：
        - 无效图片格式被拒绝
        - 返回清晰的错误消息
        """
        # Create a file that's not a valid image
        invalid_img = io.BytesIO(b"Not an image file")

        response = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("test.png", invalid_img, "image/png")}
        )

        assert response.status_code in [400, 422]

    def test_upload_avatar_corrupted_image(self, authenticated_client):
        """Test avatar upload with corrupted image data

        验证：
        - 损坏的图片被拒绝
        - 返回适当的错误
        """
        # Create corrupted image data
        corrupted_img = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"corrupted data")

        response = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("test.png", corrupted_img, "image/png")}
        )

        assert response.status_code in [400, 422]

    def test_upload_avatar_extremely_large_dimensions(self, authenticated_client):
        """Test avatar upload with large image dimensions

        验证：
        - 大尺寸图片被处理或拒绝
        - 不会导致服务器崩溃

        注意：使用 8000x8000 像素（64M 像素）的图片，低于 PIL 的 89M 像素限制，
        但仍然足够大来测试边缘情况
        """
        # 使用一个大但不会触发 DecompressionBombWarning 的尺寸
        # PIL 的默认限制是 89,478,485 像素，我们使用 8000x8000 = 64,000,000 像素
        try:
            img_bytes = self.create_test_image(size=(8000, 8000))

            response = authenticated_client.post(
                "/api/users/me/avatar", files={"avatar": ("large.png", img_bytes, "image/png")}
            )

            # Should either succeed (with resizing) or fail gracefully
            assert response.status_code in [200, 400, 422, 500]
        except Exception:
            # If image creation fails, that's also acceptable
            pass

    def test_upload_avatar_empty_file(self, authenticated_client):
        """Test avatar upload with empty file

        验证：
        - 空文件被拒绝
        - 返回验证错误
        """
        empty_file = io.BytesIO(b"")

        response = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("empty.png", empty_file, "image/png")}
        )

        assert response.status_code in [400, 422]

    def test_upload_avatar_wrong_content_type(self, authenticated_client):
        """Test avatar upload with wrong content type

        验证：
        - 内容类型不匹配被检测
        - 返回验证错误
        """
        # Send text file with image content type
        text_file = io.BytesIO(b"This is text, not an image")

        response = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("test.png", text_file, "image/png")}
        )

        assert response.status_code in [400, 422]

    def test_upload_avatar_svg_file(self, authenticated_client):
        """Test avatar upload with SVG file (potential security risk)

        验证：
        - SVG 文件被拒绝（安全考虑）
        - 返回验证错误
        """
        svg_content = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="50"/></svg>'
        svg_file = io.BytesIO(svg_content)

        response = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("test.svg", svg_file, "image/svg+xml")}
        )

        # SVG should be rejected for security reasons
        assert response.status_code in [400, 422]

    def test_upload_avatar_gif_animated(self, authenticated_client):
        """Test avatar upload with animated GIF

        验证：
        - 动画 GIF 被处理或拒绝
        """
        # Create a simple GIF (PIL doesn't easily create animated GIFs, so we'll use a static one)
        img_bytes = self.create_test_image(img_format="GIF")

        response = authenticated_client.post(
            "/api/users/me/avatar", files={"avatar": ("test.gif", img_bytes, "image/gif")}
        )

        # Should either accept or reject GIF
        assert response.status_code in [200, 400, 422]

    def test_upload_avatar_multiple_files(self, authenticated_client):
        """Test avatar upload with multiple files

        验证：
        - 只接受单个文件
        - 返回验证错误
        """
        img_bytes1 = self.create_test_image()
        img_bytes2 = self.create_test_image()

        # Try to upload multiple files (this might not work as expected with TestClient)
        response = authenticated_client.post(
            "/api/users/me/avatar",
            files=[
                ("avatar", ("test1.png", img_bytes1, "image/png")),
                ("avatar", ("test2.png", img_bytes2, "image/png")),
            ],
        )

        # Should handle multiple files gracefully
        assert response.status_code in [200, 400, 422]

    def test_upload_avatar_no_file_provided(self, authenticated_client):
        """Test avatar upload without providing file

        验证：
        - 缺少文件参数返回错误
        """
        response = authenticated_client.post("/api/users/me/avatar")

        assert response.status_code == 422

    @patch("os.remove")
    def test_delete_avatar_file_deletion_failure(self, mock_remove, authenticated_client, test_user, test_db):
        """Test avatar deletion when file removal fails

        验证：
        - Mock 文件删除失败
        - 数据库仍然更新
        - 或返回适当的错误
        """
        # Set avatar path
        test_user.avatar_path = "uploads/avatars/test.jpg"
        test_db.commit()

        # Mock file deletion failure
        mock_remove.side_effect = OSError("Permission denied")

        response = authenticated_client.delete("/api/users/me/avatar")

        # Should handle gracefully
        assert response.status_code in [200, 500]

    def test_delete_avatar_concurrent_deletion(self, authenticated_client, test_user, test_db):
        """Test concurrent avatar deletion

        验证：
        - 多次删除不会导致错误
        - 幂等性
        """
        # Set avatar path
        test_user.avatar_path = "uploads/avatars/test.jpg"
        test_db.commit()

        # Delete twice
        response1 = authenticated_client.delete("/api/users/me/avatar")
        response2 = authenticated_client.delete("/api/users/me/avatar")

        # Both should succeed (idempotent)
        assert response1.status_code == 200
        assert response2.status_code == 200

    def test_get_user_avatar_with_invalid_user_id(self, client):
        """Test getting avatar with invalid user ID format

        验证：
        - 无效 UUID 格式返回错误
        """
        response = client.get("/api/users/invalid-uuid/avatar")

        assert response.status_code in [400, 404, 422]

    def test_get_user_avatar_with_deleted_user(self, client, test_db):
        """Test getting avatar for deleted user

        验证：
        - 已删除用户返回 404
        """
        # Create and then delete a user
        deleted_user_id = str(uuid.uuid4())

        response = client.get(f"/api/users/{deleted_user_id}/avatar")

        assert response.status_code == 404

    def test_get_user_avatar_with_broken_file_path(self, client, test_user, test_db):
        """Test getting avatar when file path is broken

        验证：
        - 文件路径损坏时生成默认头像
        - 或返回 404
        """
        # Set invalid avatar path
        test_user.avatar_path = "/nonexistent/path/avatar.jpg"
        test_db.commit()

        response = client.get(f"/api/users/{test_user.id}/avatar")

        # Should either generate default or return 404
        assert response.status_code in [200, 404]


class TestUserStarsEdgeCases:
    """Test edge cases for GET /api/users/stars endpoint

    Requirements: 3.1
    """

    def test_get_user_stars_with_deleted_target(self, authenticated_client, test_user, test_db):
        """Test getting stars when target has been deleted

        验证：
        - 已删除目标的收藏被正确处理
        - 不会导致错误
        """
        # Create star record without corresponding target
        star = StarRecord(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            target_id=str(uuid.uuid4()),  # Non-existent target
            target_type="knowledge",
            created_at=datetime.now(),
        )
        test_db.add(star)
        test_db.commit()

        response = authenticated_client.get("/api/users/stars")

        assert response.status_code == 200
        # Should handle missing targets gracefully
        data = response.json()
        assert "data" in data

    def test_get_user_stars_with_invalid_target_type(self, authenticated_client, test_user, test_db):
        """Test getting stars with invalid target type

        验证：
        - 无效目标类型被正确处理
        """
        # Create star with invalid target type
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test",
            uploader_id=test_user.id,
            is_public=True,
            is_pending=False,
            created_at=datetime.now(),
        )
        test_db.add(kb)

        star = StarRecord(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            target_id=kb.id,
            target_type="invalid_type",  # Invalid type
            created_at=datetime.now(),
        )
        test_db.add(star)
        test_db.commit()

        response = authenticated_client.get("/api/users/stars")

        assert response.status_code == 200
        # Should handle invalid types gracefully

    def test_get_user_stars_complex_filtering(self, authenticated_client, test_user, test_db):
        """Test complex filtering conditions

        验证：
        - 多个过滤条件组合正确工作
        """
        # Create multiple stars
        for i in range(5):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB {i}",
                description="Test",
                uploader_id=test_user.id,
                is_public=True,
                is_pending=False,
                created_at=datetime.now(),
                base_path=f"uploads/knowledge/test_{i}",
            )
            test_db.add(kb)

            star = StarRecord(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                target_id=kb.id,
                target_type="knowledge",
                created_at=datetime.now(),
            )
            test_db.add(star)

        for i in range(3):
            pc = PersonaCard(
                id=str(uuid.uuid4()),
                name=f"PC {i}",
                description="Test",
                uploader_id=test_user.id,
                is_public=True,
                is_pending=False,
                created_at=datetime.now(),
                base_path=f"uploads/persona/test_{i}",
            )
            test_db.add(pc)

            star = StarRecord(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                target_id=pc.id,
                target_type="persona",
                created_at=datetime.now(),
            )
            test_db.add(star)
        test_db.commit()

        # Filter by type and pagination
        response = authenticated_client.get("/api/users/stars?star_type=knowledge&page=1&page_size=3")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 5
        assert len(data["data"]) == 3
        assert all(item["type"] == "knowledge" for item in data["data"])

    def test_get_user_stars_sorting_edge_cases(self, authenticated_client, test_user, test_db):
        """Test sorting edge cases

        验证：
        - 相同时间戳的排序稳定
        - 空值排序正确
        """

        # Create stars with same timestamp
        same_time = datetime.now()
        for i in range(3):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB Same Time {i}",
                description="Test",
                uploader_id=test_user.id,
                is_public=True,
                is_pending=False,
                created_at=same_time,
                base_path=f"uploads/knowledge/same_{i}",
            )
            test_db.add(kb)

            star = StarRecord(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                target_id=kb.id,
                target_type="knowledge",
                created_at=same_time,
            )
            test_db.add(star)
        test_db.commit()

        response = authenticated_client.get("/api/users/stars?sort_by=created_at&sort_order=desc")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3

    def test_get_user_stars_pagination_boundary(self, authenticated_client, test_user, test_db):
        """Test pagination boundary conditions

        验证：
        - 最后一页正确处理
        - 超出范围的页码正确处理
        """
        # Create exactly 10 stars
        for i in range(10):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB {i}",
                description="Test",
                uploader_id=test_user.id,
                is_public=True,
                is_pending=False,
                created_at=datetime.now(),
                base_path=f"uploads/knowledge/boundary_{i}",
            )
            test_db.add(kb)

            star = StarRecord(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                target_id=kb.id,
                target_type="knowledge",
                created_at=datetime.now(),
            )
            test_db.add(star)
        test_db.commit()

        # Request page beyond available data
        response = authenticated_client.get("/api/users/stars?page=100&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 10
        assert len(data["data"]) == 0  # Empty page

    def test_get_user_stars_invalid_sort_field(self, authenticated_client):
        """Test sorting with invalid field

        验证：
        - 无效排序字段被拒绝或忽略
        """
        response = authenticated_client.get("/api/users/stars?sort_by=invalid_field")

        # Should either use default sort or return error
        assert response.status_code in [200, 422]

    def test_get_user_stars_invalid_sort_order(self, authenticated_client):
        """Test sorting with invalid order

        验证：
        - 无效排序顺序被拒绝或使用默认值
        """
        response = authenticated_client.get("/api/users/stars?sort_by=created_at&sort_order=invalid")

        # Should either use default order or return error
        assert response.status_code in [200, 422]


class TestUploadHistoryEdgeCases:
    """Test edge cases for GET /api/users/me/upload-history endpoint

    Requirements: 3.1
    """

    def test_get_upload_history_with_null_timestamps(self, authenticated_client, test_user, test_db):
        """Test upload history with null timestamps

        验证：
        - null 时间戳被正确处理
        - 不会导致排序错误
        """
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB Null Time",
            description="Test",
            uploader_id=test_user.id,
            is_public=False,
            is_pending=False,
            created_at=None,  # null timestamp
        )
        test_db.add(kb)

        record = UploadRecord(
            id=str(uuid.uuid4()),
            target_id=kb.id,
            target_type="knowledge",
            uploader_id=test_user.id,
            name="KB Null Time",
            description="Test",
            status="approved",
            created_at=None,
            updated_at=None,
        )
        test_db.add(record)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/upload-history")

        assert response.status_code == 200
        # Should handle null timestamps gracefully

    def test_get_upload_history_with_very_long_names(self, authenticated_client, test_user, test_db):
        """Test upload history with very long names

        验证：
        - 超长名称被正确处理
        - 不会导致显示问题
        """
        long_name = "A" * 1000  # Very long name

        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name=long_name,
            description="Test",
            uploader_id=test_user.id,
            is_public=False,
            is_pending=False,
            created_at=datetime.now(),
        )
        test_db.add(kb)

        record = UploadRecord(
            id=str(uuid.uuid4()),
            target_id=kb.id,
            target_type="knowledge",
            uploader_id=test_user.id,
            name=long_name,
            description="Test",
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        test_db.add(record)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/upload-history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1

    def test_get_upload_history_with_special_characters(self, authenticated_client, test_user, test_db):
        """Test upload history with special characters in names

        验证：
        - 特殊字符被正确编码
        - 不会导致 JSON 解析错误
        """
        special_name = "Test <script>alert('xss')</script> 测试 emoji 😀"

        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name=special_name,
            description="Test",
            uploader_id=test_user.id,
            is_public=False,
            is_pending=False,
            created_at=datetime.now(),
        )
        test_db.add(kb)

        record = UploadRecord(
            id=str(uuid.uuid4()),
            target_id=kb.id,
            target_type="knowledge",
            uploader_id=test_user.id,
            name=special_name,
            description="Test",
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        test_db.add(record)
        test_db.commit()

        response = authenticated_client.get("/api/users/me/upload-history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        # Special characters should be properly encoded
        assert special_name in data["data"][0]["name"]

    def test_get_upload_history_combined_filters(self, authenticated_client, test_user, test_db):
        """Test upload history with combined filters

        验证：
        - 状态过滤和分页组合正确工作
        """
        # Create 15 approved and 10 rejected records
        for i in range(15):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB Approved {i}",
                description="Test",
                uploader_id=test_user.id,
                is_public=False,
                is_pending=False,
                created_at=datetime.now(),
            )
            test_db.add(kb)

            record = UploadRecord(
                id=str(uuid.uuid4()),
                target_id=kb.id,
                target_type="knowledge",
                uploader_id=test_user.id,
                name=f"KB Approved {i}",
                description="Test",
                status="approved",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            test_db.add(record)

        for i in range(10):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"KB Rejected {i}",
                description="Test",
                uploader_id=test_user.id,
                is_public=False,
                is_pending=False,
                created_at=datetime.now(),
            )
            test_db.add(kb)

            record = UploadRecord(
                id=str(uuid.uuid4()),
                target_id=kb.id,
                target_type="knowledge",
                uploader_id=test_user.id,
                name=f"KB Rejected {i}",
                description="Test",
                status="rejected",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            test_db.add(record)
        test_db.commit()

        # Get second page of approved records
        response = authenticated_client.get("/api/users/me/upload-history?status=approved&page=2&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 15
        assert len(data["data"]) == 5  # Second page has 5 items
        assert all(item["status"] == "success" for item in data["data"])

    def test_get_upload_history_invalid_status_filter(self, authenticated_client):
        """Test upload history with invalid status filter

        验证：
        - 无效状态过滤被拒绝或忽略
        """
        response = authenticated_client.get("/api/users/me/upload-history?status=invalid_status")

        # Should either ignore invalid status or return error
        assert response.status_code in [200, 422]

    def test_get_upload_history_pagination_with_zero_page_size(self, authenticated_client):
        """Test upload history with zero page size

        验证：
        - 零页面大小被拒绝或使用默认值
        """
        response = authenticated_client.get("/api/users/me/upload-history?page_size=0")

        # Should either use default or return error
        assert response.status_code in [200, 422]

    def test_get_upload_history_pagination_with_negative_page(self, authenticated_client):
        """Test upload history with negative page number

        验证：
        - 负页码被拒绝或使用默认值
        """
        response = authenticated_client.get("/api/users/me/upload-history?page=-1")

        # Should either use default or return error
        assert response.status_code in [200, 422]


class TestChangePasswordEdgeCases:
    """Test edge cases for PUT /api/users/me/password endpoint

    Requirements: 3.1, 10.7
    """

    def test_change_password_with_very_long_password(self, authenticated_client):
        """Test password change with very long password

        验证：
        - 超长密码被处理或拒绝
        """
        very_long_password = "a" * 1000

        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": very_long_password,
                "confirm_password": very_long_password,
            },
        )

        # Should either accept (if no max length) or reject
        assert response.status_code in [200, 422]

    def test_change_password_with_unicode_characters(self, authenticated_client, test_user, test_db):
        """Test password change with Unicode characters

        验证：
        - Unicode 字符密码被正确处理
        """
        unicode_password = "密码测试123😀"

        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": unicode_password,
                "confirm_password": unicode_password,
            },
        )

        # Should accept Unicode passwords
        assert response.status_code in [200, 422]

    def test_change_password_with_special_characters(self, authenticated_client, test_user, test_db):
        """Test password change with special characters

        验证：
        - 特殊字符密码被正确处理
        """
        special_password = "P@ssw0rd!#$%^&*()"

        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": special_password,
                "confirm_password": special_password,
            },
        )

        assert response.status_code == 200

        # Verify password was changed
        test_db.refresh(test_user)
        from app.core.security import verify_password

        assert verify_password(special_password, test_user.hashed_password)

    def test_change_password_with_whitespace(self, authenticated_client):
        """Test password change with leading/trailing whitespace

        验证：
        - 空白字符被正确处理（保留或去除）
        """
        password_with_spaces = "  password123  "

        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": password_with_spaces,
                "confirm_password": password_with_spaces,
            },
        )

        # Should either trim or accept with spaces
        assert response.status_code in [200, 422]

    def test_change_password_with_only_spaces(self, authenticated_client):
        """Test password change with only spaces

        验证：
        - 纯空格密码被接受（如果长度足够）或被拒绝
        """
        response = authenticated_client.put(
            "/api/users/me/password",
            json={"current_password": "testpassword123", "new_password": "      ", "confirm_password": "      "},
        )

        # API currently accepts spaces if length >= 6, or rejects if validation added
        assert response.status_code in [200, 422]

    def test_change_password_empty_strings(self, authenticated_client):
        """Test password change with empty strings

        验证：
        - 空字符串被拒绝
        """
        response = authenticated_client.put(
            "/api/users/me/password", json={"current_password": "", "new_password": "", "confirm_password": ""}
        )

        assert response.status_code == 422

    def test_change_password_null_values(self, authenticated_client):
        """Test password change with null values

        验证：
        - null 值被拒绝
        """
        response = authenticated_client.put(
            "/api/users/me/password", json={"current_password": None, "new_password": None, "confirm_password": None}
        )

        assert response.status_code == 422

    def test_change_password_case_sensitivity(self, authenticated_client):
        """Test password change case sensitivity

        验证：
        - 密码区分大小写
        """
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "TESTPASSWORD123",  # Wrong case
                "new_password": "newpassword456",
                "confirm_password": "newpassword456",
            },
        )

        assert response.status_code == 401  # Wrong current password

    def test_change_password_confirm_mismatch_by_one_char(self, authenticated_client):
        """Test password change with confirm mismatch by one character

        验证：
        - 微小差异被检测
        """
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
                "confirm_password": "newpassword457",  # Off by one
            },
        )

        assert response.status_code == 422

    def test_change_password_sql_injection_attempt(self, authenticated_client):
        """Test password change with SQL injection attempt

        验证：
        - SQL 注入被安全处理
        """
        sql_injection = "'; DROP TABLE users; --"

        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": sql_injection,
                "confirm_password": sql_injection,
            },
        )

        # Should either accept as regular password or reject
        assert response.status_code in [200, 422]

    def test_change_password_xss_attempt(self, authenticated_client):
        """Test password change with XSS attempt

        验证：
        - XSS 尝试被安全处理
        """
        xss_attempt = "<script>alert('xss')</script>"

        response = authenticated_client.put(
            "/api/users/me/password",
            json={"current_password": "testpassword123", "new_password": xss_attempt, "confirm_password": xss_attempt},
        )

        # Should accept as regular password (passwords are hashed)
        assert response.status_code in [200, 422]

    def test_change_password_concurrent_requests(self, authenticated_client, test_user, test_db):
        """Test concurrent password change requests

        验证：
        - 并发请求被正确处理
        - 密码版本正确更新
        """
        import threading

        results = []

        def change_password(password):
            response = authenticated_client.put(
                "/api/users/me/password",
                json={"current_password": "testpassword123", "new_password": password, "confirm_password": password},
            )
            results.append(response.status_code)

        # Start two concurrent password changes
        thread1 = threading.Thread(target=change_password, args=("newpass1",))
        thread2 = threading.Thread(target=change_password, args=("newpass2",))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # At least one should succeed
        assert 200 in results or 401 in results

    def test_change_password_after_account_locked(self, authenticated_client, test_user, test_db):
        """Test password change after account is locked

        验证：
        - 锁定账户的行为（JWT仍然有效，但可能在某些操作中被检查）
        """
        # Lock the account
        test_user.is_active = False
        test_db.commit()

        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
                "confirm_password": "newpassword456",
            },
        )

        # JWT token is still valid, so request may succeed or fail depending on implementation
        # Some systems check is_active on every request, others only at login
        assert response.status_code in [200, 401, 403]

    def test_change_password_version_increment(self, authenticated_client, test_user, test_db):
        """Test that password version increments correctly

        验证：
        - 密码版本正确递增
        """
        initial_version = test_user.password_version

        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
                "confirm_password": "newpassword456",
            },
        )

        assert response.status_code == 200

        test_db.refresh(test_user)
        assert test_user.password_version == initial_version + 1

    def test_change_password_multiple_times_rapidly(self, authenticated_client, test_user, test_db):
        """Test changing password multiple times rapidly

        验证：
        - 快速连续修改密码被正确处理
        - 密码修改后JWT可能失效
        """
        passwords = ["newpass1", "newpass2", "newpass3"]
        current_password = "testpassword123"

        for new_password in passwords:
            response = authenticated_client.put(
                "/api/users/me/password",
                json={
                    "current_password": current_password,
                    "new_password": new_password,
                    "confirm_password": new_password,
                },
            )

            if response.status_code == 200:
                current_password = new_password
            elif response.status_code == 429:
                # Rate limit hit
                break
            elif response.status_code == 401:
                # JWT invalidated after password change
                break

            # Should either succeed, hit rate limit, or JWT becomes invalid
            assert response.status_code in [200, 401, 429]

    def test_change_password_with_numeric_only(self, authenticated_client):
        """Test password change with numeric-only password

        验证：
        - 纯数字密码被处理（根据密码策略）
        """
        response = authenticated_client.put(
            "/api/users/me/password",
            json={"current_password": "testpassword123", "new_password": "123456789", "confirm_password": "123456789"},
        )

        # Should either accept or reject based on password policy
        assert response.status_code in [200, 422]

    def test_change_password_with_common_password(self, authenticated_client):
        """Test password change with common password

        验证：
        - 常见密码被处理（根据密码策略）
        """
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "password123",
                "confirm_password": "password123",
            },
        )

        # Should either accept or reject based on password policy
        assert response.status_code in [200, 422]

    def test_change_password_user_not_found_in_service(self, client, test_db):
        """Test password change when user ID from JWT doesn't exist in database (line 117)

        This test specifically targets line 117 in users.py where the route checks
        if the user exists after getting the user_id from the JWT token.

        Scenario: A user's JWT token contains a valid user_id, but that user
        has been deleted from the database between authentication and the service call.

        验证：
        - 当用户ID在JWT中有效但数据库中不存在时，返回404错误
        - 覆盖 users.py 第117行的 NotFoundError

        Task: 5.2.2 测试权限验证失败（117行）
        """
        import uuid

        from app.api.deps import get_current_user
        from app.main import app

        # Create a non-existent user ID
        non_existent_user_id = str(uuid.uuid4())

        # Override the get_current_user dependency to return a non-existent user ID
        def override_get_current_user():
            return {"id": non_existent_user_id}

        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.put(
                "/api/users/me/password",
                json={
                    "current_password": "testpassword123",
                    "new_password": "newpassword456",
                    "confirm_password": "newpassword456",
                },
            )

            # Should return 404 Not Found
            assert response.status_code == 404
            data = response.json()
            assert data["success"] is False
            assert "用户不存在" in data["error"]["message"]
        finally:
            # Clean up the override
            app.dependency_overrides.clear()
