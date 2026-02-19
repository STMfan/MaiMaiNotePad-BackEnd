"""Integration tests for user routes"""
import pytest
import os
from io import BytesIO
from PIL import Image
from datetime import datetime


class TestCurrentUser:
    """Tests for GET /api/users/me endpoint"""

    def test_get_current_user_success(self, authenticated_client, test_user):
        """Test getting current user information"""
        response = authenticated_client.get("/api/users/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "用户信息获取成功"
        assert data["data"]["id"] == test_user.id
        assert data["data"]["username"] == test_user.username
        assert data["data"]["email"] == test_user.email
        assert data["data"]["role"] == "user"
        assert "avatar_url" in data["data"]
        assert "is_muted" in data["data"]

    def test_get_current_user_unauthenticated(self, client):
        """Test getting current user without authentication"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create a client without authentication
        unauthenticated_client = TestClient(app)
        response = unauthenticated_client.get("/api/users/me")
        
        assert response.status_code == 401

    def test_get_current_user_with_avatar(self, authenticated_client, test_user, test_db):
        """Test getting current user with avatar"""
        # Set avatar path for user
        test_user.avatar_path = "uploads/avatars/test_avatar.jpg"
        test_user.avatar_updated_at = datetime.now()
        test_db.commit()
        
        response = authenticated_client.get("/api/users/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["avatar_url"] == "/uploads/avatars/test_avatar.jpg"
        assert data["data"]["avatar_updated_at"] is not None


class TestPasswordChange:
    """Tests for PUT /api/users/me/password endpoint"""

    def test_change_password_success(self, authenticated_client, test_user):
        """Test successful password change"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "密码修改成功，请重新登录"

    def test_change_password_wrong_current(self, authenticated_client):
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
        data = response.json()
        assert "当前密码错误" in data["message"]

    def test_change_password_mismatch(self, authenticated_client):
        """Test password change with mismatched new passwords"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword123",
                "confirm_password": "differentpassword123"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "不匹配" in data["message"]

    def test_change_password_too_short(self, authenticated_client):
        """Test password change with too short password"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "short",
                "confirm_password": "short"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "长度" in data["message"]

    def test_change_password_same_as_current(self, authenticated_client):
        """Test password change with same password as current"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "testpassword123",
                "confirm_password": "testpassword123"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "不能与当前密码相同" in data["message"]

    def test_change_password_missing_fields(self, authenticated_client):
        """Test password change with missing fields"""
        response = authenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword123"
                # Missing confirm_password
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "未填写" in data["message"]

    def test_change_password_unauthenticated(self, client):
        """Test password change without authentication"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        unauthenticated_client = TestClient(app)
        response = unauthenticated_client.put(
            "/api/users/me/password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            }
        )
        
        assert response.status_code == 401



class TestAvatarUpload:
    """Tests for POST /api/users/me/avatar endpoint"""

    def test_upload_avatar_success(self, authenticated_client, test_user):
        """Test successful avatar upload"""
        # Create a test image
        img = Image.new('RGB', (200, 200), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        response = authenticated_client.post(
            "/api/users/me/avatar",
            files={"avatar": ("test_avatar.jpg", img_bytes, "image/jpeg")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "头像上传成功"
        assert "avatar_url" in data["data"]
        assert "avatar_updated_at" in data["data"]

    def test_upload_avatar_png(self, authenticated_client, test_user):
        """Test avatar upload with PNG format"""
        img = Image.new('RGB', (200, 200), color='blue')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        response = authenticated_client.post(
            "/api/users/me/avatar",
            files={"avatar": ("test_avatar.png", img_bytes, "image/png")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "头像上传成功"

    def test_upload_avatar_invalid_type(self, authenticated_client):
        """Test avatar upload with invalid file type"""
        # Create a text file
        text_file = BytesIO(b"This is not an image")
        
        response = authenticated_client.post(
            "/api/users/me/avatar",
            files={"avatar": ("test.txt", text_file, "text/plain")}
        )
        
        assert response.status_code == 400

    def test_upload_avatar_too_large(self, authenticated_client):
        """Test avatar upload with file too large"""
        # Create a large image (> 5MB)
        img = Image.new('RGB', (5000, 5000), color='green')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG', quality=100)
        img_bytes.seek(0)
        
        response = authenticated_client.post(
            "/api/users/me/avatar",
            files={"avatar": ("large_avatar.jpg", img_bytes, "image/jpeg")}
        )
        
        # Should fail validation
        assert response.status_code == 400

    def test_upload_avatar_replaces_old(self, authenticated_client, test_user, test_db):
        """Test that uploading new avatar replaces old one"""
        # Upload first avatar
        img1 = Image.new('RGB', (200, 200), color='red')
        img1_bytes = BytesIO()
        img1.save(img1_bytes, format='JPEG')
        img1_bytes.seek(0)
        
        response1 = authenticated_client.post(
            "/api/users/me/avatar",
            files={"avatar": ("avatar1.jpg", img1_bytes, "image/jpeg")}
        )
        assert response1.status_code == 200
        old_avatar_url = response1.json()["data"]["avatar_url"]
        
        # Upload second avatar
        img2 = Image.new('RGB', (200, 200), color='blue')
        img2_bytes = BytesIO()
        img2.save(img2_bytes, format='JPEG')
        img2_bytes.seek(0)
        
        response2 = authenticated_client.post(
            "/api/users/me/avatar",
            files={"avatar": ("avatar2.jpg", img2_bytes, "image/jpeg")}
        )
        assert response2.status_code == 200
        new_avatar_url = response2.json()["data"]["avatar_url"]
        
        # URLs should be different
        assert old_avatar_url != new_avatar_url

    def test_upload_avatar_unauthenticated(self, client):
        """Test avatar upload without authentication"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        unauthenticated_client = TestClient(app)
        img = Image.new('RGB', (200, 200), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        response = unauthenticated_client.post(
            "/api/users/me/avatar",
            files={"avatar": ("test_avatar.jpg", img_bytes, "image/jpeg")}
        )
        
        assert response.status_code == 401


class TestAvatarDelete:
    """Tests for DELETE /api/users/me/avatar endpoint"""

    def test_delete_avatar_success(self, authenticated_client, test_user, test_db):
        """Test successful avatar deletion"""
        # First upload an avatar
        img = Image.new('RGB', (200, 200), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        authenticated_client.post(
            "/api/users/me/avatar",
            files={"avatar": ("test_avatar.jpg", img_bytes, "image/jpeg")}
        )
        
        # Now delete it
        response = authenticated_client.delete("/api/users/me/avatar")
        
        assert response.status_code == 200
        data = response.json()
        assert "删除" in data["message"]

    def test_delete_avatar_when_none_exists(self, authenticated_client, test_user):
        """Test deleting avatar when user has no avatar"""
        response = authenticated_client.delete("/api/users/me/avatar")
        
        assert response.status_code == 200
        data = response.json()
        assert "删除" in data["message"]

    def test_delete_avatar_unauthenticated(self, client):
        """Test avatar deletion without authentication"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        unauthenticated_client = TestClient(app)
        response = unauthenticated_client.delete("/api/users/me/avatar")
        
        assert response.status_code == 401


class TestGetUserAvatar:
    """Tests for GET /api/users/{user_id}/avatar endpoint"""

    def test_get_user_avatar_with_existing_avatar(self, authenticated_client, test_user, test_db):
        """Test getting user avatar when avatar exists"""
        # Upload an avatar first
        img = Image.new('RGB', (200, 200), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        authenticated_client.post(
            "/api/users/me/avatar",
            files={"avatar": ("test_avatar.jpg", img_bytes, "image/jpeg")}
        )
        
        # Get the avatar
        response = authenticated_client.get(f"/api/users/{test_user.id}/avatar")
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/")

    def test_get_user_avatar_generates_default(self, authenticated_client, test_user):
        """Test getting user avatar generates default when none exists"""
        response = authenticated_client.get(f"/api/users/{test_user.id}/avatar")
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/")

    def test_get_user_avatar_with_size_parameter(self, authenticated_client, test_user):
        """Test getting user avatar with custom size"""
        response = authenticated_client.get(
            f"/api/users/{test_user.id}/avatar",
            params={"size": 100}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/")

    def test_get_user_avatar_nonexistent_user(self, authenticated_client):
        """Test getting avatar for nonexistent user"""
        response = authenticated_client.get("/api/users/nonexistent-id/avatar")
        
        assert response.status_code == 404



class TestUserStars:
    """Tests for GET /api/users/stars endpoint"""

    def test_get_user_stars_empty(self, authenticated_client):
        """Test getting user stars when user has no stars"""
        response = authenticated_client.get("/api/users/stars")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0

    def test_get_user_stars_with_knowledge(self, authenticated_client, test_user, test_db, factory):
        """Test getting user stars with knowledge bases"""
        # Create a knowledge base
        kb = factory.create_knowledge_base(
            uploader=test_user,
            is_public=True,
            status="approved"
        )
        
        # Create a star record
        from app.models.database import StarRecord
        star = StarRecord(
            user_id=test_user.id,
            target_id=kb.id,
            target_type="knowledge"
        )
        test_db.add(star)
        test_db.commit()
        
        response = authenticated_client.get("/api/users/stars")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["type"] == "knowledge"
        assert data["data"][0]["target_id"] == kb.id

    def test_get_user_stars_with_persona(self, authenticated_client, test_user, test_db, factory):
        """Test getting user stars with persona cards"""
        # Create a persona card
        pc = factory.create_persona_card(
            uploader=test_user,
            is_public=True,
            status="approved"
        )
        
        # Create a star record
        from app.models.database import StarRecord
        star = StarRecord(
            user_id=test_user.id,
            target_id=pc.id,
            target_type="persona"
        )
        test_db.add(star)
        test_db.commit()
        
        response = authenticated_client.get("/api/users/stars")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["type"] == "persona"
        assert data["data"][0]["target_id"] == pc.id

    def test_get_user_stars_pagination(self, authenticated_client, test_user, test_db, factory):
        """Test user stars pagination"""
        # Create multiple knowledge bases and star them
        for i in range(5):
            kb = factory.create_knowledge_base(
                name=f"KB {i}",
                uploader=test_user,
                is_public=True,
                status="approved"
            )
            from app.models.database import StarRecord
            star = StarRecord(
                user_id=test_user.id,
                target_id=kb.id,
                target_type="knowledge"
            )
            test_db.add(star)
        test_db.commit()
        
        # Get first page
        response = authenticated_client.get("/api/users/stars?page=1&page_size=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1

    def test_get_user_stars_filter_by_type(self, authenticated_client, test_user, test_db, factory):
        """Test filtering user stars by type"""
        # Create both knowledge and persona
        kb = factory.create_knowledge_base(
            uploader=test_user,
            is_public=True,
            status="approved"
        )
        pc = factory.create_persona_card(
            uploader=test_user,
            is_public=True,
            status="approved"
        )
        
        from app.models.database import StarRecord
        star1 = StarRecord(user_id=test_user.id, target_id=kb.id, target_type="knowledge")
        star2 = StarRecord(user_id=test_user.id, target_id=pc.id, target_type="persona")
        test_db.add_all([star1, star2])
        test_db.commit()
        
        # Filter by knowledge
        response = authenticated_client.get("/api/users/stars?type=knowledge")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["type"] == "knowledge"

    def test_get_user_stars_with_details(self, authenticated_client, test_user, test_db, factory):
        """Test getting user stars with full details"""
        kb = factory.create_knowledge_base(
            uploader=test_user,
            is_public=True,
            status="approved"
        )
        
        from app.models.database import StarRecord
        star = StarRecord(user_id=test_user.id, target_id=kb.id, target_type="knowledge")
        test_db.add(star)
        test_db.commit()
        
        response = authenticated_client.get("/api/users/stars?include_details=true")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1

    def test_get_user_stars_sorting(self, authenticated_client, test_user, test_db, factory):
        """Test sorting user stars"""
        # Create knowledge bases with different star counts
        kb1 = factory.create_knowledge_base(
            name="KB 1",
            uploader=test_user,
            is_public=True,
            status="approved"
        )
        kb1.star_count = 10
        
        kb2 = factory.create_knowledge_base(
            name="KB 2",
            uploader=test_user,
            is_public=True,
            status="approved"
        )
        kb2.star_count = 5
        test_db.commit()
        
        from app.models.database import StarRecord
        star1 = StarRecord(user_id=test_user.id, target_id=kb1.id, target_type="knowledge")
        star2 = StarRecord(user_id=test_user.id, target_id=kb2.id, target_type="knowledge")
        test_db.add_all([star1, star2])
        test_db.commit()
        
        # Sort by star count descending
        response = authenticated_client.get("/api/users/stars?sort_by=star_count&sort_order=desc")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["data"][0]["star_count"] >= data["data"][1]["star_count"]


class TestUploadHistory:
    """Tests for GET /api/users/me/upload-history endpoint"""

    @pytest.mark.skip(reason="UserService.get_upload_records_by_uploader not implemented")
    def test_get_upload_history_empty(self, authenticated_client):
        """Test getting upload history when user has no uploads"""
        response = authenticated_client.get("/api/users/me/upload-history")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0

    @pytest.mark.skip(reason="UserService.get_upload_records_by_uploader not implemented")
    def test_get_upload_history_with_records(self, authenticated_client, test_user, test_db):
        """Test getting upload history with records"""
        from app.models.database import UploadRecord
        
        # Create upload records
        record = UploadRecord(
            uploader_id=test_user.id,
            target_id="test-kb-id",
            target_type="knowledge",
            name="Test KB",
            description="Test description",
            status="approved"
        )
        test_db.add(record)
        test_db.commit()
        
        response = authenticated_client.get("/api/users/me/upload-history")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Test KB"
        assert data["data"][0]["type"] == "knowledge"

    @pytest.mark.skip(reason="UserService.get_upload_records_by_uploader not implemented")
    def test_get_upload_history_pagination(self, authenticated_client, test_user, test_db):
        """Test upload history pagination"""
        from app.models.database import UploadRecord
        
        # Create multiple records
        for i in range(5):
            record = UploadRecord(
                uploader_id=test_user.id,
                target_id=f"test-id-{i}",
                target_type="knowledge",
                name=f"KB {i}",
                status="approved"
            )
            test_db.add(record)
        test_db.commit()
        
        response = authenticated_client.get("/api/users/me/upload-history?page=1&page_size=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["total"] == 5

    @pytest.mark.skip(reason="UserService.get_upload_records_by_uploader not implemented")
    def test_get_upload_history_status_mapping(self, authenticated_client, test_user, test_db):
        """Test upload history status mapping"""
        from app.models.database import UploadRecord
        
        # Create records with different statuses
        statuses = [
            ("approved", "success"),
            ("rejected", "failed"),
            ("pending", "processing")
        ]
        
        for db_status, expected_status in statuses:
            record = UploadRecord(
                uploader_id=test_user.id,
                target_id=f"test-{db_status}",
                target_type="knowledge",
                name=f"KB {db_status}",
                status=db_status
            )
            test_db.add(record)
        test_db.commit()
        
        response = authenticated_client.get("/api/users/me/upload-history")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3


class TestUploadStats:
    """Tests for GET /api/users/me/upload-stats endpoint"""

    @pytest.mark.skip(reason="UserService.get_upload_stats_by_uploader not implemented")
    def test_get_upload_stats_empty(self, authenticated_client):
        """Test getting upload stats when user has no uploads"""
        response = authenticated_client.get("/api/users/me/upload-stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 0
        assert data["data"]["success"] == 0
        assert data["data"]["pending"] == 0
        assert data["data"]["failed"] == 0

    @pytest.mark.skip(reason="UserService.get_upload_stats_by_uploader not implemented")
    def test_get_upload_stats_with_records(self, authenticated_client, test_user, test_db):
        """Test getting upload stats with records"""
        from app.models.database import UploadRecord
        
        # Create records with different statuses
        records = [
            UploadRecord(uploader_id=test_user.id, target_id="1", target_type="knowledge", name="KB1", status="approved"),
            UploadRecord(uploader_id=test_user.id, target_id="2", target_type="knowledge", name="KB2", status="approved"),
            UploadRecord(uploader_id=test_user.id, target_id="3", target_type="persona", name="PC1", status="pending"),
            UploadRecord(uploader_id=test_user.id, target_id="4", target_type="persona", name="PC2", status="rejected"),
        ]
        for record in records:
            test_db.add(record)
        test_db.commit()
        
        response = authenticated_client.get("/api/users/me/upload-stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 4
        assert data["data"]["success"] == 2
        assert data["data"]["pending"] == 1
        assert data["data"]["failed"] == 1
        assert data["data"]["knowledge"] == 2
        assert data["data"]["persona"] == 2


class TestDashboardStats:
    """Tests for GET /api/users/me/dashboard-stats endpoint"""

    @pytest.mark.skip(reason="UserService.get_upload_stats_by_uploader not implemented")
    def test_get_dashboard_stats_empty(self, authenticated_client):
        """Test getting dashboard stats when user has no data"""
        response = authenticated_client.get("/api/users/me/dashboard-stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["totalUploads"] == 0
        assert data["data"]["totalDownloads"] == 0
        assert data["data"]["totalStars"] == 0

    @pytest.mark.skip(reason="UserService.get_upload_stats_by_uploader not implemented")
    def test_get_dashboard_stats_with_data(self, authenticated_client, test_user, test_db, factory):
        """Test getting dashboard stats with data"""
        # Create knowledge base with downloads and stars
        kb = factory.create_knowledge_base(
            uploader=test_user,
            is_public=True,
            status="approved"
        )
        kb.downloads = 10
        kb.star_count = 5
        
        # Create persona card with downloads and stars
        pc = factory.create_persona_card(
            uploader=test_user,
            is_public=True,
            status="approved"
        )
        pc.downloads = 8
        pc.star_count = 3
        test_db.commit()
        
        # Create upload records
        from app.models.database import UploadRecord
        record1 = UploadRecord(uploader_id=test_user.id, target_id=kb.id, target_type="knowledge", name="KB", status="approved")
        record2 = UploadRecord(uploader_id=test_user.id, target_id=pc.id, target_type="persona", name="PC", status="approved")
        test_db.add_all([record1, record2])
        test_db.commit()
        
        response = authenticated_client.get("/api/users/me/dashboard-stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["totalUploads"] == 2
        assert data["data"]["knowledgeUploads"] == 1
        assert data["data"]["personaUploads"] == 1
        assert data["data"]["totalDownloads"] == 18
        assert data["data"]["knowledgeDownloads"] == 10
        assert data["data"]["personaDownloads"] == 8
        assert data["data"]["totalStars"] == 8
        assert data["data"]["knowledgeStars"] == 5
        assert data["data"]["personaStars"] == 3


class TestDashboardTrends:
    """Tests for GET /api/users/me/dashboard-trends endpoint"""

    @pytest.mark.skip(reason="UserService.get_dashboard_trend_stats not implemented")
    def test_get_dashboard_trends_default(self, authenticated_client):
        """Test getting dashboard trends with default parameters"""
        response = authenticated_client.get("/api/users/me/dashboard-trends")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    @pytest.mark.skip(reason="UserService.get_dashboard_trend_stats not implemented")
    def test_get_dashboard_trends_custom_days(self, authenticated_client):
        """Test getting dashboard trends with custom days parameter"""
        response = authenticated_client.get("/api/users/me/dashboard-trends?days=7")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    @pytest.mark.skip(reason="UserService.get_dashboard_trend_stats not implemented")
    def test_get_dashboard_trends_max_days(self, authenticated_client):
        """Test getting dashboard trends with maximum days"""
        response = authenticated_client.get("/api/users/me/dashboard-trends?days=90")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    @pytest.mark.skip(reason="UserService.get_dashboard_trend_stats not implemented")
    def test_get_dashboard_trends_invalid_days(self, authenticated_client):
        """Test getting dashboard trends with invalid days parameter"""
        # Days > 90 should be rejected
        response = authenticated_client.get("/api/users/me/dashboard-trends?days=100")
        
        assert response.status_code == 422  # Validation error
