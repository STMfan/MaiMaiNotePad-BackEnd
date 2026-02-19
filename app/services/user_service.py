"""
User service module
Contains business logic for user management
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.database import User
from app.core.security import verify_password, get_password_hash

logger = logging.getLogger(__name__)


class UserService:
    """
    Service class for user management operations.
    Handles user CRUD operations and authentication logic.
    """

    def __init__(self, db: Session):
        """
        Initialize UserService with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User object if found, None otherwise
        """
        try:
            return self.db.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logger.error(f'Error getting user by ID {user_id}: {str(e)}')
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User object if found, None otherwise
        """
        try:
            return self.db.query(User).filter(User.username == username).first()
        except Exception as e:
            logger.error(f'Error getting user by username {username}: {str(e)}')
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: Email address (will be converted to lowercase)
            
        Returns:
            User object if found, None otherwise
        """
        try:
            email_lower = email.lower() if email else ""
            return self.db.query(User).filter(User.email == email_lower).first()
        except Exception as e:
            logger.error(f'Error getting user by email {email}: {str(e)}')
            return None

    def get_all_users(self) -> List[User]:
        """
        Get all users from database.
        
        Returns:
            List of User objects
        """
        try:
            return self.db.query(User).all()
        except Exception as e:
            logger.error(f'Error getting all users: {str(e)}')
            return []

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        is_admin: bool = False,
        is_moderator: bool = False,
        is_super_admin: bool = False
    ) -> Optional[User]:
        """
        Create a new user.
        
        Args:
            username: Username
            email: Email address
            password: Plain text password
            is_admin: Whether user is admin
            is_moderator: Whether user is moderator
            is_super_admin: Whether user is super admin
            
        Returns:
            Created User object if successful, None otherwise
        """
        try:
            # Check if username already exists
            if self.get_user_by_username(username):
                logger.warning(f'Username {username} already exists')
                return None

            # Check if email already exists
            email_lower = email.lower() if email else ""
            if self.get_user_by_email(email_lower):
                logger.warning(f'Email {email_lower} already exists')
                return None

            # Ensure password doesn't exceed 72 bytes (bcrypt limitation)
            password = password[:72]

            # Create new user
            new_user = User(
                id=str(uuid.uuid4()),
                username=username,
                email=email_lower,
                hashed_password=get_password_hash(password),
                is_admin=is_admin,
                is_moderator=is_moderator,
                is_super_admin=is_super_admin,
                is_active=True,
                created_at=datetime.now(),
                password_version=0
            )

            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)

            logger.info(f'User {username} created successfully')
            return new_user
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error creating user {username}: {str(e)}')
            return None

    def update_user(
        self,
        user_id: str,
        username: Optional[str] = None,
        email: Optional[str] = None
    ) -> Optional[User]:
        """
        Update user information.
        
        Args:
            user_id: User ID
            username: New username (optional)
            email: New email (optional)
            
        Returns:
            Updated User object if successful, None otherwise
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                logger.warning(f'User {user_id} not found')
                return None

            # Check if super admin username change is attempted
            if username and username != user.username and user.is_super_admin:
                logger.warning(f'Super admin username change attempted and blocked: {user.username} -> {username}')
                raise ValueError("不能修改超级管理员用户名")

            # Update username if provided
            if username and username != user.username:
                # Check if new username already exists
                existing = self.get_user_by_username(username)
                if existing and existing.id != user_id:
                    logger.warning(f'Username {username} already exists')
                    return None
                user.username = username

            # Update email if provided
            if email and email != user.email:
                email_lower = email.lower()
                # Check if new email already exists
                existing = self.get_user_by_email(email_lower)
                if existing and existing.id != user_id:
                    logger.warning(f'Email {email_lower} already exists')
                    return None
                user.email = email_lower

            self.db.commit()
            self.db.refresh(user)

            logger.info(f'User {user.username} updated successfully')
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error updating user {user_id}: {str(e)}')
            raise

    def update_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Update user password.
        
        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password
            
        Returns:
            True if successful, False otherwise
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                logger.warning(f'User {user_id} not found')
                return False

            # Verify old password
            if not verify_password(old_password, user.hashed_password):
                logger.warning(f'User {user.username} tried to update password but old password verification failed')
                return False

            # Ensure new password doesn't exceed 72 bytes (bcrypt limitation)
            new_password = new_password[:72]

            # Update password
            user.hashed_password = get_password_hash(new_password)
            # Increment password version to invalidate existing tokens
            user.password_version = (user.password_version or 0) + 1

            self.db.commit()

            logger.info(f'User {user.username} updated password successfully')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error updating password for user {user_id}: {str(e)}')
            return False

    def update_role(
        self,
        user_id: str,
        is_admin: Optional[bool] = None,
        is_moderator: Optional[bool] = None
    ) -> Optional[User]:
        """
        Update user role.
        
        Args:
            user_id: User ID
            is_admin: Whether user is admin (optional)
            is_moderator: Whether user is moderator (optional)
            
        Returns:
            Updated User object if successful, None otherwise
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                logger.warning(f'User {user_id} not found')
                return None

            if is_admin is not None:
                user.is_admin = is_admin
            if is_moderator is not None:
                user.is_moderator = is_moderator

            self.db.commit()
            self.db.refresh(user)

            logger.info(f'User {user.username} role updated successfully')
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error updating role for user {user_id}: {str(e)}')
            return None

    def verify_credentials(self, username: str, password: str) -> Optional[User]:
        """
        Verify user credentials (with timing attack protection).
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            User object if credentials are valid, None otherwise
        """
        import time
        try:
            user = self.get_user_by_username(username)

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

            # Verify real password
            if verify_password(password, user.hashed_password):
                # Login successful, reset failed login count
                self.reset_failed_login(user.id)
                return user

            # Password incorrect, add delay
            time.sleep(0.1)
            # Increment failed login count
            self.increment_failed_login(user.id)
            return None
        except Exception as e:
            logger.error(f'Error verifying user credentials: {str(e)}')
            return None

    def check_account_lock(self, user_id: str) -> bool:
        """
        Check if account is locked.
        
        Args:
            user_id: User ID
            
        Returns:
            True if account is not locked, False if locked
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            if user.locked_until and user.locked_until > datetime.now():
                return False  # Account is locked

            return True  # Account is not locked
        except Exception as e:
            logger.error(f'Error checking account lock for user {user_id}: {str(e)}')
            return False

    def increment_failed_login(self, user_id: str) -> None:
        """
        Increment failed login attempts and possibly lock account.
        
        Args:
            user_id: User ID
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return

            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            user.last_failed_login = datetime.now()

            # Lock account for 30 minutes after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now() + timedelta(minutes=30)
                logger.warning(f'Account locked: username={user.username}, attempts={user.failed_login_attempts}')

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error incrementing failed login for user {user_id}: {str(e)}')

    def reset_failed_login(self, user_id: str) -> None:
        """
        Reset failed login attempts.
        
        Args:
            user_id: User ID
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return

            if user.failed_login_attempts > 0 or user.locked_until:
                user.failed_login_attempts = 0
                user.locked_until = None
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error resetting failed login for user {user_id}: {str(e)}')

    def ensure_super_admin_exists(self) -> None:
        """
        Ensure default super admin account exists.
        Creates super admin if it doesn't exist.
        """
        try:
            # Check if super admin exists
            super_admin = self.db.query(User).filter(User.is_super_admin == True).first()
            if super_admin:
                return

            # Create super admin
            super_username = os.getenv('SUPERADMIN_USERNAME', 'superadmin')
            super_pwd = os.getenv('SUPERADMIN_PWD', 'admin123456')
            external_domain = os.getenv('EXTERNAL_DOMAIN', 'example.com')

            super_pwd = super_pwd[:72]  # bcrypt limitation

            super_admin = User(
                id=str(uuid.uuid4()),
                username=super_username,
                email=f"{super_username}@{external_domain}".lower(),
                hashed_password=get_password_hash(super_pwd),
                is_active=True,
                is_admin=False,
                is_moderator=False,
                is_super_admin=True,
                created_at=datetime.now(),
                password_version=0
            )

            self.db.add(super_admin)
            self.db.commit()

            logger.info(f'Super admin account created: {super_username}')
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error ensuring super admin exists: {str(e)}')

    def promote_to_admin(self, user_id: str, highest_pwd: str) -> bool:
        """
        Promote user to admin role.
        
        Args:
            user_id: User ID
            highest_pwd: Highest password for verification
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify highest password
            highest_password_hash = get_password_hash(os.getenv('HIGHEST_PASSWORD', ''))
            if not verify_password(highest_pwd, highest_password_hash):
                logger.error(f'User {user_id} tried to become admin but highest password verification failed')
                return False

            user = self.get_user_by_id(user_id)
            if not user:
                return False

            user.is_admin = True
            self.db.commit()

            logger.info(f'User {user.username} promoted to admin')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error promoting user {user_id} to admin: {str(e)}')
            return False

    def promote_to_moderator(self, user_id: str, highest_pwd: str) -> bool:
        """
        Promote user to moderator role.
        
        Args:
            user_id: User ID
            highest_pwd: Highest password for verification
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify highest password
            highest_password_hash = get_password_hash(os.getenv('HIGHEST_PASSWORD', ''))
            if not verify_password(highest_pwd, highest_password_hash):
                logger.error(f'User {user_id} tried to become moderator but highest password verification failed')
                return False

            user = self.get_user_by_id(user_id)
            if not user:
                return False

            user.is_moderator = True
            self.db.commit()

            logger.info(f'User {user.username} promoted to moderator')
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f'Error promoting user {user_id} to moderator: {str(e)}')
            return False
