"""
API 依赖注入模块

提供 FastAPI 路由所需的认证和授权依赖。
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.core.messages import get_message
from app.services.user_service import UserService


# HTTP Bearer 安全方案
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """
    从 JWT 令牌获取当前已认证用户。
    
    Args:
        credentials: 包含 JWT 令牌的 HTTP Bearer 凭证
        db: 数据库会话
        
    Returns:
        dict: 用户信息字典，包含：
            - id: 用户 ID
            - username: 用户名
            - email: 邮箱地址
            - role: 用户角色（向后兼容）
            - is_admin: 是否为管理员
            - is_moderator: 是否为审核员
            - is_super_admin: 是否为超级管理员
            
    Raises:
        HTTPException: 令牌无效或用户不存在时返回 401
    """
    token = credentials.credentials
    
    # 验证 JWT 令牌
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_message("invalid_credentials"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 从令牌中提取用户 ID
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_message("invalid_credentials"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 从数据库获取用户
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_message("user_not_found"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证密码版本号（密码修改后令牌失效）
    token_pwd_ver = payload.get("pwd_ver", 0)
    user_pwd_ver = user.password_version or 0
    if token_pwd_ver < user_pwd_ver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_message("password_changed"),
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 确定用户角色（向后兼容）
    if user.is_super_admin:
        role = "super_admin"
    elif user.is_admin:
        role = "admin"
    elif user.is_moderator:
        role = "moderator"
    else:
        role = "user"
    
    # 返回用户信息字典
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
    获取当前管理员用户（需要管理员或超级管理员角色）。
    
    Args:
        current_user: 来自 get_current_user 的当前已认证用户
        
    Returns:
        dict: 用户信息字典
        
    Raises:
        HTTPException: 用户没有管理员权限时返回 403
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=get_message("insufficient_permissions")
        )
    return current_user


async def get_moderator_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    获取当前审核员用户（需要审核员、管理员或超级管理员角色）。
    
    Args:
        current_user: 来自 get_current_user 的当前已认证用户
        
    Returns:
        dict: 用户信息字典
        
    Raises:
        HTTPException: 用户没有审核员权限时返回 403
    """
    if not current_user.get("is_moderator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=get_message("insufficient_permissions")
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: Session = Depends(get_db)
) -> Optional[dict]:
    """
    获取当前已认证用户（可选，未提供令牌时返回 None）。
    
    适用于已认证和未认证用户行为不同但不强制要求认证的端点。
    
    Args:
        credentials: 可选的 HTTP Bearer 凭证
        db: 数据库会话
        
    Returns:
        Optional[dict]: 已认证返回用户信息字典，否则返回 None
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    
    # 验证 JWT 令牌
    payload = verify_token(token)
    if not payload:
        return None
    
    # 从令牌中提取用户 ID
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    # 从数据库获取用户
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        return None
    
    # 验证密码版本号（密码修改后令牌失效）
    token_pwd_ver = payload.get("pwd_ver", 0)
    user_pwd_ver = user.password_version or 0
    if token_pwd_ver < user_pwd_ver:
        return None
    
    # 确定用户角色（向后兼容）
    if user.is_super_admin:
        role = "super_admin"
    elif user.is_admin:
        role = "admin"
    elif user.is_moderator:
        role = "moderator"
    else:
        role = "user"
    
    # 返回用户信息字典
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": role,
        "is_admin": user.is_admin or user.is_super_admin,
        "is_moderator": user.is_moderator or user.is_admin or user.is_super_admin,
        "is_super_admin": user.is_super_admin
    }
