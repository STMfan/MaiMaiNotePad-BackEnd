"""
UserService 单元测试

测试用户管理业务逻辑，包括 CRUD 操作、认证、密码管理和角色管理。

需求: 2.2 - 服务层单元测试
"""

import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.services.user_service import UserService
from app.models.database import User
from app.core.security import get_password_hash, verify_password


class TestUserRetrieval:
    """测试用户检索方法"""
    
    def test_get_user_by_id_success(self):
        """测试通过 ID 成功获取用户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        expected_user = Mock(spec=User)
        expected_user.id = "user-123"
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=expected_user)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        user = service.get_user_by_id("user-123")
        
        assert user == expected_user
        db.query.assert_called_once_with(User)
    
    def test_get_user_by_id_not_found(self):
        """测试获取不存在的用户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        user = service.get_user_by_id("nonexistent-id")
        
        assert user is None
    
    def test_get_user_by_id_database_error(self):
        """测试数据库错误时获取用户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        db.query = Mock(side_effect=Exception("Database error"))
        
        user = service.get_user_by_id("user-123")
        
        assert user is None
    
    def test_get_user_by_username_success(self):
        """测试通过用户名成功获取用户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        expected_user = Mock(spec=User)
        expected_user.username = "testuser"
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=expected_user)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        user = service.get_user_by_username("testuser")
        
        assert user == expected_user
    
    def test_get_user_by_username_not_found(self):
        """测试获取不存在的用户名"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        user = service.get_user_by_username("nonexistent")
        
        assert user is None

    def test_get_user_by_email_success(self):
        """测试通过邮箱成功获取用户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        expected_user = Mock(spec=User)
        expected_user.email = "test@example.com"
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=expected_user)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        user = service.get_user_by_email("test@example.com")
        
        assert user == expected_user
    
    def test_get_user_by_email_case_insensitive(self):
        """测试邮箱查询不区分大小写"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        expected_user = Mock(spec=User)
        expected_user.email = "test@example.com"
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=expected_user)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        # Test with uppercase email
        user = service.get_user_by_email("TEST@EXAMPLE.COM")
        
        assert user == expected_user
    
    def test_get_all_users_success(self):
        """测试成功获取所有用户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        expected_users = [Mock(spec=User), Mock(spec=User)]
        
        mock_query = Mock()
        mock_query.all = Mock(return_value=expected_users)
        db.query = Mock(return_value=mock_query)
        
        users = service.get_all_users()
        
        assert users == expected_users
        assert len(users) == 2

    def test_get_all_users_empty(self):
        """测试数据库为空时获取所有用户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        mock_query = Mock()
        mock_query.all = Mock(return_value=[])
        db.query = Mock(return_value=mock_query)
        
        users = service.get_all_users()
        
        assert users == []


class TestUserCreation:
    """测试用户创建逻辑"""
    
    @patch('app.services.user_service.get_password_hash')
    @patch('app.services.user_service.uuid.uuid4')
    def test_create_user_success(self, mock_uuid, mock_hash):
        """测试成功创建用户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        mock_uuid.return_value = Mock(hex="test-uuid-123")
        mock_hash.return_value = "hashed_password"
        
        # Mock get_user_by_username and get_user_by_email to return None (user doesn't exist)
        service.get_user_by_username = Mock(return_value=None)
        service.get_user_by_email = Mock(return_value=None)
        
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        
        user = service.create_user(
            username="newuser",
            email="new@example.com",
            password="password123"
        )
        
        assert user is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.is_active is True
        assert user.is_admin is False
        assert db.add.called
        assert db.commit.called

    def test_create_user_duplicate_username(self):
        """测试创建重复用户名失败"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        existing_user = Mock(spec=User)
        existing_user.username = "existinguser"
        
        service.get_user_by_username = Mock(return_value=existing_user)
        
        user = service.create_user(
            username="existinguser",
            email="new@example.com",
            password="password123"
        )
        
        assert user is None
    
    def test_create_user_duplicate_email(self):
        """测试创建重复邮箱失败"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        existing_user = Mock(spec=User)
        existing_user.email = "existing@example.com"
        
        service.get_user_by_username = Mock(return_value=None)
        service.get_user_by_email = Mock(return_value=existing_user)
        
        user = service.create_user(
            username="newuser",
            email="existing@example.com",
            password="password123"
        )
        
        assert user is None
    
    @patch('app.services.user_service.get_password_hash')
    @patch('app.services.user_service.uuid.uuid4')
    def test_create_admin_user(self, mock_uuid, mock_hash):
        """测试创建管理员用户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        mock_uuid.return_value = Mock(hex="admin-uuid")
        mock_hash.return_value = "hashed_password"
        
        service.get_user_by_username = Mock(return_value=None)
        service.get_user_by_email = Mock(return_value=None)
        
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        
        user = service.create_user(
            username="adminuser",
            email="admin@example.com",
            password="password123",
            is_admin=True
        )
        
        assert user.is_admin is True

    @patch('app.services.user_service.get_password_hash')
    def test_create_user_password_truncation(self, mock_hash):
        """测试密码截断为 72 字节（bcrypt 限制）"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        mock_hash.return_value = "hashed_password"
        
        service.get_user_by_username = Mock(return_value=None)
        service.get_user_by_email = Mock(return_value=None)
        
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        
        # Create user with very long password
        long_password = "a" * 100
        user = service.create_user(
            username="testuser",
            email="test@example.com",
            password=long_password
        )
        
        # Verify password was truncated to 72 bytes before hashing
        mock_hash.assert_called_once_with(long_password[:72])


