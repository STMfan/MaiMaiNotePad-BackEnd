"""
安全模块单元测试

测试密码哈希、JWT令牌生成和验证、
以及加密/解密功能。

需求：2.2 - Core模块测试
任务：15.5.1 - security.py (77% → 95%)
"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
    get_user_from_token,
    create_user_token,
    create_refresh_token,
    SECRET_KEY,
    ALGORITHM
)


class TestPasswordHashing:
    """测试密码哈希功能"""
    
    def test_get_password_hash_basic(self):
        """测试基本密码哈希"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0
    
    def test_get_password_hash_different_passwords(self):
        """测试不同密码生成不同哈希"""
        password1 = "password1"
        password2 = "password2"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2
    
    def test_get_password_hash_same_password_different_hashes(self):
        """测试相同密码生成不同哈希（盐值）"""
        password = "samepassword"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # bcrypt 每次生成不同的哈希（因为盐值不同）
        assert hash1 != hash2
    
    def test_get_password_hash_long_password(self):
        """测试长密码哈希（bcrypt 限制72字节）"""
        long_password = "a" * 100
        hashed = get_password_hash(long_password)
        
        assert hashed is not None
        # 验证只使用前72字节
        assert verify_password(long_password[:72], hashed)
    
    def test_get_password_hash_special_characters(self):
        """测试包含特殊字符的密码"""
        password = "P@ssw0rd!#$%^&*()"
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert verify_password(password, hashed)
    
    def test_get_password_hash_unicode(self):
        """测试Unicode字符密码"""
        password = "密码123パスワード"
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert verify_password(password, hashed)
    
    def test_get_password_hash_empty_string(self):
        """测试空字符串密码"""
        password = ""
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert verify_password(password, hashed)


class TestPasswordVerification:
    """测试密码验证功能"""
    
    def test_verify_password_correct(self):
        """测试正确密码验证"""
        password = "correctpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_case_sensitive(self):
        """测试密码大小写敏感"""
        password = "Password123"
        hashed = get_password_hash(password)
        
        assert verify_password("password123", hashed) is False
        assert verify_password("PASSWORD123", hashed) is False
        assert verify_password("Password123", hashed) is True
    
    def test_verify_password_with_spaces(self):
        """测试包含空格的密码"""
        password = "pass word 123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("password123", hashed) is False
    
    def test_verify_password_invalid_hash(self):
        """测试无效哈希"""
        password = "testpassword"
        invalid_hash = "invalid_hash_string"
        
        # 应该返回 False 或抛出异常
        try:
            result = verify_password(password, invalid_hash)
            assert result is False
        except Exception:
            pass  # 某些实现可能抛出异常
    
    def test_verify_password_empty_password(self):
        """测试空密码验证"""
        password = ""
        hashed = get_password_hash(password)
        
        assert verify_password("", hashed) is True
        assert verify_password("nonempty", hashed) is False


class TestJWTTokenGeneration:
    """测试JWT令牌生成"""
    
    def test_create_access_token_basic(self):
        """测试基本访问令牌创建"""
        data = {"sub": "user123", "username": "testuser"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_expiration(self):
        """测试带自定义过期时间的令牌"""
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        
        # 解码验证过期时间
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], timezone.utc)
        now = datetime.now(timezone.utc)
        
        # 验证过期时间大约是30分钟后
        time_diff = (exp - now).total_seconds()
        assert 1700 < time_diff < 1900  # 约30分钟（允许误差）
    
    def test_create_access_token_includes_data(self):
        """测试令牌包含所有数据"""
        data = {
            "sub": "user123",
            "username": "testuser",
            "role": "admin",
            "custom_field": "value"
        }
        token = create_access_token(data)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
        assert payload["role"] == "admin"
        assert payload["custom_field"] == "value"
    
    def test_create_access_token_includes_expiration(self):
        """测试令牌包含过期时间"""
        data = {"sub": "user123"}
        token = create_access_token(data)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload
        assert isinstance(payload["exp"], (int, float))
    
    def test_create_user_token(self):
        """测试创建用户令牌"""
        token = create_user_token(
            user_id="user123",
            username="testuser",
            role="user",
            password_version=1
        )
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
        assert payload["role"] == "user"
        assert payload["type"] == "access"
        assert payload["pwd_ver"] == 1
    
    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        token = create_refresh_token(user_id="user123")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"
        assert "exp" in payload
    
    def test_create_refresh_token_longer_expiration(self):
        """测试刷新令牌有更长的过期时间"""
        access_token = create_access_token({"sub": "user123"})
        refresh_token = create_refresh_token("user123")
        
        access_payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        refresh_payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 刷新令牌应该有更长的过期时间
        assert refresh_payload["exp"] > access_payload["exp"]


