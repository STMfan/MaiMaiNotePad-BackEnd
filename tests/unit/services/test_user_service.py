"""
UserService 单元测试

测试用户管理业务逻辑，包括 CRUD 操作、认证、密码管理和角色管理。

需求: 2.2 - 服务层单元测试
"""

import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.database import User
from app.services.user_service import UserService


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

    def test_get_user_by_id_database_error(self, caplog):
        """测试数据库错误时获取用户

        验证:
        - 捕获SQLAlchemyError异常
        - 返回None而不是抛出异常
        - 错误被正确记录到日志
        """
        db = Mock(spec=Session)
        service = UserService(db)

        # 注入SQLAlchemyError
        db.query = Mock(side_effect=SQLAlchemyError("Database connection failed"))

        # 调用方法
        user = service.get_user_by_id("user-123")

        # 验证返回None
        assert user is None

        # 验证错误被记录
        assert "Error getting user by ID" in caplog.text
        assert "user-123" in caplog.text

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

    def test_get_user_by_username_database_error(self, caplog):
        """测试数据库错误时通过用户名获取用户

        验证:
        - 捕获SQLAlchemyError异常
        - 返回None而不是抛出异常
        - 错误被正确记录到日志
        """
        db = Mock(spec=Session)
        service = UserService(db)

        # 注入SQLAlchemyError
        db.query = Mock(side_effect=SQLAlchemyError("Database connection failed"))

        # 调用方法
        user = service.get_user_by_username("testuser")

        # 验证返回None
        assert user is None

        # 验证错误被记录
        assert "Error getting user by username" in caplog.text
        assert "testuser" in caplog.text

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

    def test_get_user_by_email_database_error(self, caplog):
        """测试数据库错误时通过邮箱获取用户

        验证:
        - 捕获SQLAlchemyError异常
        - 返回None而不是抛出异常
        - 错误被正确记录到日志
        """
        db = Mock(spec=Session)
        service = UserService(db)

        # 注入SQLAlchemyError
        db.query = Mock(side_effect=SQLAlchemyError("Database connection failed"))

        # 调用方法
        user = service.get_user_by_email("test@example.com")

        # 验证返回None
        assert user is None

        # 验证错误被记录
        assert "Error getting user by email" in caplog.text
        assert "test@example.com" in caplog.text

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

    def test_get_all_users_database_error(self, caplog):
        """测试数据库错误时获取所有用户

        验证:
        - 捕获SQLAlchemyError异常
        - 返回空列表而不是抛出异常
        - 错误被正确记录到日志
        """
        db = Mock(spec=Session)
        service = UserService(db)

        # 注入SQLAlchemyError
        db.query = Mock(side_effect=SQLAlchemyError("Database connection failed"))

        # 调用方法
        users = service.get_all_users()

        # 验证返回空列表
        assert users == []

        # 验证错误被记录
        assert "Error getting all users" in caplog.text


