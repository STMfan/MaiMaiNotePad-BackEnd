"""
JWT工具模块
处理JWT的生成和验证
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from passlib.context import CryptContext

# 配置密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30天

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

def create_user_token(user_id: str, username: str, role: str) -> str:
    """为用户创建JWT令牌"""
    return create_access_token(
        data={
            "sub": user_id,
            "username": username,
            "role": role
        }
    )