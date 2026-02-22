"""
安全工具模块

提供 JWT 令牌管理和密码哈希功能。
"""

import jwt
import os
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import secrets
import warnings

from app.core.config import settings
from app.core.config_manager import config_manager


# bcrypt 配置
# 在测试环境中使用更少的 rounds 来加速测试（通过 BCRYPT_ROUNDS 环境变量）
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS") or config_manager.get_int("security.bcrypt_rounds", 12))


# JWT 配置及校验
SECRET_KEY = settings.JWT_SECRET_KEY
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(32)
    warnings.warn(
        "⚠️  警告：JWT_SECRET_KEY 环境变量未设置！已生成临时密钥，生产环境必须设置强随机密钥！",
        UserWarning,
    )

if SECRET_KEY == "your-secret-key-change-this-in-production":
    warnings.warn(
        "⚠️  警告：使用默认 JWT Secret Key，生产环境不安全！请设置 JWT_SECRET_KEY 环境变量！",
        UserWarning,
    )

ALGORITHM = settings.JWT_ALGORITHM

# 计算访问令牌过期时间
_access_minutes_default = 15
if settings.JWT_EXPIRATION_HOURS > 0:
    _access_minutes_default = settings.JWT_EXPIRATION_HOURS * 60

ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES or _access_minutes_default
REFRESH_TOKEN_EXPIRE_DAYS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配。
    
    Args:
        plain_password: 明文密码
        hashed_password: 数据库中的哈希密码
        
    Returns:
        bool: 密码匹配返回 True，否则返回 False
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    使用 bcrypt 生成密码哈希。
    
    Args:
        password: 明文密码
        
    Returns:
        str: 哈希后的密码
        
    注意:
        bcrypt 最大密码长度为 72 字节
    """
    # 限制密码长度为 72 字节（bcrypt 限制）
    return pwd_context.hash(password[:72])


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌。
    
    Args:
        data: 要编码到令牌中的载荷数据
        expires_delta: 可选的自定义过期时间
        
    Returns:
        str: 编码后的 JWT 令牌
    """
    to_encode = data.copy()
    
    # 设置过期时间
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # 生成 JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    验证并解码 JWT 令牌。
    
    Args:
        token: JWT 令牌字符串
        
    Returns:
        Optional[Dict[str, Any]]: 有效则返回解码后的载荷，否则返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    从 JWT 令牌中提取用户信息。
    
    Args:
        token: JWT 令牌字符串
        
    Returns:
        Optional[Dict[str, Any]]: 有效且未过期则返回用户载荷，否则返回 None
    """
    payload = verify_token(token)
    if payload is None:
        return None
    
    # 检查令牌是否过期
    exp = payload.get("exp")
    if exp is None:
        return None
    
    if datetime.now(timezone.utc) > datetime.fromtimestamp(exp, timezone.utc):
        return None
    
    return payload


def create_user_token(user_id: str, username: str, role: str, password_version: int = 0) -> str:
    """
    为用户创建 JWT 访问令牌。
    
    Args:
        user_id: 用户 ID
        username: 用户名
        role: 用户角色
        password_version: 密码版本号，用于令牌失效控制
        
    Returns:
        str: JWT 访问令牌
    """
    return create_access_token(
        data={
            "sub": user_id,
            "username": username,
            "role": role,
            "type": "access",
            "pwd_ver": password_version  # 密码版本号
        }
    )


def create_refresh_token(user_id: str) -> str:
    """
    创建 JWT 刷新令牌。
    
    Args:
        user_id: 用户 ID
        
    Returns:
        str: JWT 刷新令牌
    """
    return create_access_token(
        data={
            "sub": user_id,
            "type": "refresh"
        },
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