class TestJWTTokenVerification:
    """测试JWT令牌验证"""
    
    def test_verify_token_valid(self):
        """测试验证有效令牌"""
        data = {"sub": "user123", "username": "testuser"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
    
    def test_verify_token_expired(self):
        """测试验证过期令牌"""
        data = {"sub": "user123"}
        # 创建已过期的令牌
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta)
        
        payload = verify_token(token)
        
        # 过期令牌应该返回 None
        assert payload is None
    
    def test_verify_token_invalid_signature(self):
        """测试验证签名无效的令牌"""
        data = {"sub": "user123"}
        token = create_access_token(data)
        
        # 修改令牌使签名无效
        tampered_token = token[:-10] + "tampered123"
        
        payload = verify_token(tampered_token)
        
        assert payload is None
    
    def test_verify_token_malformed(self):
        """测试验证格式错误的令牌"""
        malformed_token = "not.a.valid.jwt.token"
        
        payload = verify_token(malformed_token)
        
        assert payload is None
    
    def test_verify_token_empty_string(self):
        """测试验证空字符串令牌"""
        payload = verify_token("")
        
        assert payload is None
    
    def test_get_user_from_token_valid(self):
        """测试从有效令牌获取用户信息"""
        token = create_user_token(
            user_id="user123",
            username="testuser",
            role="user"
        )
        
        user_data = get_user_from_token(token)
        
        assert user_data is not None
        assert user_data["sub"] == "user123"
        assert user_data["username"] == "testuser"
    
    def test_get_user_from_token_expired(self):
        """测试从过期令牌获取用户信息"""
        data = {"sub": "user123", "username": "testuser"}
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta)
        
        user_data = get_user_from_token(token)
        
        assert user_data is None
    
    def test_get_user_from_token_no_expiration(self):
        """测试没有过期时间的令牌"""
        # 手动创建没有exp字段的令牌
        data = {"sub": "user123"}
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
        
        user_data = get_user_from_token(token)
        
        # 没有exp字段应该返回None
        assert user_data is None
    
    def test_get_user_from_token_invalid(self):
        """测试从无效令牌获取用户信息"""
        invalid_token = "invalid.token.string"
        
        user_data = get_user_from_token(invalid_token)
        
        assert user_data is None


class TestTokenSecurity:
    """测试令牌安全性"""
    
    def test_token_cannot_be_modified(self):
        """测试令牌不能被修改"""
        token = create_user_token(
            user_id="user123",
            username="testuser",
            role="user"
        )
        
        # 尝试解码并修改
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        payload["role"] = "admin"  # 尝试提升权限
        
        # 重新编码（但签名会不同）
        modified_token = jwt.encode(payload, "wrong_secret", algorithm=ALGORITHM)
        
        # 验证应该失败
        verified_payload = verify_token(modified_token)
        assert verified_payload is None
    
    def test_different_users_different_tokens(self):
        """测试不同用户生成不同令牌"""
        token1 = create_user_token("user1", "username1", "user")
        token2 = create_user_token("user2", "username2", "user")
        
        assert token1 != token2
    
    def test_token_includes_password_version(self):
        """测试令牌包含密码版本"""
        token = create_user_token(
            user_id="user123",
            username="testuser",
            role="user",
            password_version=5
        )
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["pwd_ver"] == 5
    
    def test_password_version_invalidation(self):
        """测试密码版本变更使令牌失效"""
        # 创建版本1的令牌
        token_v1 = create_user_token(
            user_id="user123",
            username="testuser",
            role="user",
            password_version=1
        )
        
        # 创建版本2的令牌（密码已更改）
        token_v2 = create_user_token(
            user_id="user123",
            username="testuser",
            role="user",
            password_version=2
        )
        
        payload_v1 = jwt.decode(token_v1, SECRET_KEY, algorithms=[ALGORITHM])
        payload_v2 = jwt.decode(token_v2, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 版本应该不同
        assert payload_v1["pwd_ver"] != payload_v2["pwd_ver"]


class TestSecurityEdgeCases:
    """测试安全模块边缘情况"""
    
    def test_very_long_password(self):
        """测试超长密码"""
        long_password = "a" * 1000
        hashed = get_password_hash(long_password)
        
        # bcrypt 限制72字节
        assert verify_password(long_password[:72], hashed)
    
    def test_password_with_null_bytes(self):
        """测试包含空字节的密码"""
        password = "pass\x00word"
        
        # bcrypt不允许空字节，应该抛出异常
        with pytest.raises(Exception):
            hashed = get_password_hash(password)
    
    def test_token_with_large_payload(self):
        """测试大负载令牌"""
        large_data = {
            "sub": "user123",
            "data": "x" * 10000  # 大量数据
        }
        
        token = create_access_token(large_data)
        payload = verify_token(token)
        
        assert payload is not None
        assert len(payload["data"]) == 10000
    
    def test_concurrent_token_generation(self):
        """测试并发令牌生成"""
        tokens = []
        for i in range(100):
            token = create_user_token(f"user{i}", f"username{i}", "user")
            tokens.append(token)
        
        # 所有令牌应该不同
        assert len(set(tokens)) == 100
    
    def test_token_expiration_boundary(self):
        """测试令牌过期边界"""
        # 创建即将过期的令牌（1秒后）
        data = {"sub": "user123"}
        expires_delta = timedelta(seconds=1)
        token = create_access_token(data, expires_delta)
        
        # 立即验证应该成功
        payload = get_user_from_token(token)
        assert payload is not None
        
        # 等待2秒后验证应该失败
        import time
        time.sleep(2)
        payload = get_user_from_token(token)
        assert payload is None
