"""
测试依赖注入模块

测试 app/api/deps.py 中的认证和授权依赖
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_admin_user,
    get_moderator_user,
    get_current_user_optional,
)
from app.models.database import User


class TestGetCurrentUser:
    """测试 get_current_user 依赖"""
    
    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, test_db):
        """测试有效令牌返回用户信息"""
        # 创建测试用户
        user = User(
            id="test-user-id",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            password_version=1
        )
        test_db.add(user)
        test_db.commit()
        
        # Mock credentials
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"
        
        # Mock verify_token
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": user.id, "pwd_ver": 1}
            
            # 调用依赖
            result = await get_current_user(credentials, test_db)
            
            # 验证结果
            assert result["id"] == user.id
            assert result["username"] == user.username
            assert result["email"] == user.email
            assert result["role"] == "user"
            assert result["is_admin"] is False
            assert result["is_moderator"] is False
            assert result["is_super_admin"] is False
    
    @pytest.mark.asyncio
    async def test_admin_user_returns_correct_role(self, test_db):
        """测试管理员用户返回正确角色"""
        user = User(
            id="admin-user-id",
            username="admin",
            email="admin@example.com",
            hashed_password="hashed",
            is_active=True,
            is_admin=True,
            is_moderator=False,
            is_super_admin=False,
            password_version=1
        )
        test_db.add(user)
        test_db.commit()
        
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": user.id, "pwd_ver": 1}
            
            result = await get_current_user(credentials, test_db)
            
            assert result["role"] == "admin"
            assert result["is_admin"] is True
            assert result["is_moderator"] is True
    
    @pytest.mark.asyncio
    async def test_super_admin_user_returns_correct_role(self, test_db):
        """测试超级管理员用户返回正确角色"""
        user = User(
            id="super-admin-id",
            username="superadmin",
            email="superadmin@example.com",
            hashed_password="hashed",
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=True,
            password_version=1
        )
        test_db.add(user)
        test_db.commit()
        
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": user.id, "pwd_ver": 1}
            
            result = await get_current_user(credentials, test_db)
            
            assert result["role"] == "super_admin"
            assert result["is_admin"] is True
            assert result["is_moderator"] is True
            assert result["is_super_admin"] is True
    
    @pytest.mark.asyncio
    async def test_moderator_user_returns_correct_role(self, test_db):
        """测试审核员用户返回正确角色"""
        user = User(
            id="moderator-id",
            username="moderator",
            email="moderator@example.com",
            hashed_password="hashed",
            is_active=True,
            is_admin=False,
            is_moderator=True,
            is_super_admin=False,
            password_version=1
        )
        test_db.add(user)
        test_db.commit()
        
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": user.id, "pwd_ver": 1}
            
            result = await get_current_user(credentials, test_db)
            
            assert result["role"] == "moderator"
            assert result["is_admin"] is False
            assert result["is_moderator"] is True
    
    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, test_db):
        """测试无效令牌抛出 401 异常"""
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "invalid_token"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, test_db)
            
            assert exc_info.value.status_code == 401
            assert "Invalid authentication credentials" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_token_without_user_id_raises_401(self, test_db):
        """测试没有用户 ID 的令牌抛出 401 异常"""
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "token_without_sub"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"other_field": "value"}
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, test_db)
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_nonexistent_user_raises_401(self, test_db):
        """测试不存在的用户抛出 401 异常"""
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "nonexistent-user-id", "pwd_ver": 1}
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, test_db)
            
            assert exc_info.value.status_code == 401
            assert "User not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_outdated_password_version_raises_401(self, test_db):
        """测试密码版本过期的令牌抛出 401 异常"""
        user = User(
            id="test-user-id",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            password_version=2  # 用户已更改密码
        )
        test_db.add(user)
        test_db.commit()
        
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "old_token"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": user.id, "pwd_ver": 1}  # 旧版本
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, test_db)
            
            assert exc_info.value.status_code == 401
            assert "password change" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_missing_password_version_in_token(self, test_db):
        """测试令牌中缺少密码版本时使用默认值 0"""
        user = User(
            id="test-user-id",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            password_version=None  # 用户没有密码版本
        )
        test_db.add(user)
        test_db.commit()
        
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "token_without_pwd_ver"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": user.id}  # 没有 pwd_ver
            
            result = await get_current_user(credentials, test_db)
            
            assert result["id"] == user.id


class TestGetAdminUser:
    """测试 get_admin_user 依赖"""
    
    @pytest.mark.asyncio
    async def test_admin_user_passes(self):
        """测试管理员用户通过检查"""
        current_user = {
            "id": "admin-id",
            "username": "admin",
            "is_admin": True,
            "is_moderator": True,
            "is_super_admin": False
        }
        
        result = await get_admin_user(current_user)
        assert result == current_user
    
    @pytest.mark.asyncio
    async def test_super_admin_user_passes(self):
        """测试超级管理员用户通过检查"""
        current_user = {
            "id": "super-admin-id",
            "username": "superadmin",
            "is_admin": True,
            "is_moderator": True,
            "is_super_admin": True
        }
        
        result = await get_admin_user(current_user)
        assert result == current_user
    
    @pytest.mark.asyncio
    async def test_non_admin_user_raises_403(self):
        """测试非管理员用户抛出 403 异常"""
        current_user = {
            "id": "user-id",
            "username": "user",
            "is_admin": False,
            "is_moderator": False,
            "is_super_admin": False
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user(current_user)
        
        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in exc_info.value.detail


class TestGetModeratorUser:
    """测试 get_moderator_user 依赖"""
    
    @pytest.mark.asyncio
    async def test_moderator_user_passes(self):
        """测试审核员用户通过检查"""
        current_user = {
            "id": "moderator-id",
            "username": "moderator",
            "is_admin": False,
            "is_moderator": True,
            "is_super_admin": False
        }
        
        result = await get_moderator_user(current_user)
        assert result == current_user
    
    @pytest.mark.asyncio
    async def test_admin_user_passes(self):
        """测试管理员用户通过检查"""
        current_user = {
            "id": "admin-id",
            "username": "admin",
            "is_admin": True,
            "is_moderator": True,
            "is_super_admin": False
        }
        
        result = await get_moderator_user(current_user)
        assert result == current_user
    
    @pytest.mark.asyncio
    async def test_non_moderator_user_raises_403(self):
        """测试非审核员用户抛出 403 异常"""
        current_user = {
            "id": "user-id",
            "username": "user",
            "is_admin": False,
            "is_moderator": False,
            "is_super_admin": False
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_moderator_user(current_user)
        
        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in exc_info.value.detail


class TestGetCurrentUserOptional:
    """测试 get_current_user_optional 依赖"""
    
    @pytest.mark.asyncio
    async def test_no_credentials_returns_none(self, test_db):
        """测试没有凭证时返回 None"""
        result = await get_current_user_optional(None, test_db)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, test_db):
        """测试有效令牌返回用户信息"""
        user = User(
            id="test-user-id",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            password_version=1
        )
        test_db.add(user)
        test_db.commit()
        
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": user.id, "pwd_ver": 1}
            
            result = await get_current_user_optional(credentials, test_db)
            
            assert result is not None
            assert result["id"] == user.id
            assert result["username"] == user.username
    
    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self, test_db):
        """测试无效令牌返回 None（不抛出异常）"""
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "invalid_token"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = None
            
            result = await get_current_user_optional(credentials, test_db)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_token_without_user_id_returns_none(self, test_db):
        """测试没有用户 ID 的令牌返回 None"""
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "token_without_sub"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"other_field": "value"}
            
            result = await get_current_user_optional(credentials, test_db)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_nonexistent_user_returns_none(self, test_db):
        """测试不存在的用户返回 None"""
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid_token"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "nonexistent-user-id", "pwd_ver": 1}
            
            result = await get_current_user_optional(credentials, test_db)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_outdated_password_version_returns_none(self, test_db):
        """测试密码版本过期的令牌返回 None"""
        user = User(
            id="test-user-id",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            password_version=2
        )
        test_db.add(user)
        test_db.commit()
        
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "old_token"
        
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": user.id, "pwd_ver": 1}
            
            result = await get_current_user_optional(credentials, test_db)
            assert result is None
