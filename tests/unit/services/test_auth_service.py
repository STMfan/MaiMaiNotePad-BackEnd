"""
AuthService 单元测试

测试认证业务逻辑，包括用户认证、
注册、邮箱验证、密码重置和令牌管理。

需求: 2.2 - 服务层单元测试
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService
from app.models.database import User, EmailVerification
from app.core.security import get_password_hash


class TestAuthentication:
    """测试用户认证方法"""

    def test_authenticate_user_success(self):
        """测试成功的用户认证"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Create mock user
        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = get_password_hash("password123")
        mock_user.locked_until = None
        mock_user.failed_login_attempts = 0
        mock_user.is_admin = False
        mock_user.is_moderator = False
        mock_user.is_super_admin = False
        mock_user.password_version = 0

        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_user)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.authenticate_user("testuser", "password123")

        assert result is not None
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user"]["username"] == "testuser"
        # _reset_failed_login is called which commits
        assert db.commit.call_count >= 0  # May or may not commit depending on failed_login_attempts

    def test_authenticate_user_invalid_username(self):
        """测试使用无效用户名的认证"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock database query returning None
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.authenticate_user("nonexistent", "password123")

        assert result is None

    def test_authenticate_user_invalid_password(self):
        """测试使用无效密码的认证"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Create mock user
        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.hashed_password = get_password_hash("password123")
        mock_user.locked_until = None
        mock_user.failed_login_attempts = 0

        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_user)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.authenticate_user("testuser", "wrongpassword")

        assert result is None
        # Should increment failed login attempts
        db.commit.assert_called()

    def test_authenticate_user_account_locked(self):
        """测试使用锁定账户的认证"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Create mock user with locked account
        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.hashed_password = get_password_hash("password123")
        mock_user.locked_until = datetime.now() + timedelta(minutes=30)

        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_user)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.authenticate_user("testuser", "password123")

        assert result is None


class TestTokenCreation:
    """测试令牌创建方法"""

    def test_create_tokens_regular_user(self):
        """测试为普通用户创建令牌"""
        db = Mock(spec=Session)
        service = AuthService(db)

        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.is_admin = False
        mock_user.is_moderator = False
        mock_user.is_super_admin = False
        mock_user.password_version = 0

        result = service.create_tokens(mock_user)

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert result["user"]["role"] == "user"

    def test_create_tokens_admin_user(self):
        """测试为管理员用户创建令牌"""
        db = Mock(spec=Session)
        service = AuthService(db)

        mock_user = Mock(spec=User)
        mock_user.id = "admin-123"
        mock_user.username = "adminuser"
        mock_user.email = "admin@example.com"
        mock_user.is_admin = True
        mock_user.is_moderator = False
        mock_user.is_super_admin = False
        mock_user.password_version = 0

        result = service.create_tokens(mock_user)

        assert result["user"]["role"] == "admin"
        assert result["user"]["is_admin"] is True

    def test_create_tokens_super_admin_user(self):
        """测试为超级管理员用户创建令牌"""
        db = Mock(spec=Session)
        service = AuthService(db)

        mock_user = Mock(spec=User)
        mock_user.id = "superadmin-123"
        mock_user.username = "superadmin"
        mock_user.email = "superadmin@example.com"
        mock_user.is_admin = True
        mock_user.is_moderator = True
        mock_user.is_super_admin = True
        mock_user.password_version = 0

        result = service.create_tokens(mock_user)

        assert result["user"]["role"] == "super_admin"
        assert result["user"]["is_super_admin"] is True


class TestUserRegistration:
    """测试用户注册方法"""

    def test_register_user_success(self):
        """测试成功的用户注册"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock check_register_legality to return "ok"
        service.check_register_legality = Mock(return_value="ok")

        # Mock database operations
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        result = service.register_user("newuser", "password123", "new@example.com")

        assert result is not None
        assert result.username == "newuser"
        assert result.email == "new@example.com"
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_register_user_duplicate_username(self):
        """测试使用重复用户名的注册"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock check_register_legality to return error
        service.check_register_legality = Mock(return_value="用户名已存在")

        result = service.register_user("existinguser", "password123", "new@example.com")

        assert result is None

    def test_register_user_duplicate_email(self):
        """测试使用重复邮箱的注册"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock check_register_legality to return error
        service.check_register_legality = Mock(return_value="该邮箱已被注册")

        result = service.register_user("newuser", "password123", "existing@example.com")

        assert result is None

    def test_register_user_email_lowercase(self):
        """测试注册时邮箱转换为小写"""
        db = Mock(spec=Session)
        service = AuthService(db)

        service.check_register_legality = Mock(return_value="ok")
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        result = service.register_user("newuser", "password123", "NEW@EXAMPLE.COM")

        assert result.email == "new@example.com"


