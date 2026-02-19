"""
Unit tests for API dependency injection module
Tests authentication and authorization dependencies
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_admin_user,
    get_moderator_user,
    get_current_user_optional
)
from app.models.database import User
from app.core.security import create_user_token


class TestGetCurrentUser:
    """Test get_current_user dependency"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, test_db: Session, test_user: User):
        """Test successful user authentication"""
        # Create valid token
        token = create_user_token(
            user_id=test_user.id,
            username=test_user.username,
            role="user",
            password_version=test_user.password_version
        )
        
        # Create credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        # Call dependency
        result = await get_current_user(credentials, test_db)
        
        # Verify result
        assert result["id"] == test_user.id
        assert result["username"] == test_user.username
        assert result["email"] == test_user.email
        assert result["role"] == "user"
        assert result["is_admin"] is False
        assert result["is_moderator"] is False
        assert result["is_super_admin"] is False
    
    @pytest.mark.asyncio
    async def test_get_current_user_admin(self, test_db: Session):
        """Test authentication with admin user"""
        # Create admin user
        admin_user = User(
            id=str(uuid.uuid4()),
            username="adminuser",
            email="admin@example.com",
            hashed_password="hashed",
            is_active=True,
            is_admin=True,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(admin_user)
        test_db.commit()
        test_db.refresh(admin_user)
        
        # Create valid token
        token = create_user_token(
            user_id=admin_user.id,
            username=admin_user.username,
            role="admin",
            password_version=admin_user.password_version
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        result = await get_current_user(credentials, test_db)
        
        assert result["role"] == "admin"
        assert result["is_admin"] is True
        assert result["is_moderator"] is True
        assert result["is_super_admin"] is False
    
    @pytest.mark.asyncio
    async def test_get_current_user_super_admin(self, test_db: Session):
        """Test authentication with super admin user"""
        # Create super admin user
        super_admin = User(
            id=str(uuid.uuid4()),
            username="superadmin",
            email="superadmin@example.com",
            hashed_password="hashed",
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=True,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(super_admin)
        test_db.commit()
        test_db.refresh(super_admin)
        
        token = create_user_token(
            user_id=super_admin.id,
            username=super_admin.username,
            role="super_admin",
            password_version=super_admin.password_version
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        result = await get_current_user(credentials, test_db)
        
        assert result["role"] == "super_admin"
        assert result["is_admin"] is True
        assert result["is_moderator"] is True
        assert result["is_super_admin"] is True
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, test_db: Session):
        """Test authentication with invalid token"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_db)
        
        assert exc_info.value.status_code == 401
        assert "Invalid authentication credentials" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self, test_db: Session):
        """Test authentication when user doesn't exist in database"""
        # Create token with non-existent user ID
        token = create_user_token(
            user_id="non-existent-id",
            username="ghost",
            role="user",
            password_version=0
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_db)
        
        assert exc_info.value.status_code == 401
        assert "User not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_password_changed(self, test_db: Session, test_user: User):
        """Test authentication fails when password has been changed"""
        # Create token with old password version
        token = create_user_token(
            user_id=test_user.id,
            username=test_user.username,
            role="user",
            password_version=0
        )
        
        # Update user's password version
        test_user.password_version = 1
        test_db.commit()
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_db)
        
        assert exc_info.value.status_code == 401
        assert "Token expired due to password change" in exc_info.value.detail


class TestGetAdminUser:
    """Test get_admin_user dependency"""
    
    @pytest.mark.asyncio
    async def test_get_admin_user_success(self):
        """Test admin user access granted"""
        current_user = {
            "id": "user-id",
            "username": "admin",
            "is_admin": True,
            "is_moderator": True,
            "is_super_admin": False
        }
        
        result = await get_admin_user(current_user)
        
        assert result == current_user
    
    @pytest.mark.asyncio
    async def test_get_admin_user_super_admin(self):
        """Test super admin user access granted"""
        current_user = {
            "id": "user-id",
            "username": "superadmin",
            "is_admin": True,
            "is_moderator": True,
            "is_super_admin": True
        }
        
        result = await get_admin_user(current_user)
        
        assert result == current_user
    
    @pytest.mark.asyncio
    async def test_get_admin_user_forbidden(self):
        """Test regular user denied admin access"""
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
    
    @pytest.mark.asyncio
    async def test_get_admin_user_moderator_forbidden(self):
        """Test moderator denied admin access"""
        current_user = {
            "id": "user-id",
            "username": "moderator",
            "is_admin": False,
            "is_moderator": True,
            "is_super_admin": False
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user(current_user)
        
        assert exc_info.value.status_code == 403


class TestGetModeratorUser:
    """Test get_moderator_user dependency"""
    
    @pytest.mark.asyncio
    async def test_get_moderator_user_success(self):
        """Test moderator user access granted"""
        current_user = {
            "id": "user-id",
            "username": "moderator",
            "is_admin": False,
            "is_moderator": True,
            "is_super_admin": False
        }
        
        result = await get_moderator_user(current_user)
        
        assert result == current_user
    
    @pytest.mark.asyncio
    async def test_get_moderator_user_admin(self):
        """Test admin user access granted"""
        current_user = {
            "id": "user-id",
            "username": "admin",
            "is_admin": True,
            "is_moderator": True,
            "is_super_admin": False
        }
        
        result = await get_moderator_user(current_user)
        
        assert result == current_user
    
    @pytest.mark.asyncio
    async def test_get_moderator_user_super_admin(self):
        """Test super admin user access granted"""
        current_user = {
            "id": "user-id",
            "username": "superadmin",
            "is_admin": True,
            "is_moderator": True,
            "is_super_admin": True
        }
        
        result = await get_moderator_user(current_user)
        
        assert result == current_user
    
    @pytest.mark.asyncio
    async def test_get_moderator_user_forbidden(self):
        """Test regular user denied moderator access"""
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
    """Test get_current_user_optional dependency"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_optional_with_valid_token(
        self, test_db: Session, test_user: User
    ):
        """Test optional authentication with valid token"""
        token = create_user_token(
            user_id=test_user.id,
            username=test_user.username,
            role="user",
            password_version=test_user.password_version
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        result = await get_current_user_optional(credentials, test_db)
        
        assert result is not None
        assert result["id"] == test_user.id
        assert result["username"] == test_user.username
    
    @pytest.mark.asyncio
    async def test_get_current_user_optional_no_credentials(self, test_db: Session):
        """Test optional authentication without credentials"""
        result = await get_current_user_optional(None, test_db)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_current_user_optional_invalid_token(self, test_db: Session):
        """Test optional authentication with invalid token returns None"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token"
        )
        
        result = await get_current_user_optional(credentials, test_db)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_current_user_optional_user_not_found(self, test_db: Session):
        """Test optional authentication when user doesn't exist returns None"""
        token = create_user_token(
            user_id="non-existent-id",
            username="ghost",
            role="user",
            password_version=0
        )
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        result = await get_current_user_optional(credentials, test_db)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_current_user_optional_password_changed(
        self, test_db: Session, test_user: User
    ):
        """Test optional authentication returns None when password changed"""
        token = create_user_token(
            user_id=test_user.id,
            username=test_user.username,
            role="user",
            password_version=0
        )
        
        # Update user's password version
        test_user.password_version = 1
        test_db.commit()
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        result = await get_current_user_optional(credentials, test_db)
        
        assert result is None
