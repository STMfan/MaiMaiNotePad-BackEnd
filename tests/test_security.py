"""
Unit tests for security module (JWT and password management)
"""

import pytest
from datetime import datetime, timedelta, timezone
import jwt

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
    get_user_from_token,
    create_user_token,
    create_refresh_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)


class TestPasswordHashing:
    """测试密码哈希和验证功能"""
    
    def test_password_hash_generation(self):
        """测试密码哈希生成"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # 验证哈希不为空
        assert hashed is not None
        assert len(hashed) > 0
        
        # 验证哈希与原密码不同
        assert hashed != password
    
    def test_password_verification_success(self):
        """测试密码验证成功"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # 验证正确的密码
        assert verify_password(password, hashed) is True
    
    def test_password_verification_failure(self):
        """测试密码验证失败"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        # 验证错误的密码
        assert verify_password(wrong_password, hashed) is False
    
    def test_password_hash_uniqueness(self):
        """测试相同密码生成不同的哈希（bcrypt salt）"""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # bcrypt 每次生成的哈希应该不同（因为 salt 不同）
        assert hash1 != hash2
        
        # 但两个哈希都应该能验证原密码
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
    
    def test_password_length_limit(self):
        """测试密码长度限制（bcrypt 限制 72 字节）"""
        # 创建超过 72 字节的密码
        long_password = "a" * 100
        hashed = get_password_hash(long_password)
        
        # 验证前 72 字节应该匹配
        assert verify_password(long_password[:72], hashed) is True
        
        # 完整密码也应该匹配（因为函数内部截断）
        assert verify_password(long_password, hashed) is True


class TestJWTCreation:
    """测试 JWT 令牌创建"""
    
    def test_create_access_token_basic(self):
        """测试基本的访问令牌创建"""
        data = {"sub": "user123", "username": "testuser"}
        token = create_access_token(data)
        
        # 验证令牌不为空
        assert token is not None
        assert len(token) > 0
        
        # 验证令牌可以解码
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
        assert "exp" in payload
    
    def test_create_access_token_with_custom_expiration(self):
        """测试使用自定义过期时间创建令牌"""
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=30)
        
        # 记录创建前的时间
        before_time = datetime.now(timezone.utc)
        token = create_access_token(data, expires_delta=expires_delta)
        after_time = datetime.now(timezone.utc)
        
        # 解码并验证过期时间
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"], timezone.utc)
        
        # 验证过期时间在合理范围内（JWT 时间戳精度为秒，需要容忍微秒差异）
        expected_min = (before_time + expires_delta).replace(microsecond=0)
        expected_max = (after_time + expires_delta).replace(microsecond=0) + timedelta(seconds=1)
        
        assert expected_min <= exp_time <= expected_max
    
    def test_create_access_token_default_expiration(self):
        """测试默认过期时间"""
        data = {"sub": "user123"}
        
        # 记录创建前的时间
        before_time = datetime.now(timezone.utc)
        token = create_access_token(data)
        after_time = datetime.now(timezone.utc)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"], timezone.utc)
        
        # 验证过期时间在合理范围内（JWT 时间戳精度为秒，需要容忍微秒差异）
        expected_min = (before_time + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).replace(microsecond=0)
        expected_max = (after_time + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).replace(microsecond=0) + timedelta(seconds=1)
        
        assert expected_min <= exp_time <= expected_max
    
    def test_create_user_token(self):
        """测试创建用户令牌"""
        user_id = "user123"
        username = "testuser"
        role = "user"
        password_version = 1
        
        token = create_user_token(user_id, username, role, password_version)
        
        # 验证令牌内容
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == user_id
        assert payload["username"] == username
        assert payload["role"] == role
        assert payload["type"] == "access"
        assert payload["pwd_ver"] == password_version
    
    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        user_id = "user123"
        
        # 记录创建前的时间
        before_time = datetime.now(timezone.utc)
        token = create_refresh_token(user_id)
        after_time = datetime.now(timezone.utc)
        
        # 验证令牌内容
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        
        # 验证过期时间（JWT 时间戳精度为秒，需要容忍微秒差异）
        exp_time = datetime.fromtimestamp(payload["exp"], timezone.utc)
        expected_min = (before_time + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).replace(microsecond=0)
        expected_max = (after_time + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).replace(microsecond=0) + timedelta(seconds=1)
        
        assert expected_min <= exp_time <= expected_max


class TestJWTVerification:
    """测试 JWT 令牌验证"""
    
    def test_verify_token_valid(self):
        """测试验证有效令牌"""
        data = {"sub": "user123", "username": "testuser"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
    
    def test_verify_token_invalid(self):
        """测试验证无效令牌"""
        invalid_token = "invalid.token.string"
        
        payload = verify_token(invalid_token)
        
        assert payload is None
    
    def test_verify_token_expired(self):
        """测试验证过期令牌"""
        data = {"sub": "user123"}
        # 创建已过期的令牌（-1 分钟）
        expires_delta = timedelta(minutes=-1)
        token = create_access_token(data, expires_delta=expires_delta)
        
        payload = verify_token(token)
        
        # verify_token 会检查过期时间，过期令牌返回 None
        assert payload is None
    
    def test_verify_token_wrong_signature(self):
        """测试验证签名错误的令牌"""
        data = {"sub": "user123"}
        # 使用错误的密钥创建令牌
        wrong_token = jwt.encode(data, "wrong_secret_key", algorithm=ALGORITHM)
        
        payload = verify_token(wrong_token)
        
        assert payload is None
    
    def test_get_user_from_token_valid(self):
        """测试从有效令牌获取用户信息"""
        data = {"sub": "user123", "username": "testuser"}
        token = create_access_token(data)
        
        user_payload = get_user_from_token(token)
        
        assert user_payload is not None
        assert user_payload["sub"] == "user123"
        assert user_payload["username"] == "testuser"
    
    def test_get_user_from_token_expired(self):
        """测试从过期令牌获取用户信息"""
        data = {"sub": "user123"}
        # 创建已过期的令牌
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta=expires_delta)
        
        user_payload = get_user_from_token(token)
        
        # 过期令牌应该返回 None
        assert user_payload is None
    
    def test_get_user_from_token_invalid(self):
        """测试从无效令牌获取用户信息"""
        invalid_token = "invalid.token.string"
        
        user_payload = get_user_from_token(invalid_token)
        
        assert user_payload is None
    
    def test_get_user_from_token_no_expiration(self):
        """测试没有过期时间的令牌"""
        # 手动创建没有 exp 字段的令牌
        data = {"sub": "user123"}
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
        
        user_payload = get_user_from_token(token)
        
        # 没有过期时间应该返回 None
        assert user_payload is None


class TestPasswordVersionMechanism:
    """测试密码版本机制"""
    
    def test_password_version_in_token(self):
        """测试令牌中包含密码版本"""
        user_id = "user123"
        username = "testuser"
        role = "user"
        password_version = 2
        
        token = create_user_token(user_id, username, role, password_version)
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["pwd_ver"] == password_version
    
    def test_password_version_default(self):
        """测试密码版本默认值"""
        user_id = "user123"
        username = "testuser"
        role = "user"
        
        # 不传递 password_version，应该使用默认值 0
        token = create_user_token(user_id, username, role)
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["pwd_ver"] == 0
    
    def test_password_version_increment(self):
        """测试密码版本递增"""
        user_id = "user123"
        username = "testuser"
        role = "user"
        
        # 创建版本 1 的令牌
        token_v1 = create_user_token(user_id, username, role, password_version=1)
        payload_v1 = verify_token(token_v1)
        
        # 创建版本 2 的令牌
        token_v2 = create_user_token(user_id, username, role, password_version=2)
        payload_v2 = verify_token(token_v2)
        
        assert payload_v1["pwd_ver"] == 1
        assert payload_v2["pwd_ver"] == 2
        
        # 两个令牌应该不同
        assert token_v1 != token_v2
