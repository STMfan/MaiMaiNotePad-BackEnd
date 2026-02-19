"""
AuthHelper for authentication testing
Provides helper methods for creating authenticated test clients with different user roles
"""

from typing import Optional, Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.database import User
from app.core.security import create_user_token


class AuthHelper:
    """Helper for managing authentication in integration tests"""
    
    def __init__(self, client: TestClient, db: Session):
        """
        Initialize the AuthHelper
        
        Args:
            client: FastAPI TestClient instance
            db: SQLAlchemy database session
        """
        self.client = client
        self.db = db
    
    def get_auth_headers(self, user: User) -> Dict[str, str]:
        """
        Generate authentication headers for a user
        
        Args:
            user: User instance to generate token for
        
        Returns:
            Dictionary with Authorization header
        """
        # Determine user role
        if user.is_super_admin:
            role = "super_admin"
        elif user.is_admin:
            role = "admin"
        elif user.is_moderator:
            role = "moderator"
        else:
            role = "user"
        
        # Create token
        token = create_user_token(
            user_id=user.id,
            username=user.username,
            role=role,
            password_version=user.password_version
        )
        
        return {"Authorization": f"Bearer {token}"}
    
    def create_authenticated_client(self, user: User) -> TestClient:
        """
        Create an authenticated test client for a specific user
        
        Args:
            user: User instance to authenticate as
        
        Returns:
            TestClient with authentication headers set
        """
        headers = self.get_auth_headers(user)
        self.client.headers.update(headers)
        return self.client
    
    def create_user_client(self, user: Optional[User] = None) -> TestClient:
        """
        Create an authenticated test client for a regular user
        
        Args:
            user: Optional User instance (will be created if not provided)
        
        Returns:
            TestClient authenticated as a regular user
        """
        from tests.test_data_factory import TestDataFactory
        
        if user is None:
            factory = TestDataFactory(self.db)
            user = factory.create_user(
                is_admin=False,
                is_moderator=False,
                is_super_admin=False
            )
        
        return self.create_authenticated_client(user)
    
    def create_admin_client(self, user: Optional[User] = None) -> TestClient:
        """
        Create an authenticated test client for an admin user
        
        Args:
            user: Optional User instance (will be created if not provided)
        
        Returns:
            TestClient authenticated as an admin
        """
        from tests.test_data_factory import TestDataFactory
        
        if user is None:
            factory = TestDataFactory(self.db)
            user = factory.create_user(
                is_admin=True,
                is_moderator=False,
                is_super_admin=False
            )
        
        return self.create_authenticated_client(user)
    
    def create_moderator_client(self, user: Optional[User] = None) -> TestClient:
        """
        Create an authenticated test client for a moderator user
        
        Args:
            user: Optional User instance (will be created if not provided)
        
        Returns:
            TestClient authenticated as a moderator
        """
        from tests.test_data_factory import TestDataFactory
        
        if user is None:
            factory = TestDataFactory(self.db)
            user = factory.create_user(
                is_admin=False,
                is_moderator=True,
                is_super_admin=False
            )
        
        return self.create_authenticated_client(user)
    
    def create_super_admin_client(self, user: Optional[User] = None) -> TestClient:
        """
        Create an authenticated test client for a super admin user
        
        Args:
            user: Optional User instance (will be created if not provided)
        
        Returns:
            TestClient authenticated as a super admin
        """
        from tests.test_data_factory import TestDataFactory
        
        if user is None:
            factory = TestDataFactory(self.db)
            user = factory.create_user(
                is_admin=True,
                is_moderator=True,
                is_super_admin=True
            )
        
        return self.create_authenticated_client(user)
    
    def clear_auth(self) -> None:
        """
        Clear authentication headers from the client
        """
        self.client.headers.pop("Authorization", None)