class TestUserUpdate:
    """测试用户更新逻辑"""
    
    def test_update_user_username(self):
        """测试更新用户名"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        existing_user = Mock(spec=User)
        existing_user.id = "user-123"
        existing_user.username = "oldusername"
        existing_user.email = "test@example.com"
        existing_user.is_super_admin = False
        
        service.get_user_by_id = Mock(return_value=existing_user)
        service.get_user_by_username = Mock(return_value=None)
        
        db.commit = Mock()
        db.refresh = Mock()
        
        updated_user = service.update_user("user-123", username="newusername")
        
        assert updated_user.username == "newusername"
        assert db.commit.called

    def test_update_user_email(self):
        """测试更新用户邮箱"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        existing_user = Mock(spec=User)
        existing_user.id = "user-123"
        existing_user.username = "testuser"
        existing_user.email = "old@example.com"
        
        service.get_user_by_id = Mock(return_value=existing_user)
        service.get_user_by_email = Mock(return_value=None)
        
        db.commit = Mock()
        db.refresh = Mock()
        
        updated_user = service.update_user("user-123", email="new@example.com")
        
        assert updated_user.email == "new@example.com"
        assert db.commit.called
    
    def test_update_user_duplicate_username(self):
        """测试更新为重复用户名失败"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        existing_user = Mock(spec=User)
        existing_user.id = "user-123"
        existing_user.username = "oldusername"
        existing_user.is_super_admin = False
        
        other_user = Mock(spec=User)
        other_user.id = "user-456"
        other_user.username = "takenusername"
        
        service.get_user_by_id = Mock(return_value=existing_user)
        service.get_user_by_username = Mock(return_value=other_user)
        
        updated_user = service.update_user("user-123", username="takenusername")
        
        assert updated_user is None
    
    def test_update_super_admin_username_blocked(self):
        """测试超级管理员用户名不能修改"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        super_admin = Mock(spec=User)
        super_admin.id = "admin-123"
        super_admin.username = "superadmin"
        super_admin.is_super_admin = True
        
        service.get_user_by_id = Mock(return_value=super_admin)
        
        with pytest.raises(ValueError, match="不能修改超级管理员用户名"):
            service.update_user("admin-123", username="newsuperadmin")

    def test_update_user_not_found(self):
        """测试更新不存在的用户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        service.get_user_by_id = Mock(return_value=None)
        
        updated_user = service.update_user("nonexistent-id", username="newname")
        
        assert updated_user is None


class TestPasswordManagement:
    """测试密码管理逻辑"""
    
    @patch('app.services.user_service.verify_password')
    @patch('app.services.user_service.get_password_hash')
    def test_update_password_success(self, mock_hash, mock_verify):
        """测试成功更新密码"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.hashed_password = "old_hash"
        user.password_version = 0
        
        service.get_user_by_id = Mock(return_value=user)
        mock_verify.return_value = True
        mock_hash.return_value = "new_hash"
        
        db.commit = Mock()
        
        result = service.update_password("user-123", "oldpassword", "newpassword")
        
        assert result is True
        assert user.hashed_password == "new_hash"
        assert user.password_version == 1
        assert db.commit.called
    
    @patch('app.services.user_service.verify_password')
    def test_update_password_wrong_old_password(self, mock_verify):
        """测试旧密码错误时更新失败"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.hashed_password = "old_hash"
        
        service.get_user_by_id = Mock(return_value=user)
        mock_verify.return_value = False
        
        result = service.update_password("user-123", "wrongpassword", "newpassword")
        
        assert result is False

    def test_update_password_user_not_found(self):
        """测试更新不存在用户的密码"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        service.get_user_by_id = Mock(return_value=None)
        
        result = service.update_password("nonexistent-id", "oldpass", "newpass")
        
        assert result is False
    
    @patch('app.services.user_service.verify_password')
    @patch('app.services.user_service.get_password_hash')
    def test_update_password_increments_version(self, mock_hash, mock_verify):
        """测试密码更新递增版本号"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.hashed_password = "old_hash"
        user.password_version = 5
        
        service.get_user_by_id = Mock(return_value=user)
        mock_verify.return_value = True
        mock_hash.return_value = "new_hash"
        
        db.commit = Mock()
        
        service.update_password("user-123", "oldpass", "newpass")
        
        assert user.password_version == 6


class TestRoleManagement:
    """测试角色管理逻辑"""
    
    def test_update_role_to_admin(self):
        """测试将用户角色更新为管理员"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.is_admin = False
        user.is_moderator = False
        
        service.get_user_by_id = Mock(return_value=user)
        
        db.commit = Mock()
        db.refresh = Mock()
        
        updated_user = service.update_role("user-123", is_admin=True)
        
        assert updated_user.is_admin is True
        assert db.commit.called

    def test_update_role_to_moderator(self):
        """测试将用户角色更新为审核员"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.is_admin = False
        user.is_moderator = False
        
        service.get_user_by_id = Mock(return_value=user)
        
        db.commit = Mock()
        db.refresh = Mock()
        
        updated_user = service.update_role("user-123", is_moderator=True)
        
        assert updated_user.is_moderator is True
    
    def test_update_role_user_not_found(self):
        """测试更新不存在用户的角色"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        service.get_user_by_id = Mock(return_value=None)
        
        updated_user = service.update_role("nonexistent-id", is_admin=True)
        
        assert updated_user is None
    
    @patch('app.services.user_service.verify_password')
    @patch('app.services.user_service.get_password_hash')
    def test_promote_to_admin_success(self, mock_hash, mock_verify):
        """测试使用正确密码提升用户为管理员"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.is_admin = False
        
        service.get_user_by_id = Mock(return_value=user)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = True
        
        db.commit = Mock()
        
        with patch.dict(os.environ, {'HIGHEST_PASSWORD': 'correct_password'}):
            result = service.promote_to_admin("user-123", "correct_password")
        
        assert result is True
        assert user.is_admin is True
        assert db.commit.called

    @patch('app.services.user_service.verify_password')
    @patch('app.services.user_service.get_password_hash')
    def test_promote_to_admin_wrong_password(self, mock_hash, mock_verify):
        """测试使用错误密码提升管理员失败"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.is_admin = False
        
        service.get_user_by_id = Mock(return_value=user)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = False
        
        result = service.promote_to_admin("user-123", "wrong_password")
        
        assert result is False
        assert user.is_admin is False
    
    @patch('app.services.user_service.verify_password')
    @patch('app.services.user_service.get_password_hash')
    def test_promote_to_moderator_success(self, mock_hash, mock_verify):
        """测试使用正确密码提升用户为审核员"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.is_moderator = False
        
        service.get_user_by_id = Mock(return_value=user)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = True
        
        db.commit = Mock()
        
        with patch.dict(os.environ, {'HIGHEST_PASSWORD': 'correct_password'}):
            result = service.promote_to_moderator("user-123", "correct_password")
        
        assert result is True
        assert user.is_moderator is True
        assert db.commit.called


class TestCredentialVerification:
    """测试凭证验证逻辑"""
    
    @patch('app.services.user_service.verify_password')
    def test_verify_credentials_success(self, mock_verify):
        """测试成功验证凭证"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.hashed_password = "hashed_password"
        
        service.get_user_by_username = Mock(return_value=user)
        service.reset_failed_login = Mock()
        mock_verify.return_value = True
        
        result = service.verify_credentials("testuser", "correct_password")
        
        assert result == user
        service.reset_failed_login.assert_called_once_with(user.id)

    @patch('time.sleep')
    @patch('app.services.user_service.verify_password')
    def test_verify_credentials_wrong_password(self, mock_verify, mock_sleep):
        """测试使用错误密码验证凭证"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.hashed_password = "hashed_password"
        
        service.get_user_by_username = Mock(return_value=user)
        service.increment_failed_login = Mock()
        mock_verify.return_value = False
        
        result = service.verify_credentials("testuser", "wrong_password")
        
        assert result is None
        service.increment_failed_login.assert_called_once_with(user.id)
        mock_sleep.assert_called_once_with(0.1)
    
    @patch('time.sleep')
    @patch('app.services.user_service.verify_password')
    def test_verify_credentials_user_not_found(self, mock_verify, mock_sleep):
        """测试验证不存在用户的凭证（时序攻击防护）"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        service.get_user_by_username = Mock(return_value=None)
        
        result = service.verify_credentials("nonexistent", "password")
        
        assert result is None
        # Verify dummy hash was used (timing attack protection)
        assert mock_verify.called
        mock_sleep.assert_called_once_with(0.1)


