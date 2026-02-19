"""
Security utilities for JWT and password management
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
import secrets
import warnings

from app.core.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# JWT configuration with validation
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

# Calculate access token expiration
_access_minutes_default = 15
if settings.JWT_EXPIRATION_HOURS > 0:
    _access_minutes_default = settings.JWT_EXPIRATION_HOURS * 60

ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES or _access_minutes_default
REFRESH_TOKEN_EXPIRE_DAYS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generate password hash using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
        
    Note:
        bcrypt has a maximum password length of 72 bytes
    """
    # Limit password to 72 bytes for bcrypt
    return pwd_context.hash(password[:72])


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Payload data to encode in token
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Generate JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Optional[Dict[str, Any]]: Decoded payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Extract user information from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Optional[Dict[str, Any]]: User payload if valid and not expired, None otherwise
    """
    payload = verify_token(token)
    if payload is None:
        return None
    
    # Check if token is expired
    exp = payload.get("exp")
    if exp is None:
        return None
    
    if datetime.now(timezone.utc) > datetime.fromtimestamp(exp, timezone.utc):
        return None
    
    return payload


def create_user_token(user_id: str, username: str, role: str, password_version: int = 0) -> str:
    """
    Create JWT access token for a user.
    
    Args:
        user_id: User ID
        username: Username
        role: User role
        password_version: Password version for token invalidation
        
    Returns:
        str: JWT access token
    """
    return create_access_token(
        data={
            "sub": user_id,
            "username": username,
            "role": role,
            "type": "access",
            "pwd_ver": password_version  # Password version number
        }
    )


def create_refresh_token(user_id: str) -> str:
    """
    Create JWT refresh token.
    
    Args:
        user_id: User ID
        
    Returns:
        str: JWT refresh token
    """
    return create_access_token(
        data={
            "sub": user_id,
            "type": "refresh"
        },
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