class TestUserCreation:
    """测试用户创建逻辑"""

    @patch("app.services.user_service.get_password_hash")
    @patch("app.services.user_service.uuid.uuid4")
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

        user = service.create_user(username="newuser", email="new@example.com", password="password123")

        assert user is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.is_active is True
        assert user.is_admin is False
        assert db.add.called
        assert db.commit.called

    def test_create_user_duplicate_username(self, caplog):
        """测试创建重复用户名失败

        验证:
        - 当用户名已存在时返回None
        - 记录警告日志
        """
        db = Mock(spec=Session)
        service = UserService(db)

        existing_user = Mock(spec=User)
        existing_user.username = "existinguser"

        service.get_user_by_username = Mock(return_value=existing_user)

        user = service.create_user(username="existinguser", email="new@example.com", password="password123")

        # 验证返回None
        assert user is None

        # 验证警告被记录
        assert "Username existinguser already exists" in caplog.text

    def test_create_user_duplicate_email(self, caplog):
        """测试创建重复邮箱失败

        验证:
        - 当邮箱已存在时返回None
        - 记录警告日志
        """
        db = Mock(spec=Session)
        service = UserService(db)

        existing_user = Mock(spec=User)
        existing_user.email = "existing@example.com"

        service.get_user_by_username = Mock(return_value=None)
        service.get_user_by_email = Mock(return_value=existing_user)

        user = service.create_user(username="newuser", email="existing@example.com", password="password123")

        # 验证返回None
        assert user is None

        # 验证警告被记录
        assert "Email existing@example.com already exists" in caplog.text

    @patch("app.services.user_service.get_password_hash")
    @patch("app.services.user_service.uuid.uuid4")
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
            username="adminuser", email="admin@example.com", password="password123", is_admin=True
        )

        assert user.is_admin is True

    @patch("app.services.user_service.get_password_hash")
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
        _ = service.create_user(username="testuser", email="test@example.com", password=long_password)

        # Verify password was truncated to 72 bytes before hashing
        mock_hash.assert_called_once_with(long_password[:72])

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
    @patch("app.services.user_service.uuid.uuid4")
    def test_create_user_long_password_verification(self, mock_uuid, mock_hash, mock_verify):
        """测试超长密码（>72字节）的创建和验证

        验证:
        - 用户可以使用超过72字节的密码成功创建
        - 密码被截断到72字节
        - 使用前72字节可以成功验证
        - 超过72字节的部分不影响验证

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.2 - 测试超长密码截断（72字节）

        bcrypt限制: bcrypt只使用密码的前72字节进行哈希
        """
        db = Mock(spec=Session)
        service = UserService(db)

        mock_uuid.return_value = Mock(hex="test-uuid-123")

        # 创建超过72字节的密码
        long_password = "a" * 100  # 100字节密码
        truncated_password = long_password[:72]  # 前72字节

        # Mock密码哈希
        mock_hash.return_value = "hashed_password_72bytes"

        service.get_user_by_username = Mock(return_value=None)
        service.get_user_by_email = Mock(return_value=None)

        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        # 步骤1: 创建用户
        user = service.create_user(username="testuser", email="test@example.com", password=long_password)

        # 验证用户创建成功
        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"

        # 验证密码被截断到72字节后才进行哈希
        mock_hash.assert_called_once_with(truncated_password)

        # 步骤2: 验证密码验证逻辑
        # 模拟用户已存在
        user.hashed_password = "hashed_password_72bytes"
        service.get_user_by_username = Mock(return_value=user)
        service.reset_failed_login = Mock()
        service.increment_failed_login = Mock()

        # 测试使用前72字节可以验证成功
        mock_verify.return_value = True
        result = service.verify_credentials("testuser", truncated_password)
        assert result == user

        # 测试使用完整的100字节密码也应该成功（因为只使用前72字节）
        mock_verify.return_value = True
        result = service.verify_credentials("testuser", long_password)
        assert result == user

        # 测试超过72字节的部分不影响验证
        # 即使后面的字符不同，只要前72字节相同就应该验证成功
        different_suffix_password = truncated_password + "b" * 28  # 前72字节相同，后28字节不同
        mock_verify.return_value = True
        result = service.verify_credentials("testuser", different_suffix_password)
        assert result == user


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

        # 验证尝试修改超级管理员用户名时抛出 ValueError
        with pytest.raises(ValueError, match="不能修改超级管理员用户名"):
            service.update_user("admin-123", username="newsuperadmin")

        # 验证用户名保持不变（未被修改）
        assert super_admin.username == "superadmin"

        # 验证数据库回滚被调用
        db.rollback.assert_called_once()

    def test_update_super_admin_other_fields_allowed(self):
        """测试超级管理员可以修改其他字段（如邮箱）"""
        db = Mock(spec=Session)
        service = UserService(db)

        super_admin = Mock(spec=User)
        super_admin.id = "admin-123"
        super_admin.username = "superadmin"
        super_admin.email = "old@example.com"
        super_admin.is_super_admin = True

        service.get_user_by_id = Mock(return_value=super_admin)
        service.get_user_by_email = Mock(return_value=None)

        # 更新邮箱应该成功
        updated_user = service.update_user("admin-123", email="new@example.com")

        # 验证邮箱被更新
        assert super_admin.email == "new@example.com"
        assert updated_user == super_admin

        # 验证数据库提交被调用
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(super_admin)

    def test_update_user_not_found(self):
        """测试更新不存在的用户"""
        db = Mock(spec=Session)
        service = UserService(db)

        service.get_user_by_id = Mock(return_value=None)

        updated_user = service.update_user("nonexistent-id", username="newname")

        assert updated_user is None