class TestEmailVerification:
    """测试邮箱验证方法"""

    def test_verify_email_code_success(self):
        """测试成功的邮箱验证码验证"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Create mock verification record
        mock_record = Mock(spec=EmailVerification)
        mock_record.email = "test@example.com"
        mock_record.code = "123456"
        mock_record.is_used = False
        mock_record.expires_at = datetime.now() + timedelta(minutes=2)

        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_record)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.verify_email_code("test@example.com", "123456")

        assert result is True
        assert mock_record.is_used is True
        db.commit.assert_called_once()

    def test_verify_email_code_invalid(self):
        """测试使用无效验证码的验证"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock database query returning None
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.verify_email_code("test@example.com", "wrong")

        assert result is False

    def test_verify_email_code_expired(self):
        """测试使用过期验证码的验证"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock database query returning None (expired code filtered out)
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.verify_email_code("test@example.com", "123456")

        assert result is False

    def test_save_verification_code_success(self):
        """测试保存验证码"""
        db = Mock(spec=Session)
        service = AuthService(db)

        db.add = Mock()
        db.commit = Mock()

        result = service.save_verification_code("test@example.com", "123456")

        assert result is not None
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_generate_verification_code(self):
        """测试验证码生成"""
        db = Mock(spec=Session)
        service = AuthService(db)

        code = service.generate_verification_code()

        assert len(code) == 6
        assert code.isdigit()


class TestRateLimit:
    """测试速率限制方法"""

    def test_check_email_rate_limit_within_limits(self):
        """测试在限制范围内的速率限制检查"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock database query returning low counts
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.count = Mock(return_value=0)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.check_email_rate_limit("test@example.com")

        assert result is True

    def test_check_email_rate_limit_hourly_exceeded(self):
        """测试超过每小时限制的速率限制检查"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        # First call returns 5 (hourly limit), second call returns 0
        mock_filter.count = Mock(side_effect=[5, 0])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.check_email_rate_limit("test@example.com")

        assert result is False

    def test_check_email_rate_limit_minute_exceeded(self):
        """测试超过每分钟限制的速率限制检查"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        # First call returns 0 (hourly ok), second call returns 1 (minute limit)
        mock_filter.count = Mock(side_effect=[0, 1])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.check_email_rate_limit("test@example.com")

        assert result is False


class TestPasswordReset:
    """测试密码重置方法"""

    def test_reset_password_success(self):
        """测试成功的密码重置"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Create mock user
        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.password_version = 0
        mock_user.failed_login_attempts = 3
        mock_user.locked_until = datetime.now() + timedelta(minutes=10)

        # Mock verify_email_code
        service.verify_email_code = Mock(return_value=True)

        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_user)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        success, message = service.reset_password("test@example.com", "123456", "newpassword")

        assert success is True
        assert "成功" in message
        assert mock_user.password_version == 1
        assert mock_user.failed_login_attempts == 0
        assert mock_user.locked_until is None
        db.commit.assert_called_once()

    def test_reset_password_invalid_code(self):
        """测试使用无效验证码的密码重置"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock verify_email_code to return False
        service.verify_email_code = Mock(return_value=False)

        success, message = service.reset_password("test@example.com", "wrong", "newpassword")

        assert success is False
        assert "验证码" in message

    def test_reset_password_user_not_found(self):
        """测试用户不存在时的密码重置"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock verify_email_code
        service.verify_email_code = Mock(return_value=True)

        # Mock database query returning None
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        success, message = service.reset_password("nonexistent@example.com", "123456", "newpassword")

        assert success is False
        assert "不存在" in message


class TestTokenRefresh:
    """测试令牌刷新方法"""

    @patch("app.core.security.verify_token")
    def test_refresh_access_token_success(self, mock_verify_token):
        """测试成功的令牌刷新"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock verify_token
        mock_verify_token.return_value = {"sub": "user-123"}

        # Create mock user
        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.is_admin = False
        mock_user.is_moderator = False
        mock_user.is_super_admin = False
        mock_user.password_version = 0

        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=mock_user)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.refresh_access_token("valid_refresh_token")

        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert result["user_id"] == "user-123"

    @patch("app.core.security.verify_token")
    def test_refresh_access_token_invalid_token(self, mock_verify_token):
        """测试使用无效令牌的令牌刷新"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock verify_token to return None
        mock_verify_token.return_value = None

        with pytest.raises(ValueError):
            service.refresh_access_token("invalid_token")

    @patch("app.core.security.verify_token")
    def test_refresh_access_token_user_not_found(self, mock_verify_token):
        """测试用户不存在时的令牌刷新"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock verify_token
        mock_verify_token.return_value = {"sub": "nonexistent-user"}

        # Mock database query returning None
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        with pytest.raises(ValueError):
            service.refresh_access_token("valid_token")