class TestAccountLocking:
    """测试账户锁定逻辑"""
    
    def test_check_account_lock_not_locked(self):
        """测试检查未锁定的账户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.locked_until = None
        
        service.get_user_by_id = Mock(return_value=user)
        
        result = service.check_account_lock("user-123")
        
        assert result is True

    def test_check_account_lock_locked(self):
        """测试检查已锁定的账户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.locked_until = datetime.now() + timedelta(minutes=30)
        
        service.get_user_by_id = Mock(return_value=user)
        
        result = service.check_account_lock("user-123")
        
        assert result is False
    
    def test_check_account_lock_expired(self):
        """测试检查锁定已过期的账户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.locked_until = datetime.now() - timedelta(minutes=1)
        
        service.get_user_by_id = Mock(return_value=user)
        
        result = service.check_account_lock("user-123")
        
        assert result is True
    
    def test_increment_failed_login(self):
        """测试递增失败登录次数"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.failed_login_attempts = 2
        user.last_failed_login = None
        user.locked_until = None
        
        service.get_user_by_id = Mock(return_value=user)
        
        db.commit = Mock()
        
        service.increment_failed_login("user-123")
        
        assert user.failed_login_attempts == 3
        assert user.last_failed_login is not None
        assert db.commit.called
    
    def test_increment_failed_login_locks_account(self):
        """测试 5 次失败后锁定账户"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.failed_login_attempts = 4
        user.locked_until = None
        
        service.get_user_by_id = Mock(return_value=user)
        
        db.commit = Mock()
        
        service.increment_failed_login("user-123")
        
        assert user.failed_login_attempts == 5
        assert user.locked_until is not None
        assert user.locked_until > datetime.now()

    def test_reset_failed_login(self):
        """测试重置失败登录次数"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.failed_login_attempts = 3
        user.locked_until = datetime.now() + timedelta(minutes=30)
        
        service.get_user_by_id = Mock(return_value=user)
        
        db.commit = Mock()
        
        service.reset_failed_login("user-123")
        
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        assert db.commit.called
    
    def test_reset_failed_login_already_zero(self):
        """测试重置已为零的失败登录次数（不提交）"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        user = Mock(spec=User)
        user.id = "user-123"
        user.failed_login_attempts = 0
        user.locked_until = None
        
        service.get_user_by_id = Mock(return_value=user)
        
        db.commit = Mock()
        
        service.reset_failed_login("user-123")
        
        # Should not commit if already zero
        assert not db.commit.called


class TestSuperAdminManagement:
    """测试超级管理员管理逻辑"""
    
    @patch('app.services.user_service.get_password_hash')
    @patch('app.services.user_service.uuid.uuid4')
    def test_ensure_super_admin_exists_creates_admin(self, mock_uuid, mock_hash):
        """测试不存在时创建超级管理员"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        mock_uuid.return_value = Mock(hex="super-admin-uuid")
        mock_hash.return_value = "hashed_password"
        
        # Mock query to return None (no super admin exists)
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        db.add = Mock()
        db.commit = Mock()
        
        with patch.dict(os.environ, {
            'SUPERADMIN_USERNAME': 'superadmin',
            'SUPERADMIN_PWD': 'admin123',
            'EXTERNAL_DOMAIN': 'example.com'
        }):
            service.ensure_super_admin_exists()
        
        assert db.add.called
        assert db.commit.called

    def test_ensure_super_admin_exists_already_exists(self):
        """测试已存在时不创建超级管理员"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        existing_admin = Mock(spec=User)
        existing_admin.is_super_admin = True
        
        # Mock query to return existing super admin
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=existing_admin)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        db.add = Mock()
        db.commit = Mock()
        
        service.ensure_super_admin_exists()
        
        # Should not add or commit if super admin already exists
        assert not db.add.called
        assert not db.commit.called


class TestUploadRecords:
    """测试上传记录检索逻辑"""
    
    def test_get_upload_records_by_uploader(self):
        """测试按上传者获取上传记录"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_offset = Mock()
        mock_limit = Mock()
        
        expected_records = [Mock(), Mock()]
        mock_limit.all = Mock(return_value=expected_records)
        mock_offset.limit = Mock(return_value=mock_limit)
        mock_order.offset = Mock(return_value=mock_offset)
        mock_filter.order_by = Mock(return_value=mock_order)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        records = service.get_upload_records_by_uploader("user-123", page=1, page_size=20)
        
        assert records == expected_records
    
    def test_get_upload_records_with_status_filter(self):
        """测试使用状态过滤获取上传记录"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        # Mock query chain - filter is called twice, so we need to handle that
        mock_query = Mock()
        mock_filter1 = Mock()
        mock_filter2 = Mock()
        mock_order = Mock()
        mock_offset = Mock()
        mock_limit = Mock()
        
        expected_records = [Mock()]
        mock_limit.all = Mock(return_value=expected_records)
        mock_offset.limit = Mock(return_value=mock_limit)
        mock_order.offset = Mock(return_value=mock_offset)
        mock_filter2.order_by = Mock(return_value=mock_order)
        mock_filter1.filter = Mock(return_value=mock_filter2)
        mock_query.filter = Mock(return_value=mock_filter1)
        db.query = Mock(return_value=mock_query)
        
        records = service.get_upload_records_by_uploader(
            "user-123",
            page=1,
            page_size=20,
            status="approved"
        )
        
        assert records == expected_records

    def test_get_upload_records_count_by_uploader(self):
        """Test getting upload records count"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.count = Mock(return_value=10)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        count = service.get_upload_records_count_by_uploader("user-123")
        
        assert count == 10
    
    def test_get_upload_records_count_with_status(self):
        """Test getting upload records count with status filter"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        # Mock query chain - filter is called twice for status filter
        mock_query = Mock()
        mock_filter1 = Mock()
        mock_filter2 = Mock()
        mock_filter2.count = Mock(return_value=5)
        mock_filter1.filter = Mock(return_value=mock_filter2)
        mock_query.filter = Mock(return_value=mock_filter1)
        db.query = Mock(return_value=mock_query)
        
        count = service.get_upload_records_count_by_uploader("user-123", status="pending")
        
        assert count == 5


class TestResourceRetrieval:
    """Test knowledge base and persona card retrieval"""
    
    def test_get_knowledge_base_by_id(self):
        """Test getting knowledge base by ID"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        expected_kb = Mock()
        expected_kb.id = "kb-123"
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=expected_kb)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        kb = service.get_knowledge_base_by_id("kb-123")
        
        assert kb == expected_kb
    
    def test_get_persona_card_by_id(self):
        """Test getting persona card by ID"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        expected_pc = Mock()
        expected_pc.id = "pc-123"
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=expected_pc)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        pc = service.get_persona_card_by_id("pc-123")
        
        assert pc == expected_pc

    def test_get_total_file_size_knowledge_base(self):
        """Test getting total file size for knowledge base"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        # Mock files with sizes
        file1 = Mock()
        file1.file_size = 1024
        file2 = Mock()
        file2.file_size = 2048
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[file1, file2])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        total_size = service.get_total_file_size_by_target("kb-123", "knowledge")
        
        assert total_size == 3072
    
    def test_get_total_file_size_persona_card(self):
        """Test getting total file size for persona card"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        # Mock files with sizes
        file1 = Mock()
        file1.file_size = 512
        file2 = Mock()
        file2.file_size = 1024
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[file1, file2])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        total_size = service.get_total_file_size_by_target("pc-123", "persona")
        
        assert total_size == 1536
    
    def test_get_total_file_size_invalid_type(self):
        """Test getting total file size with invalid target type"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        total_size = service.get_total_file_size_by_target("target-123", "invalid")
        
        assert total_size == 0
    
    def test_get_total_file_size_no_files(self):
        """Test getting total file size when no files exist"""
        db = Mock(spec=Session)
        service = UserService(db)
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        
        total_size = service.get_total_file_size_by_target("kb-123", "knowledge")
        
        assert total_size == 0



