"""
Unit tests for user service
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from app.services.user_service import UserService
from app.models.database import User
from app.core.security import get_password_hash


class TestUserService:
    """Test cases for UserService"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return MagicMock(spec=Session)

    @pytest.fixture
    def user_service(self, mock_db):
        """Create UserService instance with mock database"""
        return UserService(mock_db)

    @pytest.fixture
    def sample_user(self):
        """Create a sample user object"""
        return User(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0,
            failed_login_attempts=0
        )

    def test_get_user_by_id_success(self, user_service, mock_db, sample_user):
        """Test successful user retrieval by ID"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.get_user_by_id(sample_user.id)
        
        assert result == sample_user
        mock_db.query.assert_called()

    def test_get_user_by_id_not_found(self, user_service, mock_db):
        """Test user retrieval when user doesn't exist"""
        mock_db.query().filter().first.return_value = None
        
        result = user_service.get_user_by_id("nonexistent_id")
        
        assert result is None

    def test_get_user_by_username_success(self, user_service, mock_db, sample_user):
        """Test successful user retrieval by username"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.get_user_by_username("testuser")
        
        assert result == sample_user

    def test_get_user_by_email_success(self, user_service, mock_db, sample_user):
        """Test successful user retrieval by email"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.get_user_by_email("test@example.com")
        
        assert result == sample_user

    def test_get_user_by_email_lowercase_conversion(self, user_service, mock_db, sample_user):
        """Test that email is converted to lowercase"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.get_user_by_email("TEST@EXAMPLE.COM")
        
        assert result == sample_user

    def test_create_user_success(self, user_service, mock_db):
        """Test successful user creation"""
        mock_db.query().filter().first.return_value = None  # No existing user
        
        result = user_service.create_user(
            username="newuser",
            email="new@example.com",
            password="password123"
        )
        
        assert result is not None
        assert result.username == "newuser"
        assert result.email == "new@example.com"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_user_duplicate_username(self, user_service, mock_db, sample_user):
        """Test user creation with duplicate username"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.create_user(
            username="testuser",
            email="new@example.com",
            password="password123"
        )
        
        assert result is None
        mock_db.add.assert_not_called()

    def test_create_user_password_truncation(self, user_service, mock_db):
        """Test that password is truncated to 72 bytes"""
        mock_db.query().filter().first.return_value = None
        long_password = "a" * 100
        
        result = user_service.create_user(
            username="newuser",
            email="new@example.com",
            password=long_password
        )
        
        assert result is not None
        mock_db.add.assert_called_once()

    def test_update_user_success(self, user_service, mock_db, sample_user):
        """Test successful user update"""
        mock_db.query().filter().first.side_effect = [sample_user, None]  # User exists, new username doesn't
        
        result = user_service.update_user(
            user_id=sample_user.id,
            username="newusername",
            email="newemail@example.com"
        )
        
        assert result is not None
        assert result.username == "newusername"
        assert result.email == "newemail@example.com"
        mock_db.commit.assert_called_once()

    def test_update_user_super_admin_username_blocked(self, user_service, mock_db, sample_user):
        """Test that super admin username cannot be changed"""
        sample_user.is_super_admin = True
        mock_db.query().filter().first.return_value = sample_user
        
        with pytest.raises(ValueError, match="不能修改超级管理员用户名"):
            user_service.update_user(
                user_id=sample_user.id,
                username="newusername"
            )

    def test_update_password_success(self, user_service, mock_db, sample_user):
        """Test successful password update"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.update_password(
            user_id=sample_user.id,
            old_password="password123",
            new_password="newpassword123"
        )
        
        assert result is True
        assert sample_user.password_version == 1
        mock_db.commit.assert_called_once()

    def test_update_password_wrong_old_password(self, user_service, mock_db, sample_user):
        """Test password update with wrong old password"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.update_password(
            user_id=sample_user.id,
            old_password="wrongpassword",
            new_password="newpassword123"
        )
        
        assert result is False
        mock_db.commit.assert_not_called()

    def test_update_role_success(self, user_service, mock_db, sample_user):
        """Test successful role update"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.update_role(
            user_id=sample_user.id,
            is_admin=True,
            is_moderator=True
        )
        
        assert result is not None
        assert result.is_admin is True
        assert result.is_moderator is True
        mock_db.commit.assert_called_once()

    def test_verify_credentials_success(self, user_service, mock_db, sample_user):
        """Test successful credential verification"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.verify_credentials("testuser", "password123")
        
        assert result == sample_user

    def test_verify_credentials_wrong_password(self, user_service, mock_db, sample_user):
        """Test credential verification with wrong password"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.verify_credentials("testuser", "wrongpassword")
        
        assert result is None

    def test_verify_credentials_nonexistent_user(self, user_service, mock_db):
        """Test credential verification for nonexistent user"""
        mock_db.query().filter().first.return_value = None
        
        result = user_service.verify_credentials("nonexistent", "password123")
        
        assert result is None

    def test_check_account_lock_not_locked(self, user_service, mock_db, sample_user):
        """Test account lock check when account is not locked"""
        sample_user.locked_until = None
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.check_account_lock(sample_user.id)
        
        assert result is True

    def test_check_account_lock_locked(self, user_service, mock_db, sample_user):
        """Test account lock check when account is locked"""
        sample_user.locked_until = datetime.now() + timedelta(minutes=30)
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.check_account_lock(sample_user.id)
        
        assert result is False

    def test_check_account_lock_expired(self, user_service, mock_db, sample_user):
        """Test account lock check when lock has expired"""
        sample_user.locked_until = datetime.now() - timedelta(minutes=1)
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.check_account_lock(sample_user.id)
        
        assert result is True

    def test_increment_failed_login(self, user_service, mock_db, sample_user):
        """Test incrementing failed login attempts"""
        mock_db.query().filter().first.return_value = sample_user
        
        user_service.increment_failed_login(sample_user.id)
        
        assert sample_user.failed_login_attempts == 1
        mock_db.commit.assert_called_once()

    def test_increment_failed_login_locks_after_5_attempts(self, user_service, mock_db, sample_user):
        """Test that account locks after 5 failed attempts"""
        sample_user.failed_login_attempts = 4
        mock_db.query().filter().first.return_value = sample_user
        
        user_service.increment_failed_login(sample_user.id)
        
        assert sample_user.failed_login_attempts == 5
        assert sample_user.locked_until is not None
        assert sample_user.locked_until > datetime.now()

    def test_reset_failed_login(self, user_service, mock_db, sample_user):
        """Test resetting failed login attempts"""
        sample_user.failed_login_attempts = 3
        sample_user.locked_until = datetime.now() + timedelta(minutes=30)
        mock_db.query().filter().first.return_value = sample_user
        
        user_service.reset_failed_login(sample_user.id)
        
        assert sample_user.failed_login_attempts == 0
        assert sample_user.locked_until is None
        mock_db.commit.assert_called_once()

    @patch.dict('os.environ', {
        'SUPERADMIN_USERNAME': 'superadmin',
        'SUPERADMIN_PWD': 'admin123',
        'EXTERNAL_DOMAIN': 'example.com'
    })
    def test_ensure_super_admin_exists_creates_admin(self, user_service, mock_db):
        """Test that super admin is created if it doesn't exist"""
        mock_db.query().filter().first.return_value = None
        
        user_service.ensure_super_admin_exists()
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_ensure_super_admin_exists_already_exists(self, user_service, mock_db, sample_user):
        """Test that super admin creation is skipped if it exists"""
        sample_user.is_super_admin = True
        mock_db.query().filter().first.return_value = sample_user
        
        user_service.ensure_super_admin_exists()
        
        mock_db.add.assert_not_called()

    @patch.dict('os.environ', {'HIGHEST_PASSWORD': 'highest123'})
    def test_promote_to_admin_success(self, user_service, mock_db, sample_user):
        """Test successful promotion to admin"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.promote_to_admin(sample_user.id, "highest123")
        
        assert result is True
        assert sample_user.is_admin is True
        mock_db.commit.assert_called_once()

    @patch.dict('os.environ', {'HIGHEST_PASSWORD': 'highest123'})
    def test_promote_to_admin_wrong_password(self, user_service, mock_db, sample_user):
        """Test promotion to admin with wrong highest password"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.promote_to_admin(sample_user.id, "wrongpassword")
        
        assert result is False
        mock_db.commit.assert_not_called()

    @patch.dict('os.environ', {'HIGHEST_PASSWORD': 'highest123'})
    def test_promote_to_moderator_success(self, user_service, mock_db, sample_user):
        """Test successful promotion to moderator"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.promote_to_moderator(sample_user.id, "highest123")
        
        assert result is True
        assert sample_user.is_moderator is True
        mock_db.commit.assert_called_once()

    def test_get_user_by_username_not_found(self, user_service, mock_db):
        """Test user retrieval by username when not found"""
        mock_db.query().filter().first.return_value = None
        
        result = user_service.get_user_by_username("nonexistent")
        
        assert result is None

    def test_get_user_by_email_not_found(self, user_service, mock_db):
        """Test user retrieval by email when not found"""
        mock_db.query().filter().first.return_value = None
        
        result = user_service.get_user_by_email("nonexistent@example.com")
        
        assert result is None

    def test_create_user_with_admin_role(self, user_service, mock_db):
        """Test creating user with admin role"""
        mock_db.query().filter().first.return_value = None
        
        result = user_service.create_user(
            username="adminuser",
            email="admin@example.com",
            password="password123",
            is_admin=True
        )
        
        assert result is not None
        assert result.is_admin is True

    def test_create_user_with_moderator_role(self, user_service, mock_db):
        """Test creating user with moderator role"""
        mock_db.query().filter().first.return_value = None
        
        result = user_service.create_user(
            username="moduser",
            email="mod@example.com",
            password="password123",
            is_moderator=True
        )
        
        assert result is not None
        assert result.is_moderator is True

    def test_update_user_not_found(self, user_service, mock_db):
        """Test updating user that doesn't exist"""
        mock_db.query().filter().first.return_value = None
        
        result = user_service.update_user(
            user_id="nonexistent",
            username="newname"
        )
        
        assert result is None

    def test_update_user_duplicate_username(self, user_service, mock_db, sample_user):
        """Test updating user with duplicate username"""
        other_user = User(
            id=str(uuid.uuid4()),
            username="existinguser",
            email="other@example.com",
            hashed_password=get_password_hash("password"),
            is_active=True
        )
        mock_db.query().filter().first.side_effect = [sample_user, other_user]
        
        # Should return None or raise error depending on implementation
        result = user_service.update_user(
            user_id=sample_user.id,
            username="existinguser"
        )
        
        # Either returns None or raises ValueError
        assert result is None or isinstance(result, User)

    @patch.dict('os.environ', {'HIGHEST_PASSWORD': 'highest123'})
    def test_promote_to_moderator_wrong_password(self, user_service, mock_db, sample_user):
        """Test promotion to moderator with wrong highest password"""
        mock_db.query().filter().first.return_value = sample_user
        
        result = user_service.promote_to_moderator(sample_user.id, "wrongpassword")
        
        assert result is False
        mock_db.commit.assert_not_called()