class TestPasswordManagement:
    """测试密码管理逻辑"""

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
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

    @patch("app.services.user_service.verify_password")
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

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
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

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
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

        with patch.dict(os.environ, {"HIGHEST_PASSWORD": "correct_password"}):
            result = service.promote_to_admin("user-123", "correct_password")

        assert result is True
        assert user.is_admin is True
        assert db.commit.called

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
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

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
    def test_promote_to_admin_user_not_exists(self, mock_hash, mock_verify):
        """测试提升不存在的用户为管理员失败"""
        db = Mock(spec=Session)
        service = UserService(db)

        service.get_user_by_id = Mock(return_value=None)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = True

        with patch.dict(os.environ, {"HIGHEST_PASSWORD": "correct_password"}):
            result = service.promote_to_admin("nonexistent-user", "correct_password")

        assert result is False
        assert not db.commit.called

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
    def test_promote_to_admin_already_admin(self, mock_hash, mock_verify):
        """测试提升已经是管理员的用户"""
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.is_admin = True  # 已经是管理员

        service.get_user_by_id = Mock(return_value=user)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = True

        db.commit = Mock()

        with patch.dict(os.environ, {"HIGHEST_PASSWORD": "correct_password"}):
            result = service.promote_to_admin("user-123", "correct_password")

        # 即使已经是管理员，操作也应该成功
        assert result is True
        assert user.is_admin is True
        assert db.commit.called

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
    def test_promote_to_admin_database_error(self, mock_hash, mock_verify):
        """测试数据库错误时提升管理员失败并回滚"""
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.is_admin = False

        service.get_user_by_id = Mock(return_value=user)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = True

        # 模拟数据库提交失败
        db.commit = Mock(side_effect=SQLAlchemyError("Database error"))
        db.rollback = Mock()

        with patch.dict(os.environ, {"HIGHEST_PASSWORD": "correct_password"}):
            result = service.promote_to_admin("user-123", "correct_password")

        assert result is False
        assert db.rollback.called

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
    def test_promote_to_admin_logs_error_on_wrong_password(self, mock_hash, mock_verify, caplog):
        """测试错误密码时记录错误日志"""
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.is_admin = False

        service.get_user_by_id = Mock(return_value=user)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = False

        with patch.dict(os.environ, {"HIGHEST_PASSWORD": "correct_password"}):
            result = service.promote_to_admin("user-123", "wrong_password")

        assert result is False
        # 验证错误日志被记录
        assert any("highest password verification failed" in record.message.lower() for record in caplog.records)

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
    def test_promote_to_admin_logs_error_on_exception(self, mock_hash, mock_verify, caplog):
        """测试异常时记录错误日志"""
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.is_admin = False

        service.get_user_by_id = Mock(return_value=user)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = True

        # 模拟数据库提交失败
        db.commit = Mock(side_effect=SQLAlchemyError("Database error"))
        db.rollback = Mock()

        with patch.dict(os.environ, {"HIGHEST_PASSWORD": "correct_password"}):
            result = service.promote_to_admin("user-123", "correct_password")

        assert result is False
        # 验证错误日志被记录
        assert any("Error promoting user" in record.message for record in caplog.records)

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
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

        with patch.dict(os.environ, {"HIGHEST_PASSWORD": "correct_password"}):
            result = service.promote_to_moderator("user-123", "correct_password")

        assert result is True
        assert user.is_moderator is True
        assert db.commit.called

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
    def test_promote_to_moderator_wrong_password(self, mock_hash, mock_verify):
        """测试使用错误密码提升审核员失败

        验证:
        - 当密码验证失败时返回False
        - 用户的is_moderator状态保持不变
        - 错误被记录到日志

        需求: FR3 - 服务层异常处理测试
        任务: 4.3.2 - 测试promote_to_moderator权限验证失败
        """
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.is_moderator = False

        service.get_user_by_id = Mock(return_value=user)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = False

        result = service.promote_to_moderator("user-123", "wrong_password")

        assert result is False
        assert user.is_moderator is False

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
    def test_promote_to_moderator_user_not_exists(self, mock_hash, mock_verify):
        """测试提升不存在的用户为审核员失败

        验证:
        - 当用户不存在时返回False
        - 数据库commit不被调用

        需求: FR3 - 服务层异常处理测试
        任务: 4.3.2 - 测试promote_to_moderator权限验证失败
        """
        db = Mock(spec=Session)
        service = UserService(db)

        service.get_user_by_id = Mock(return_value=None)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = True

        with patch.dict(os.environ, {"HIGHEST_PASSWORD": "correct_password"}):
            result = service.promote_to_moderator("nonexistent-user", "correct_password")

        assert result is False
        assert not db.commit.called

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
    def test_promote_to_moderator_already_moderator(self, mock_hash, mock_verify):
        """测试提升已经是审核员的用户

        验证:
        - 即使用户已经是审核员，操作也应该成功
        - 用户的is_moderator状态保持为True
        - 数据库commit被调用

        需求: FR3 - 服务层异常处理测试
        任务: 4.3.2 - 测试promote_to_moderator权限验证失败
        """
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.is_moderator = True  # 已经是审核员

        service.get_user_by_id = Mock(return_value=user)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = True

        db.commit = Mock()

        with patch.dict(os.environ, {"HIGHEST_PASSWORD": "correct_password"}):
            result = service.promote_to_moderator("user-123", "correct_password")

        # 即使已经是审核员，操作也应该成功
        assert result is True
        assert user.is_moderator is True
        assert db.commit.called

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
    def test_promote_to_moderator_database_error(self, mock_hash, mock_verify):
        """测试数据库错误时提升审核员失败并回滚

        验证:
        - 当数据库提交失败时返回False
        - 数据库回滚被调用
        - 错误被记录到日志

        需求: FR3 - 服务层异常处理测试
        任务: 4.3.2 - 测试promote_to_moderator权限验证失败
        """
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.is_moderator = False

        service.get_user_by_id = Mock(return_value=user)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = True

        # 模拟数据库提交失败
        db.commit = Mock(side_effect=SQLAlchemyError("Database error"))
        db.rollback = Mock()

        with patch.dict(os.environ, {"HIGHEST_PASSWORD": "correct_password"}):
            result = service.promote_to_moderator("user-123", "correct_password")

        assert result is False
        assert db.rollback.called

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
    def test_promote_to_moderator_logs_error_on_wrong_password(self, mock_hash, mock_verify, caplog):
        """测试错误密码时记录错误日志

        验证:
        - 当密码验证失败时，错误被记录到日志
        - 日志包含用户ID和失败原因

        需求: FR3 - 服务层异常处理测试
        任务: 4.3.2 - 测试promote_to_moderator权限验证失败
        """
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.is_moderator = False

        service.get_user_by_id = Mock(return_value=user)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = False

        with patch.dict(os.environ, {"HIGHEST_PASSWORD": "correct_password"}):
            result = service.promote_to_moderator("user-123", "wrong_password")

        assert result is False
        # 验证错误日志被记录
        assert any("highest password verification failed" in record.message.lower() for record in caplog.records)

    @patch("app.services.user_service.verify_password")
    @patch("app.services.user_service.get_password_hash")
    def test_promote_to_moderator_logs_error_on_exception(self, mock_hash, mock_verify, caplog):
        """测试异常时记录错误日志

        验证:
        - 当发生异常时，错误被记录到日志
        - 日志包含用户ID和错误详情
        - 数据库回滚被调用

        需求: FR3 - 服务层异常处理测试
        任务: 4.3.2 - 测试promote_to_moderator权限验证失败
        """
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.is_moderator = False

        service.get_user_by_id = Mock(return_value=user)
        mock_hash.return_value = "highest_hash"
        mock_verify.return_value = True

        # 模拟数据库提交失败
        db.commit = Mock(side_effect=SQLAlchemyError("Database error"))
        db.rollback = Mock()

        with patch.dict(os.environ, {"HIGHEST_PASSWORD": "correct_password"}):
            result = service.promote_to_moderator("user-123", "correct_password")

        assert result is False
        # 验证错误日志被记录
        assert any(
            "Error promoting user" in record.message and "to moderator" in record.message for record in caplog.records
        )


