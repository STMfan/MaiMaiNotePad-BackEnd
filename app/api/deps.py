"""
API dependency injection module
Provides authentication and authorization dependencies for FastAPI routes
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.services.user_service import UserService


# HTTP Bearer security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials containing JWT token
        db: Database session
        
    Returns:
        dict: User information dictionary containing:
            - id: User ID
            - username: Username
            - email: Email address
            - role: User role (for backward compatibility)
            - is_admin: Whether user is admin
            - is_moderator: Whether user is moderator
            - is_super_admin: Whether user is super admin
            
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials
    
    # Verify JWT token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user ID from token
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password version (invalidate token if password changed)
    token_pwd_ver = payload.get("pwd_ver", 0)
    user_pwd_ver = user.password_version or 0
    if token_pwd_ver < user_pwd_ver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired due to password change. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Determine user role for backward compatibility
    if user.is_super_admin:
        role = "super_admin"
    elif user.is_admin:
        role = "admin"
    elif user.is_moderator:
        role = "moderator"
    else:
        role = "user"
    
    # Return user information dictionary
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": role,
        "is_admin": user.is_admin or user.is_super_admin,
        "is_moderator": user.is_moderator or user.is_admin or user.is_super_admin,
        "is_super_admin": user.is_super_admin
    }


async def get_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current admin user (requires admin or super admin role).
    
    Args:
        current_user: Current authenticated user from get_current_user
        
    Returns:
        dict: User information dictionary
        
    Raises:
        HTTPException: 403 if user doesn't have admin permissions
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_moderator_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current moderator user (requires moderator, admin, or super admin role).
    
    Args:
        current_user: Current authenticated user from get_current_user
        
    Returns:
        dict: User information dictionary
        
    Raises:
        HTTPException: 403 if user doesn't have moderator permissions
    """
    if not current_user.get("is_moderator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db)
) -> Optional[dict]:
    """
    Get current authenticated user (optional, returns None if no token provided).
    
    This dependency is useful for endpoints that work differently for authenticated
    vs unauthenticated users, but don't require authentication.
    
    Args:
        credentials: Optional HTTP Bearer credentials containing JWT token
        db: Database session
        
    Returns:
        Optional[dict]: User information dictionary if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    
    # Verify JWT token
    payload = verify_token(token)
    if not payload:
        return None
    
    # Extract user ID from token
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    # Get user from database
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        return None
    
    # Verify password version (invalidate token if password changed)
    token_pwd_ver = payload.get("pwd_ver", 0)
    user_pwd_ver = user.password_version or 0
    if token_pwd_ver < user_pwd_ver:
        return None
    
    # Determine user role for backward compatibility
    if user.is_super_admin:
        role = "super_admin"
    elif user.is_admin:
        role = "admin"
    elif user.is_moderator:
        role = "moderator"
    else:
        role = "user"
    
    # Return user information dictionary
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": role,
        "is_admin": user.is_admin or user.is_super_admin,
        "is_moderator": user.is_moderator or user.is_admin or user.is_super_admin,
        "is_super_admin": user.is_super_admin
    }
