"""
Authentication service module
Contains business logic for authentication operations
"""

import uuid
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.database import User, EmailVerification
from app.core.security import (
    verify_password,
    get_password_hash,
    create_user_token,
    create_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service class for authentication operations.
    Handles login, registration, and password reset logic.
    """

    def __init__(self, db: Session):
        """
        Initialize AuthService with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with username and password.
        Includes timing attack protection and account lock checking.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Dictionary with tokens and user info if authentication successful, None otherwise
        """
        import time
        try:
            user = self.db.query(User).filter(User.username == username).first()

            # Use dummy hash verification if user doesn't exist (prevent timing attacks)
            if not user:
                dummy_hash = "$2b$12$dummy.hash.for.timing.attack.prevention.abcdefghijklmnopqrstuv"
                try:
                    verify_password(password, dummy_hash)
                except:
                    pass
                # Add random delay to further obscure timing differences
                time.sleep(0.1)
                return None

            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.now():
                logger.warning(f'Account locked: username={username}, locked_until={user.locked_until}')
                time.sleep(0.1)
                return None

            # Verify password
            if verify_password(password, user.hashed_password):
                # Login successful, reset failed login count
                self._reset_failed_login(user)
                # Return tokens and user info
                return self.create_tokens(user)

            # Password incorrect, add delay and increment failed login count
            time.sleep(0.1)
            self._increment_failed_login(user)
            return None
        except Exception as e:
            logger.error(f'Error authenticating user: {str(e)}')
            return None

    def create_tokens(self, user: User) -> Dict[str, Any]:
        """
        Create access and refresh tokens for authenticated user.
        
        Args:
            user: Authenticated User object
            
        Returns:
            Dictionary containing access_token, refresh_token, token_type, expires_in, and user info
        """
        try:
            # Determine user role
            if user.is_super_admin:
                role = "super_admin"
            elif user.is_admin:
                role = "admin"
            elif user.is_moderator:
                role = "moderator"
            else:
                role = "user"

            # Create tokens
            access_token = create_user_token(
                user_id=user.id,
                username=user.username,
                role=role,
                password_version=user.password_version or 0
            )
            refresh_token = create_refresh_token(user_id=user.id)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": role,
                    "is_admin": user.is_admin,
                    "is_moderator": user.is_moderator,
                    "is_super_admin": user.is_super_admin
                }
            }
        except Exception as e:
            logger.error(f'Error creating tokens for user {user.id}: {str(e)}')
            raise

    def register_user(
        self,
        username: str,
        password: str,
        email: str
    ) -> Optional[User]:
        """
        Register a new user (assumes email verification already done).
        
        Args:
            username: Username
            password: Plain text password
            email: Email address (should be lowercase)
            
        Returns:
            User object if successful, None otherwise
        """
        try:
            # Normalize email to lowercase
            email_lower = email.lower()
            
            # Check for duplicates
            legality_check = self.check_register_legality(username, email_lower)
            if legality_check != "ok":
                logger.warning(f'Registration failed: {legality_check}')
                return None

            # Ensure password doesn't exceed 72 bytes (bcrypt limitation)
            password = password[:72]

            # Create new user
            new_user = User(
                id=str(uuid.uuid4()),
                username=username,
                email=email_lower,
                hashed_password=get_password_hash(password),
                is_admin=False,
                is_moderator=False,
                is_super_admin=False,
                is_active=True,
                created_at=datetime.now(),
                password_version=0
            )

            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)

            logger.info(f'User registered successfully: username={username}, email={email_lower}')
            return new_user
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error registering user {username}: {str(e)}')
            return None

    def verify_email_code(self, email: str, code: str) -> bool:
        """
        Verify email verification code (unused and not expired).
        Marks the code as used if valid.
        
        Args:
            email: Email address (should be lowercase)
            code: Verification code
            
        Returns:
            True if code is valid, False otherwise
        """
        try:
            record = self.db.query(EmailVerification).filter(
                EmailVerification.email == email,
                EmailVerification.code == code,
                EmailVerification.is_used == False,
                EmailVerification.expires_at > datetime.now()
            ).first()

            if record:
                # Mark as used
                record.is_used = True
                self.db.commit()
                logger.info(f'Email verification code verified: email={email}')
                return True

            logger.warning(f'Invalid or expired verification code: email={email}')
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error verifying email code for {email}: {str(e)}')
            return False

    def save_verification_code(self, email: str, code: str) -> Optional[str]:
        """
        Save email verification code to database.
        Code expires in 2 minutes.
        
        Args:
            email: Email address (should be lowercase)
            code: Verification code
            
        Returns:
            Verification record ID if successful, None otherwise
        """
        try:
            verification = EmailVerification(
                id=str(uuid.uuid4()),
                email=email,
                code=code,
                is_used=False,
                expires_at=datetime.now() + timedelta(minutes=2)
            )
            self.db.add(verification)
            self.db.commit()
            
            logger.info(f'Verification code saved: email={email}, code_id={verification.id}')
            return verification.id
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error saving verification code for {email}: {str(e)}')
            return None

    def check_email_rate_limit(self, email: str) -> bool:
        """
        Check if email has exceeded rate limits:
        - Maximum 5 requests per hour
        - Maximum 1 request per minute
        
        Args:
            email: Email address (should be lowercase)
            
        Returns:
            True if within rate limits, False if exceeded
        """
        try:
            now = datetime.now()
            one_hour_ago = now - timedelta(hours=1)
            one_minute_ago = now - timedelta(minutes=1)

            # Check hourly limit (5 requests)
            hourly_count = self.db.query(EmailVerification).filter(
                EmailVerification.email == email,
                EmailVerification.created_at > one_hour_ago
            ).count()
            
            if hourly_count >= 5:
                logger.warning(f'Email rate limit exceeded (hourly): email={email}, count={hourly_count}')
                return False

            # Check minute limit (1 request)
            minute_count = self.db.query(EmailVerification).filter(
                EmailVerification.email == email,
                EmailVerification.created_at > one_minute_ago
            ).count()
            
            if minute_count >= 1:
                logger.warning(f'Email rate limit exceeded (minute): email={email}')
                return False

            return True
        except Exception as e:
            logger.error(f'Error checking email rate limit for {email}: {str(e)}')
            return False

    def reset_password(
        self,
        email: str,
        verification_code: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Reset user password with email verification.
        
        Args:
            email: Email address
            verification_code: Email verification code
            new_password: New plain text password
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Normalize email to lowercase
            email_lower = email.lower()

            # Verify email code
            if not self.verify_email_code(email_lower, verification_code):
                return False, "验证码错误或已失效"

            # Find user by email
            user = self.db.query(User).filter(User.email == email_lower).first()
            if not user:
                return False, "用户不存在"

            # Ensure password doesn't exceed 72 bytes (bcrypt limitation)
            new_password = new_password[:72]

            # Update password and increment password version
            user.hashed_password = get_password_hash(new_password)
            user.password_version = (user.password_version or 0) + 1

            # Reset failed login attempts
            user.failed_login_attempts = 0
            user.locked_until = None

            self.db.commit()

            logger.info(f'Password reset successfully: username={user.username}, email={email_lower}')
            return True, "密码重置成功"
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error resetting password for {email}: {str(e)}')
            return False, "密码重置失败"

    def generate_verification_code(self) -> str:
        """
        Generate a 6-digit verification code.
        
        Returns:
            6-digit verification code as string
        """
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    def send_verification_code(self, email: str) -> Optional[str]:
        """
        Generate and save verification code for email registration.
        
        Args:
            email: Email address (should be lowercase)
            
        Returns:
            Verification record ID if successful, None otherwise
        """
        try:
            code = self.generate_verification_code()
            code_id = self.save_verification_code(email, code)
            
            if code_id:
                # Send email with verification code
                from app.services.email_service import send_email
                subject = "MaiMaiNotePad 注册验证码"
                body = f"您的验证码是: {code}\n\n验证码将在2分钟后过期。"
                send_email(email, subject, body)
                
            return code_id
        except Exception as e:
            logger.error(f'Error sending verification code to {email}: {str(e)}')
            raise

    def send_reset_password_code(self, email: str) -> Optional[str]:
        """
        Generate and save verification code for password reset.
        
        Args:
            email: Email address (should be lowercase)
            
        Returns:
            Verification record ID if successful, None otherwise
        """
        try:
            code = self.generate_verification_code()
            code_id = self.save_verification_code(email, code)
            
            if code_id:
                # Send email with verification code
                from app.services.email_service import send_email
                subject = "MaiMaiNotePad 重置密码验证码"
                body = f"您的重置密码验证码是: {code}\n\n验证码将在2分钟后过期。"
                send_email(email, subject, body)
                
            return code_id
        except Exception as e:
            logger.error(f'Error sending reset password code to {email}: {str(e)}')
            raise

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dictionary containing new access_token and user info
        """
        from app.core.security import verify_token, create_user_token
        
        try:
            # Verify refresh token
            payload = verify_token(refresh_token)
            if not payload:
                raise ValueError("Invalid refresh token")
            
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Invalid token payload")
            
            # Get user from database
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # Determine user role
            if user.is_super_admin:
                role = "super_admin"
            elif user.is_admin:
                role = "admin"
            elif user.is_moderator:
                role = "moderator"
            else:
                role = "user"
            
            # Create new access token
            access_token = create_user_token(
                user_id=user.id,
                username=user.username,
                role=role,
                password_version=user.password_version or 0
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user_id": user.id
            }
        except Exception as e:
            logger.error(f'Error refreshing access token: {str(e)}')
            raise

    def check_register_legality(self, username: str, email: str) -> str:
        """
        Check if username and email are available for registration.
        
        Args:
            username: Username
            email: Email address (should be lowercase)
            
        Returns:
            "ok" if available, error message otherwise
        """
        try:
            # Check if username exists
            user = self.db.query(User).filter(User.username == username).first()
            if user:
                return "用户名已存在"

            # Check if email exists
            user = self.db.query(User).filter(User.email == email).first()
            if user:
                return "该邮箱已被注册"

            return "ok"
        except Exception as e:
            logger.error(f'Error checking registration legality: {str(e)}')
            return "系统错误"

    def _increment_failed_login(self, user: User) -> None:
        """
        Increment failed login attempts and possibly lock account.
        Account is locked for 30 minutes after 5 failed attempts.
        
        Args:
            user: User object
        """
        try:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            user.last_failed_login = datetime.now()

            # Lock account for 30 minutes after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now() + timedelta(minutes=30)
                logger.warning(
                    f'Account locked due to failed login attempts: '
                    f'username={user.username}, attempts={user.failed_login_attempts}'
                )

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error incrementing failed login for user {user.id}: {str(e)}')

    def _reset_failed_login(self, user: User) -> None:
        """
        Reset failed login attempts after successful login.
        
        Args:
            user: User object
        """
        try:
            if user.failed_login_attempts > 0 or user.locked_until:
                user.failed_login_attempts = 0
                user.locked_until = None
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error resetting failed login for user {user.id}: {str(e)}')
