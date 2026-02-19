"""
Unit tests for authentication service
"""

import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.models.database import User, EmailVerification
from app.core.security import get_password_hash, verify_password


class TestAuthService:
    """Test cases for AuthService"""

    @pytest.fixture
    def auth_service(self, test_db: Session):
        """Create AuthService instance"""
        return AuthService(test_db)

    @pytest.fixture
    def user_service(self, test_db: Session):
        """Create UserService instance"""
        return UserService(test_db)

    @pytest.fixture
    def test_user(self, test_db: Session):
        """Create a test user"""
        user = User(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        return user

    def test_authenticate_user_success(self, auth_service: AuthService, test_user: User):
        """Test successful user authentication"""
        result = auth_service.authenticate_user("testuser", "password123")
        assert result is not None
        assert isinstance(result, dict)
        assert "access_token" in result
        assert "user" in result
        assert result["user"]["id"] == test_user.id
        assert result["user"]["username"] == test_user.username

    def test_authenticate_user_wrong_password(self, auth_service: AuthService, test_user: User):
        """Test authentication with wrong password"""
        user = auth_service.authenticate_user("testuser", "wrongpassword")
        assert user is None

    def test_authenticate_user_nonexistent(self, auth_service: AuthService):
        """Test authentication with nonexistent user"""
        user = auth_service.authenticate_user("nonexistent", "password123")
        assert user is None

    def test_authenticate_user_locked_account(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test authentication with locked account"""
        # Lock the account
        test_user.locked_until = datetime.now() + timedelta(minutes=30)
        test_db.commit()

        user = auth_service.authenticate_user("testuser", "password123")
        assert user is None

    def test_create_tokens(self, auth_service: AuthService, test_user: User):
        """Test token creation"""
        tokens = auth_service.create_tokens(test_user)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0
        assert "user" in tokens
        assert tokens["user"]["id"] == test_user.id
        assert tokens["user"]["username"] == test_user.username
        assert tokens["user"]["role"] == "user"

    def test_create_tokens_admin(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test token creation for admin user"""
        test_user.is_admin = True
        test_db.commit()

        tokens = auth_service.create_tokens(test_user)
        assert tokens["user"]["role"] == "admin"

    def test_register_user_success(self, auth_service: AuthService, test_db: Session):
        """Test successful user registration"""
        email = "newuser@example.com"
        code = "123456"
        
        # Save verification code
        auth_service.save_verification_code(email, code)
        
        # Verify code first
        assert auth_service.verify_email_code(email, code) is True
        
        # Register user
        user = auth_service.register_user(
            username="newuser",
            email=email,
            password="password123"
        )
        
        assert user is not None
        assert user.username == "newuser"
        assert user.email == email

    def test_register_user_duplicate_username(self, auth_service: AuthService, test_user: User):
        """Test registration with duplicate username"""
        email = "another@example.com"
        code = "123456"
        
        auth_service.save_verification_code(email, code)
        
        user = auth_service.register_user(
            username=test_user.username,
            email=email,
            password="password123"
        )
        
        # Should return None due to duplicate username check in service
        assert user is None

    def test_register_user_duplicate_email(self, auth_service: AuthService, test_user: User):
        """Test registration with duplicate email"""
        code = "123456"
        
        auth_service.save_verification_code(test_user.email, code)
        
        user = auth_service.register_user(
            username="newuser",
            email=test_user.email,
            password="password123"
        )
        
        # Should return None due to duplicate email check in service
        assert user is None

    def test_register_user_invalid_code(self, auth_service: AuthService):
        """Test registration with invalid verification code"""
        # Don't save any verification code
        
        # Verify code should fail
        assert auth_service.verify_email_code("newuser@example.com", "invalid") is False
        
        # Registration should still work (verification is separate from registration)
        user = auth_service.register_user(
            username="newuser",
            email="newuser@example.com",
            password="password123"
        )
        
        assert user is not None

    def test_verify_email_code_success(self, auth_service: AuthService, test_db: Session):
        """Test successful email code verification"""
        email = "test@example.com"
        code = "123456"
        
        # Save verification code
        verification = EmailVerification(
            id=str(uuid.uuid4()),
            email=email,
            code=code,
            is_used=False,
            expires_at=datetime.now() + timedelta(minutes=2)
        )
        test_db.add(verification)
        test_db.commit()
        
        # Verify code
        result = auth_service.verify_email_code(email, code)
        assert result is True
        
        # Check that code is marked as used
        test_db.refresh(verification)
        assert verification.is_used is True

    def test_verify_email_code_expired(self, auth_service: AuthService, test_db: Session):
        """Test verification with expired code"""
        email = "test@example.com"
        code = "123456"
        
        # Save expired verification code
        verification = EmailVerification(
            id=str(uuid.uuid4()),
            email=email,
            code=code,
            is_used=False,
            expires_at=datetime.now() - timedelta(minutes=1)  # Expired
        )
        test_db.add(verification)
        test_db.commit()
        
        # Verify code
        result = auth_service.verify_email_code(email, code)
        assert result is False

    def test_verify_email_code_already_used(self, auth_service: AuthService, test_db: Session):
        """Test verification with already used code"""
        email = "test@example.com"
        code = "123456"
        
        # Save used verification code
        verification = EmailVerification(
            id=str(uuid.uuid4()),
            email=email,
            code=code,
            is_used=True,  # Already used
            expires_at=datetime.now() + timedelta(minutes=2)
        )
        test_db.add(verification)
        test_db.commit()
        
        # Verify code
        result = auth_service.verify_email_code(email, code)
        assert result is False

    def test_save_verification_code(self, auth_service: AuthService, test_db: Session):
        """Test saving verification code"""
        email = "test@example.com"
        code = "123456"
        
        code_id = auth_service.save_verification_code(email, code)
        assert code_id is not None
        
        # Verify code was saved
        verification = test_db.query(EmailVerification).filter(
            EmailVerification.id == code_id
        ).first()
        assert verification is not None
        assert verification.email == email
        assert verification.code == code
        assert verification.is_used is False

    def test_check_email_rate_limit_within_limits(self, auth_service: AuthService):
        """Test email rate limit check when within limits"""
        email = "test@example.com"
        result = auth_service.check_email_rate_limit(email)
        assert result is True

    def test_check_email_rate_limit_minute_exceeded(self, auth_service: AuthService, test_db: Session):
        """Test email rate limit check when minute limit exceeded"""
        email = "test@example.com"
        
        # Add a recent verification code (within 1 minute)
        verification = EmailVerification(
            id=str(uuid.uuid4()),
            email=email,
            code="123456",
            is_used=False,
            expires_at=datetime.now() + timedelta(minutes=2),
            created_at=datetime.now()
        )
        test_db.add(verification)
        test_db.commit()
        
        result = auth_service.check_email_rate_limit(email)
        assert result is False

    def test_check_email_rate_limit_hourly_exceeded(self, auth_service: AuthService, test_db: Session):
        """Test email rate limit check when hourly limit exceeded"""
        email = "test@example.com"
        
        # Add 5 verification codes within the last hour
        for i in range(5):
            verification = EmailVerification(
                id=str(uuid.uuid4()),
                email=email,
                code=f"12345{i}",
                is_used=False,
                expires_at=datetime.now() + timedelta(minutes=2),
                created_at=datetime.now() - timedelta(minutes=i * 10)
            )
            test_db.add(verification)
        test_db.commit()
        
        result = auth_service.check_email_rate_limit(email)
        assert result is False

    def test_reset_password_success(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test successful password reset"""
        email = test_user.email
        code = "123456"
        new_password = "newpassword123"
        
        # Save verification code
        auth_service.save_verification_code(email, code)
        
        # Reset password
        success, message = auth_service.reset_password(email, code, new_password)
        
        assert success is True
        assert message == "密码重置成功"
        
        # Verify password was changed
        test_db.refresh(test_user)
        assert verify_password(new_password, test_user.hashed_password)
        assert test_user.password_version == 1

    def test_reset_password_invalid_code(self, auth_service: AuthService, test_user: User):
        """Test password reset with invalid code"""
        success, message = auth_service.reset_password(
            test_user.email,
            "invalid",
            "newpassword123"
        )
        
        assert success is False
        assert "验证码错误或已失效" in message

    def test_reset_password_nonexistent_user(self, auth_service: AuthService):
        """Test password reset for nonexistent user"""
        email = "nonexistent@example.com"
        code = "123456"
        
        # Save verification code
        auth_service.save_verification_code(email, code)
        
        success, message = auth_service.reset_password(email, code, "newpassword123")
        
        assert success is False
        assert "用户不存在" in message

    def test_generate_verification_code(self, auth_service: AuthService):
        """Test verification code generation"""
        code = auth_service.generate_verification_code()
        
        assert len(code) == 6
        assert code.isdigit()

    def test_failed_login_increments_counter(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test that failed login increments counter"""
        initial_attempts = test_user.failed_login_attempts or 0
        
        # Attempt login with wrong password
        auth_service.authenticate_user("testuser", "wrongpassword")
        
        # Check that counter was incremented
        test_db.refresh(test_user)
        assert test_user.failed_login_attempts == initial_attempts + 1

    def test_account_locks_after_5_failed_attempts(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test that account locks after 5 failed login attempts"""
        # Attempt login 5 times with wrong password
        for _ in range(5):
            auth_service.authenticate_user("testuser", "wrongpassword")
        
        # Check that account is locked
        test_db.refresh(test_user)
        assert test_user.locked_until is not None
        assert test_user.locked_until > datetime.now()

    def test_successful_login_resets_counter(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test that successful login resets failed login counter"""
        # Set failed login attempts
        test_user.failed_login_attempts = 3
        test_db.commit()
        
        # Successful login
        auth_service.authenticate_user("testuser", "password123")
        
        # Check that counter was reset
        test_db.refresh(test_user)
        assert test_user.failed_login_attempts == 0

    def test_refresh_access_token_success(self, auth_service: AuthService, test_user: User):
        """Test successful token refresh"""
        from app.core.security import create_refresh_token
        
        # Create a refresh token
        refresh_token = create_refresh_token(test_user.id)
        
        # Refresh the access token
        result = auth_service.refresh_access_token(refresh_token)
        
        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert result["user_id"] == test_user.id

    def test_refresh_access_token_invalid_token(self, auth_service: AuthService):
        """Test token refresh with invalid token"""
        with pytest.raises(ValueError):
            auth_service.refresh_access_token("invalid_token")

    def test_refresh_access_token_nonexistent_user(self, auth_service: AuthService, test_db: Session):
        """Test token refresh for nonexistent user"""
        from app.core.security import create_refresh_token
        
        # Create token for nonexistent user
        fake_user_id = str(uuid.uuid4())
        refresh_token = create_refresh_token(fake_user_id)
        
        with pytest.raises(ValueError, match="User not found"):
            auth_service.refresh_access_token(refresh_token)

    def test_send_verification_code_success(self, auth_service: AuthService, test_db: Session):
        """Test sending verification code"""
        from unittest.mock import patch
        
        with patch('app.services.email_service.send_email') as mock_send_email:
            email = "test@example.com"
            code_id = auth_service.send_verification_code(email)
            
            assert code_id is not None
            mock_send_email.assert_called_once()
            
            # Verify code was saved
            verification = test_db.query(EmailVerification).filter(
                EmailVerification.id == code_id
            ).first()
            assert verification is not None
            assert verification.email == email

    def test_send_reset_password_code_success(self, auth_service: AuthService, test_db: Session):
        """Test sending password reset code"""
        from unittest.mock import patch
        
        with patch('app.services.email_service.send_email') as mock_send_email:
            email = "test@example.com"
            code_id = auth_service.send_reset_password_code(email)
            
            assert code_id is not None
            mock_send_email.assert_called_once()
            
            # Verify code was saved
            verification = test_db.query(EmailVerification).filter(
                EmailVerification.id == code_id
            ).first()
            assert verification is not None
            assert verification.email == email

    def test_check_register_legality_ok(self, auth_service: AuthService):
        """Test registration legality check when username and email are available"""
        result = auth_service.check_register_legality("newuser", "new@example.com")
        assert result == "ok"

    def test_check_register_legality_username_exists(self, auth_service: AuthService, test_user: User):
        """Test registration legality check when username exists"""
        result = auth_service.check_register_legality(test_user.username, "new@example.com")
        assert result == "用户名已存在"

    def test_check_register_legality_email_exists(self, auth_service: AuthService, test_user: User):
        """Test registration legality check when email exists"""
        result = auth_service.check_register_legality("newuser", test_user.email)
        assert result == "该邮箱已被注册"

    def test_authenticate_user_timing_attack_protection(self, auth_service: AuthService):
        """Test that authentication has timing attack protection for nonexistent users"""
        import time
        
        # Measure time for nonexistent user
        start = time.time()
        auth_service.authenticate_user("nonexistent", "password")
        nonexistent_time = time.time() - start
        
        # Should take at least 0.1 seconds due to delay
        assert nonexistent_time >= 0.1

    def test_create_tokens_super_admin(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test token creation for super admin user"""
        test_user.is_super_admin = True
        test_db.commit()

        tokens = auth_service.create_tokens(test_user)
        assert tokens["user"]["role"] == "super_admin"
        assert tokens["user"]["is_super_admin"] is True

    def test_create_tokens_moderator(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test token creation for moderator user"""
        test_user.is_moderator = True
        test_db.commit()

        tokens = auth_service.create_tokens(test_user)
        assert tokens["user"]["role"] == "moderator"
        assert tokens["user"]["is_moderator"] is True

    def test_register_user_email_normalization(self, auth_service: AuthService, test_db: Session):
        """Test that email is normalized to lowercase during registration"""
        email = "NewUser@EXAMPLE.COM"
        code = "123456"
        
        auth_service.save_verification_code(email.lower(), code)
        auth_service.verify_email_code(email.lower(), code)
        
        user = auth_service.register_user(
            username="newuser",
            email=email,
            password="password123"
        )
        
        assert user is not None
        assert user.email == email.lower()

    def test_register_user_password_truncation(self, auth_service: AuthService, test_db: Session):
        """Test that password is truncated to 72 bytes during registration"""
        email = "newuser@example.com"
        code = "123456"
        long_password = "a" * 100
        
        auth_service.save_verification_code(email, code)
        auth_service.verify_email_code(email, code)
        
        user = auth_service.register_user(
            username="newuser",
            email=email,
            password=long_password
        )
        
        assert user is not None
        # Password should be truncated but still work
        from app.core.security import verify_password
        assert verify_password(long_password[:72], user.hashed_password)

    def test_reset_password_email_normalization(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test that email is normalized during password reset"""
        email_upper = test_user.email.upper()
        code = "123456"
        
        auth_service.save_verification_code(test_user.email, code)
        
        success, message = auth_service.reset_password(email_upper, code, "newpassword123")
        
        assert success is True

    def test_reset_password_truncates_password(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test that password is truncated during reset"""
        code = "123456"
        long_password = "b" * 100
        
        auth_service.save_verification_code(test_user.email, code)
        
        success, message = auth_service.reset_password(test_user.email, code, long_password)
        
        assert success is True
        test_db.refresh(test_user)
        from app.core.security import verify_password
        assert verify_password(long_password[:72], test_user.hashed_password)

    def test_reset_password_clears_account_lock(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test that password reset clears account lock"""
        code = "123456"
        
        # Lock the account
        test_user.locked_until = datetime.now() + timedelta(minutes=30)
        test_user.failed_login_attempts = 5
        test_db.commit()
        
        auth_service.save_verification_code(test_user.email, code)
        
        success, message = auth_service.reset_password(test_user.email, code, "newpassword123")
        
        assert success is True
        test_db.refresh(test_user)
        assert test_user.locked_until is None
        assert test_user.failed_login_attempts == 0

    def test_account_lock_expires_automatically(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test that expired account lock allows login"""
        # Set lock that has expired
        test_user.locked_until = datetime.now() - timedelta(minutes=1)
        test_user.failed_login_attempts = 5
        test_db.commit()
        
        # Should be able to login
        result = auth_service.authenticate_user("testuser", "password123")
        
        assert result is not None
        assert "access_token" in result

    def test_successful_login_clears_lock(self, auth_service: AuthService, test_user: User, test_db: Session):
        """Test that successful login clears account lock"""
        # Set lock and failed attempts
        test_user.locked_until = datetime.now() - timedelta(minutes=1)  # Expired
        test_user.failed_login_attempts = 3
        test_db.commit()
        
        # Successful login
        auth_service.authenticate_user("testuser", "password123")
        
        # Check that lock and counter were cleared
        test_db.refresh(test_user)
        assert test_user.locked_until is None
        assert test_user.failed_login_attempts == 0
