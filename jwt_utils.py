"""
JWT工具模块
处理JWT的生成和验证
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_urlsafe(32)
    import warnings
    warnings.warn(
        "⚠️  警告：JWT_SECRET_KEY 环境变量未设置！已生成临时密钥，生产环境必须设置强随机密钥！",
        UserWarning,
    )

if SECRET_KEY == "your-secret-key-change-this-in-production":
    import warnings
    warnings.warn(
        "⚠️  警告：使用默认 JWT Secret Key，生产环境不安全！请设置 JWT_SECRET_KEY 环境变量！",
        UserWarning,
    )

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

_access_minutes_default = 15
_jwt_exp_hours = _get_int_env("JWT_EXPIRATION_HOURS", 0)
if _jwt_exp_hours > 0:
    _access_minutes_default = _jwt_exp_hours * 60

ACCESS_TOKEN_EXPIRE_MINUTES = _get_int_env(
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    _get_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", _access_minutes_default),
)
REFRESH_TOKEN_EXPIRE_DAYS = _get_int_env("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    
    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # 生成JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """从JWT令牌中获取用户信息"""
    payload = verify_token(token)
    if payload is None:
        return None
    
    # 检查令牌是否过期
    exp = payload.get("exp")
    if exp is None:
        return None
    
    if datetime.utcnow() > datetime.fromtimestamp(exp):
        return None
    
    return payload

def create_user_token(user_id: str, username: str, role: str, password_version: int = 0) -> str:
    """为用户创建JWT访问令牌"""
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
    """创建刷新令牌"""
    return create_access_token(
        data={
            "sub": user_id,
            "type": "refresh"
        },
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