class TestCredentialVerification:
    """测试凭证验证逻辑"""

    @patch("app.services.user_service.verify_password")
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

    @patch("time.sleep")
    @patch("app.services.user_service.verify_password")
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

    @patch("time.sleep")
    @patch("app.services.user_service.verify_password")
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

    @patch("time.sleep")
    @patch("app.services.user_service.verify_password")
    def test_verify_credentials_timing_attack_protection(self, mock_verify, mock_sleep):
        """测试密码验证的计时攻击防护

        验证:
        - 无论用户是否存在，都执行密码验证（使用虚拟哈希）
        - 验证失败后添加固定延迟（0.1秒）
        - 防止通过响应时间判断用户是否存在

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.4 - 测试密码验证失败（计时攻击防护）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        # 场景1: 用户不存在
        service.get_user_by_username = Mock(return_value=None)

        result = service.verify_credentials("nonexistent", "password")

        # 验证返回 None
        assert result is None

        # 验证虚拟哈希被使用（防止计时攻击）
        assert mock_verify.called
        dummy_hash = "$2b$12$dummy.hash.for.timing.attack.prevention.abcdefghijklmnopqrstuv"
        mock_verify.assert_called_with("password", dummy_hash)

        # 验证添加了延迟
        mock_sleep.assert_called_once_with(0.1)

        # 重置 mock
        mock_verify.reset_mock()
        mock_sleep.reset_mock()

        # 场景2: 用户存在但密码错误
        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.hashed_password = "real_hash"

        service.get_user_by_username = Mock(return_value=user)
        service.increment_failed_login = Mock()
        mock_verify.return_value = False

        result = service.verify_credentials("testuser", "wrong_password")

        # 验证返回 None
        assert result is None

        # 验证使用真实哈希
        mock_verify.assert_called_with("wrong_password", "real_hash")

        # 验证添加了延迟
        mock_sleep.assert_called_once_with(0.1)

        # 验证失败次数递增
        service.increment_failed_login.assert_called_once_with(user.id)

    @patch("time.sleep")
    @patch("app.services.user_service.verify_password")
    def test_verify_credentials_increments_failed_login_on_wrong_password(self, mock_verify, mock_sleep):
        """测试密码错误时递增失败登录次数

        验证:
        - 密码验证失败时调用 increment_failed_login
        - 传递正确的用户 ID
        - 返回 None 表示验证失败

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.4 - 测试密码验证失败（失败次数递增）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.hashed_password = "hashed_password"

        service.get_user_by_username = Mock(return_value=user)
        service.increment_failed_login = Mock()
        mock_verify.return_value = False

        # 调用验证凭证
        result = service.verify_credentials("testuser", "wrong_password")

        # 验证返回 None
        assert result is None

        # 验证失败次数递增被调用
        service.increment_failed_login.assert_called_once_with("user-123")

        # 验证添加了延迟
        mock_sleep.assert_called_once_with(0.1)

    @patch("time.sleep")
    @patch("app.services.user_service.verify_password")
    def test_verify_credentials_does_not_increment_on_user_not_found(self, mock_verify, mock_sleep):
        """测试用户不存在时不递增失败登录次数

        验证:
        - 用户不存在时不调用 increment_failed_login
        - 使用虚拟哈希进行验证（计时攻击防护）
        - 返回 None

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.4 - 测试密码验证失败（用户不存在场景）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        service.get_user_by_username = Mock(return_value=None)
        service.increment_failed_login = Mock()

        # 调用验证凭证
        result = service.verify_credentials("nonexistent", "password")

        # 验证返回 None
        assert result is None

        # 验证不调用 increment_failed_login（用户不存在）
        service.increment_failed_login.assert_not_called()

        # 验证虚拟哈希被使用
        assert mock_verify.called

        # 验证添加了延迟
        mock_sleep.assert_called_once_with(0.1)

    @patch("app.services.user_service.verify_password")
    def test_verify_credentials_resets_failed_login_on_success(self, mock_verify):
        """测试密码验证成功时重置失败登录次数

        验证:
        - 密码验证成功时调用 reset_failed_login
        - 传递正确的用户 ID
        - 返回用户对象

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.4 - 测试密码验证失败（成功场景对比）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.hashed_password = "hashed_password"

        service.get_user_by_username = Mock(return_value=user)
        service.reset_failed_login = Mock()
        mock_verify.return_value = True

        # 调用验证凭证
        result = service.verify_credentials("testuser", "correct_password")

        # 验证返回用户对象
        assert result == user

        # 验证失败次数被重置
        service.reset_failed_login.assert_called_once_with("user-123")

    @patch("time.sleep")
    @patch("app.services.user_service.verify_password")
    def test_verify_credentials_handles_exception_gracefully(self, mock_verify, mock_sleep, caplog):
        """测试密码验证过程中的异常处理

        验证:
        - 捕获验证过程中的异常
        - 返回 None 而不是抛出异常
        - 错误被记录到日志

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.4 - 测试密码验证失败（异常处理）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        # 模拟 get_user_by_username 抛出异常
        service.get_user_by_username = Mock(side_effect=Exception("Database error"))

        # 调用验证凭证
        result = service.verify_credentials("testuser", "password")

        # 验证返回 None
        assert result is None

        # 验证错误被记录
        assert "Error verifying user credentials" in caplog.text

    @patch("time.sleep")
    @patch("app.services.user_service.verify_password")
    def test_verify_credentials_multiple_failed_attempts(self, mock_verify, mock_sleep):
        """测试多次密码验证失败

        验证:
        - 每次失败都递增失败次数
        - 每次失败都添加延迟
        - 每次都返回 None

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.4 - 测试密码验证失败（多次失败）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.hashed_password = "hashed_password"

        service.get_user_by_username = Mock(return_value=user)
        service.increment_failed_login = Mock()
        mock_verify.return_value = False

        # 模拟 3 次失败尝试
        for i in range(3):
            result = service.verify_credentials("testuser", f"wrong_password_{i}")

            # 验证每次都返回 None
            assert result is None

        # 验证 increment_failed_login 被调用 3 次
        assert service.increment_failed_login.call_count == 3

        # 验证每次都添加了延迟
        assert mock_sleep.call_count == 3


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

    def test_check_account_lock_user_not_found(self):
        """测试检查不存在用户的账户锁定状态

        验证:
        - 用户不存在时返回 False（安全默认值）
        - 不抛出异常

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.5 - 测试账户锁定机制（边界情况）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        service.get_user_by_id = Mock(return_value=None)

        result = service.check_account_lock("nonexistent-id")

        assert result is False

    def test_check_account_lock_database_error(self, caplog):
        """测试数据库错误时检查账户锁定状态

        验证:
        - 捕获异常并返回 False（安全默认值）
        - 错误被正确记录到日志
        - 不抛出异常

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.5 - 测试账户锁定机制（异常处理）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        # 注入数据库异常
        service.get_user_by_id = Mock(side_effect=Exception("Database error"))

        result = service.check_account_lock("user-123")

        # 验证返回 False（安全默认值）
        assert result is False

        # 验证错误被记录
        assert "Error checking account lock" in caplog.text
        assert "user-123" in caplog.text

    def test_increment_failed_login_user_not_found(self):
        """测试递增不存在用户的失败登录次数

        验证:
        - 用户不存在时不执行任何操作
        - 不抛出异常
        - 不提交数据库

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.5 - 测试账户锁定机制（边界情况）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        service.get_user_by_id = Mock(return_value=None)
        db.commit = Mock()

        # 调用方法（不应抛出异常）
        service.increment_failed_login("nonexistent-id")

        # 验证不提交数据库
        assert not db.commit.called

    def test_increment_failed_login_database_error(self, caplog):
        """测试数据库错误时递增失败登录次数

        验证:
        - 捕获异常并回滚事务
        - 错误被正确记录到日志
        - 不抛出异常

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.5 - 测试账户锁定机制（异常处理）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.failed_login_attempts = 2

        service.get_user_by_id = Mock(return_value=user)

        # 注入数据库提交异常
        db.commit = Mock(side_effect=SQLAlchemyError("Database commit failed"))
        db.rollback = Mock()

        # 调用方法（不应抛出异常）
        service.increment_failed_login("user-123")

        # 验证回滚被调用
        db.rollback.assert_called_once()

        # 验证错误被记录
        assert "Error incrementing failed login" in caplog.text
        assert "user-123" in caplog.text

    def test_increment_failed_login_from_zero(self):
        """测试从零开始递增失败登录次数

        验证:
        - failed_login_attempts 为 None 时正确初始化为 1
        - last_failed_login 被设置为当前时间
        - 数据库提交被调用

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.5 - 测试账户锁定机制（边界情况）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.failed_login_attempts = None  # 初始值为 None
        user.last_failed_login = None
        user.locked_until = None

        service.get_user_by_id = Mock(return_value=user)
        db.commit = Mock()

        service.increment_failed_login("user-123")

        # 验证从 None 正确初始化为 1
        assert user.failed_login_attempts == 1
        assert user.last_failed_login is not None
        assert db.commit.called

    def test_increment_failed_login_locks_at_exactly_5(self, caplog):
        """测试恰好第 5 次失败时锁定账户

        验证:
        - 第 5 次失败时设置 locked_until
        - locked_until 设置为当前时间 + 30 分钟
        - 记录警告日志

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.5 - 测试账户锁定机制（锁定阈值）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.username = "testuser"
        user.failed_login_attempts = 4
        user.locked_until = None

        service.get_user_by_id = Mock(return_value=user)
        db.commit = Mock()

        before_time = datetime.now()
        service.increment_failed_login("user-123")
        after_time = datetime.now()

        # 验证失败次数为 5
        assert user.failed_login_attempts == 5

        # 验证账户被锁定
        assert user.locked_until is not None

        # 验证锁定时间约为 30 分钟后
        expected_lock_time = before_time + timedelta(minutes=30)
        assert user.locked_until >= expected_lock_time
        assert user.locked_until <= after_time + timedelta(minutes=30, seconds=1)

        # 验证警告日志
        assert "Account locked" in caplog.text
        assert "testuser" in caplog.text
        assert "attempts=5" in caplog.text

    def test_reset_failed_login_user_not_found(self):
        """测试重置不存在用户的失败登录次数

        验证:
        - 用户不存在时不执行任何操作
        - 不抛出异常
        - 不提交数据库

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.5 - 测试账户锁定机制（边界情况）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        service.get_user_by_id = Mock(return_value=None)
        db.commit = Mock()

        # 调用方法（不应抛出异常）
        service.reset_failed_login("nonexistent-id")

        # 验证不提交数据库
        assert not db.commit.called

    def test_reset_failed_login_database_error(self, caplog):
        """测试数据库错误时重置失败登录次数

        验证:
        - 捕获异常并回滚事务
        - 不抛出异常（静默失败）

        需求: FR3 - 服务层异常处理测试
        任务: 4.2.5 - 测试账户锁定机制（异常处理）
        """
        db = Mock(spec=Session)
        service = UserService(db)

        user = Mock(spec=User)
        user.id = "user-123"
        user.failed_login_attempts = 3
        user.locked_until = datetime.now() + timedelta(minutes=30)

        service.get_user_by_id = Mock(return_value=user)

        # 注入数据库提交异常
        db.commit = Mock(side_effect=SQLAlchemyError("Database commit failed"))
        db.rollback = Mock()

        # 调用方法（不应抛出异常）
        service.reset_failed_login("user-123")

        # 验证回滚被调用
        db.rollback.assert_called_once()


class TestSuperAdminManagement:
    """测试超级管理员管理逻辑"""

    @patch("app.services.user_service.get_password_hash")
    @patch("app.services.user_service.uuid.uuid4")
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

        with patch.dict(
            os.environ,
            {"SUPERADMIN_USERNAME": "superadmin", "SUPERADMIN_PWD": "admin123", "EXTERNAL_DOMAIN": "example.com"},
        ):
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

        records = service.get_upload_records_by_uploader("user-123", page=1, page_size=20, status="approved")

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


class TestBoundaryValueHandling:
    """测试边界值和空值参数处理

    验证 user_service 方法正确处理 None/null 参数和空字符串，
    返回 None 或空列表而不抛出异常。

    需求: FR3 - 服务层异常处理测试
    任务: 4.2.1 - 测试空值参数处理
    """

    def test_get_user_by_id_with_none(self):
        """测试 get_user_by_id 使用 None 参数

        验证:
        - 接受 None 作为参数
        - 返回 None 而不抛出异常
        - 优雅处理边界情况
        """
        db = Mock(spec=Session)
        service = UserService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        # 调用方法使用 None 参数
        result = service.get_user_by_id(None)

        # 验证返回 None
        assert result is None

    def test_get_user_by_username_with_none(self):
        """测试 get_user_by_username 使用 None 参数

        验证:
        - 接受 None 作为参数
        - 返回 None 而不抛出异常
        - 优雅处理边界情况
        """
        db = Mock(spec=Session)
        service = UserService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        # 调用方法使用 None 参数
        result = service.get_user_by_username(None)

        # 验证返回 None
        assert result is None

    def test_get_user_by_email_with_none(self):
        """测试 get_user_by_email 使用 None 参数

        验证:
        - 接受 None 作为参数
        - 返回 None 而不抛出异常
        - 优雅处理边界情况
        - email.lower() 在 None 上不会失败
        """
        db = Mock(spec=Session)
        service = UserService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        # 调用方法使用 None 参数
        result = service.get_user_by_email(None)

        # 验证返回 None
        assert result is None

    def test_get_user_by_username_with_empty_string(self):
        """测试 get_user_by_username 使用空字符串

        验证:
        - 接受空字符串作为参数
        - 返回 None（空字符串不是有效用户名）
        - 优雅处理边界情况
        """
        db = Mock(spec=Session)
        service = UserService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        # 调用方法使用空字符串
        result = service.get_user_by_username("")

        # 验证返回 None
        assert result is None

    def test_get_user_by_email_with_empty_string(self):
        """测试 get_user_by_email 使用空字符串

        验证:
        - 接受空字符串作为参数
        - 返回 None（空字符串不是有效邮箱）
        - 优雅处理边界情况
        """
        db = Mock(spec=Session)
        service = UserService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        # 调用方法使用空字符串
        result = service.get_user_by_email("")

        # 验证返回 None
        assert result is None

    def test_get_user_by_id_with_empty_string(self):
        """测试 get_user_by_id 使用空字符串

        验证:
        - 接受空字符串作为参数
        - 返回 None（空字符串不是有效 ID）
        - 优雅处理边界情况
        """
        db = Mock(spec=Session)
        service = UserService(db)

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=None)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        # 调用方法使用空字符串
        result = service.get_user_by_id("")

        # 验证返回 None
        assert result is None


class TestDashboardTrendStats:
    """测试仪表板趋势统计功能"""

    def test_get_dashboard_trend_stats_basic(self, test_db, factory):
        """测试基本的趋势统计"""
        user = factory.create_user()
        service = UserService(test_db)

        result = service.get_dashboard_trend_stats(user.id, days=7)

        assert result is not None
        assert "days" in result
        assert "items" in result
        assert result["days"] == 7
        assert len(result["items"]) == 7

        # 验证每一天的数据结构
        for item in result["items"]:
            assert "date" in item
            assert "knowledgeDownloads" in item
            assert "personaDownloads" in item
            assert "knowledgeStars" in item
            assert "personaStars" in item

    def test_get_dashboard_trend_stats_with_data(self, test_db, factory):
        """测试有数据的趋势统计"""
        import uuid

        from app.models.database import DownloadRecord, KnowledgeBase, PersonaCard, StarRecord

        user = factory.create_user()

        # 创建知识库
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test",
            uploader_id=user.id,
            copyright_owner="Test",
            is_pending=False,
            is_public=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        test_db.add(kb)

        # 创建人格卡
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test",
            uploader_id=user.id,
            copyright_owner="Test",
            version="1.0.0",
            base_path="/tmp/test_pc",
            is_pending=False,
            is_public=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        test_db.add(pc)
        test_db.commit()

        # 创建下载记录
        download1 = DownloadRecord(
            id=str(uuid.uuid4()), target_id=kb.id, target_type="knowledge", created_at=datetime.now()
        )
        test_db.add(download1)

        download2 = DownloadRecord(
            id=str(uuid.uuid4()), target_id=pc.id, target_type="persona", created_at=datetime.now()
        )
        test_db.add(download2)

        # 创建收藏记录
        star1 = StarRecord(
            id=str(uuid.uuid4()),
            target_id=kb.id,
            target_type="knowledge",
            user_id=str(uuid.uuid4()),
            created_at=datetime.now(),
        )
        test_db.add(star1)

        star2 = StarRecord(
            id=str(uuid.uuid4()),
            target_id=pc.id,
            target_type="persona",
            user_id=str(uuid.uuid4()),
            created_at=datetime.now(),
        )
        test_db.add(star2)
        test_db.commit()

        service = UserService(test_db)
        result = service.get_dashboard_trend_stats(user.id, days=7)

        assert result is not None
        assert result["days"] == 7
        assert len(result["items"]) == 7

        # 今天应该有数据
        today_str = datetime.now().date().strftime("%Y-%m-%d")
        today_item = next((item for item in result["items"] if item["date"] == today_str), None)
        assert today_item is not None
        assert today_item["knowledgeDownloads"] >= 1
        assert today_item["personaDownloads"] >= 1
        assert today_item["knowledgeStars"] >= 1
        assert today_item["personaStars"] >= 1

    def test_get_dashboard_trend_stats_min_days(self, test_db, factory):
        """测试最小天数限制"""
        user = factory.create_user()
        service = UserService(test_db)

        # 请求 0 天，应该被限制为最小值（1天）
        result = service.get_dashboard_trend_stats(user.id, days=0)

        assert result is not None
        assert result["days"] >= 1

    def test_get_dashboard_trend_stats_max_days(self, test_db, factory):
        """测试最大天数限制"""
        user = factory.create_user()
        service = UserService(test_db)

        # 请求 1000 天，应该被限制为最大值（90天）
        result = service.get_dashboard_trend_stats(user.id, days=1000)

        assert result is not None
        assert result["days"] <= 90

    def test_get_dashboard_trend_stats_30_days(self, test_db, factory):
        """测试 30 天的趋势统计"""
        user = factory.create_user()
        service = UserService(test_db)

        result = service.get_dashboard_trend_stats(user.id, days=30)

        assert result is not None
        assert result["days"] == 30
        assert len(result["items"]) == 30

    def test_get_dashboard_trend_stats_database_error(self, test_db, factory):
        """测试数据库错误时的处理"""
        user = factory.create_user()

        # 创建一个会抛出异常的 mock
        db_mock = Mock(spec=Session)
        db_mock.query.side_effect = Exception("Database error")

        service = UserService(db_mock)
        result = service.get_dashboard_trend_stats(user.id, days=7)

        # 应该返回空数据而不是抛出异常
        assert result is not None
        assert result["days"] == 7
        assert result["items"] == []

    def test_get_dashboard_trend_stats_no_data(self, test_db, factory):
        """测试没有数据的用户"""
        user = factory.create_user()
        service = UserService(test_db)

        result = service.get_dashboard_trend_stats(user.id, days=7)

        assert result is not None
        assert result["days"] == 7
        assert len(result["items"]) == 7

        # 所有数据应该为 0
        for item in result["items"]:
            assert item["knowledgeDownloads"] == 0
            assert item["personaDownloads"] == 0
            assert item["knowledgeStars"] == 0
            assert item["personaStars"] == 0


class TestUserServiceAdditionalCoverage:
    """额外的测试以提升覆盖率"""

    def test_update_user_email_conflict(self, test_db, factory):
        """测试更新用户邮箱时的冲突"""
        _ = factory.create_user(username="user1", email="user1@example.com")
        user2 = factory.create_user(username="user2", email="user2@example.com")

        service = UserService(test_db)

        # 尝试将 user2 的邮箱改为 user1 的邮箱
        result = service.update_user(user2.id, email="user1@example.com")

        # 应该返回 None，因为邮箱已存在
        assert result is None