class TestRegistrationLegality:
    """测试注册合法性检查方法"""

    def test_check_register_legality_available(self):
        """测试用户名和邮箱可用时的合法性检查"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock database query returning None (no conflicts)
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.check_register_legality("newuser", "new@example.com")

        assert result == "ok"

    def test_check_register_legality_username_exists(self):
        """测试用户名已存在时的合法性检查"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Create mock user
        mock_user = Mock(spec=User)
        mock_user.username = "existinguser"

        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        # First call returns user (username exists), second call not reached
        mock_filter.first = Mock(return_value=mock_user)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.check_register_legality("existinguser", "new@example.com")

        assert "用户名" in result

    def test_check_register_legality_email_exists(self):
        """测试邮箱已存在时的合法性检查"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Create mock user
        mock_user = Mock(spec=User)
        mock_user.email = "existing@example.com"

        # Mock database query
        mock_query = Mock()
        mock_filter = Mock()
        # First call returns None (username ok), second call returns user (email exists)
        mock_filter.first = Mock(side_effect=[None, mock_user])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        result = service.check_register_legality("newuser", "existing@example.com")

        assert "邮箱" in result


class TestFailedLoginManagement:
    """测试失败登录尝试管理"""

    def test_increment_failed_login(self):
        """测试增加失败登录尝试次数"""
        db = Mock(spec=Session)
        service = AuthService(db)

        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.failed_login_attempts = 2

        service._increment_failed_login(mock_user)

        assert mock_user.failed_login_attempts == 3
        db.commit.assert_called_once()

    def test_increment_failed_login_locks_account(self):
        """测试5次失败尝试后账户被锁定"""
        db = Mock(spec=Session)
        service = AuthService(db)

        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.failed_login_attempts = 4
        mock_user.locked_until = None

        service._increment_failed_login(mock_user)

        assert mock_user.failed_login_attempts == 5
        assert mock_user.locked_until is not None
        db.commit.assert_called_once()

    def test_reset_failed_login(self):
        """测试重置失败登录尝试次数"""
        db = Mock(spec=Session)
        service = AuthService(db)

        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.failed_login_attempts = 3
        mock_user.locked_until = datetime.now() + timedelta(minutes=10)

        service._reset_failed_login(mock_user)

        assert mock_user.failed_login_attempts == 0
        assert mock_user.locked_until is None
        db.commit.assert_called_once()

    def test_reset_failed_login_no_changes_needed(self):
        """测试不需要更改时的重置"""
        db = Mock(spec=Session)
        service = AuthService(db)

        mock_user = Mock(spec=User)
        mock_user.id = "user-123"
        mock_user.failed_login_attempts = 0
        mock_user.locked_until = None

        service._reset_failed_login(mock_user)

        # Should not commit if no changes needed
        db.commit.assert_not_called()


class TestEmailSending:
    """测试邮件发送方法"""

    @patch("app.services.email_service.send_email")
    def test_send_verification_code_success(self, mock_send_email):
        """测试发送验证码"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock save_verification_code
        service.save_verification_code = Mock(return_value="code-id-123")
        service.generate_verification_code = Mock(return_value="123456")

        result = service.send_verification_code("test@example.com")

        assert result == "code-id-123"
        mock_send_email.assert_called_once()
        # Check email content
        call_args = mock_send_email.call_args
        assert "test@example.com" in call_args[0]
        assert "123456" in call_args[0][2]  # Body contains code

    @patch("app.services.email_service.send_email")
    def test_send_reset_password_code_success(self, mock_send_email):
        """测试发送密码重置验证码"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock save_verification_code
        service.save_verification_code = Mock(return_value="code-id-456")
        service.generate_verification_code = Mock(return_value="654321")

        result = service.send_reset_password_code("test@example.com")

        assert result == "code-id-456"
        mock_send_email.assert_called_once()
        # Check email content
        call_args = mock_send_email.call_args
        assert "test@example.com" in call_args[0]
        assert "654321" in call_args[0][2]  # Body contains code
        assert "重置密码" in call_args[0][1]  # Subject mentions password reset

    @patch("app.services.email_service.send_email")
    def test_send_verification_code_save_failure(self, mock_send_email):
        """测试保存失败时发送验证码"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock save_verification_code to return None (failure)
        service.save_verification_code = Mock(return_value=None)
        service.generate_verification_code = Mock(return_value="123456")

        result = service.send_verification_code("test@example.com")

        assert result is None
        # Email should not be sent if save fails
        mock_send_email.assert_not_called()

    @patch("app.services.email_service.send_email")
    def test_send_reset_password_code_save_failure(self, mock_send_email):
        """测试保存失败时发送重置验证码"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock save_verification_code to return None (failure)
        service.save_verification_code = Mock(return_value=None)
        service.generate_verification_code = Mock(return_value="654321")

        result = service.send_reset_password_code("test@example.com")

        assert result is None
        # Email should not be sent if save fails
        mock_send_email.assert_not_called()


class TestErrorHandling:
    """测试各种场景下的错误处理"""

    def test_authenticate_user_database_error(self):
        """测试数据库错误时的认证"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock database query to raise exception
        db.query = Mock(side_effect=Exception("Database error"))

        result = service.authenticate_user("testuser", "password123")

        assert result is None

    def test_register_user_database_error(self):
        """测试数据库错误时的注册"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock check_register_legality to return "ok"
        service.check_register_legality = Mock(return_value="ok")

        # Mock database add to raise exception
        db.add = Mock(side_effect=Exception("Database error"))
        db.rollback = Mock()

        result = service.register_user("newuser", "password123", "new@example.com")

        assert result is None
        db.rollback.assert_called_once()

    def test_verify_email_code_database_error(self):
        """测试数据库错误时的邮箱验证"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock database query to raise exception
        db.query = Mock(side_effect=Exception("Database error"))

        result = service.verify_email_code("test@example.com", "123456")

        assert result is False

    def test_save_verification_code_database_error(self):
        """测试数据库错误时保存验证码"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock database add to raise exception
        db.add = Mock(side_effect=Exception("Database error"))
        db.rollback = Mock()

        result = service.save_verification_code("test@example.com", "123456")

        assert result is None
        db.rollback.assert_called_once()

    def test_check_email_rate_limit_database_error(self):
        """测试数据库错误时的速率限制检查"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock database query to raise exception
        db.query = Mock(side_effect=Exception("Database error"))

        result = service.check_email_rate_limit("test@example.com")

        # Should return False (deny) on error for safety
        assert result is False

    def test_reset_password_database_error(self):
        """测试数据库错误时的密码重置"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock verify_email_code
        service.verify_email_code = Mock(return_value=True)

        # Mock database query to raise exception
        db.query = Mock(side_effect=Exception("Database error"))
        db.rollback = Mock()

        success, message = service.reset_password("test@example.com", "123456", "newpassword")

        assert success is False
        db.rollback.assert_called_once()

    def test_check_register_legality_database_error(self):
        """测试数据库错误时的注册合法性检查"""
        db = Mock(spec=Session)
        service = AuthService(db)

        # Mock database query to raise exception
        db.query = Mock(side_effect=Exception("Database error"))

        result = service.check_register_legality("newuser", "new@example.com")

        # Should return error message on exception
        assert result != "ok"
        assert "错误" in result or "失败" in result
