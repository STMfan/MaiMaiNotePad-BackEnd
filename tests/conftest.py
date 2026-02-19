import pytest
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from hypothesis import settings, Verbosity, HealthCheck

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure hypothesis profiles for property-based testing
# CI profile: 100 iterations with verbose output for detailed test results
settings.register_profile(
    "ci",
    max_examples=100,
    verbosity=Verbosity.verbose,
    deadline=None,  # Disable deadline for CI to avoid flaky tests
    suppress_health_check=[HealthCheck.too_slow]
)

# Development profile: 10 iterations for faster feedback during development
settings.register_profile(
    "dev",
    max_examples=10,
    verbosity=Verbosity.normal,
    deadline=None
)

# Default profile: Use CI profile to ensure minimum 100 iterations
# Can be overridden with HYPOTHESIS_PROFILE environment variable
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "ci"))

# Set test environment variables
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_for_testing_only")
os.environ.setdefault("MAIL_USER", "test@example.com")
os.environ.setdefault("MAIL_PWD", "test_password")
os.environ.setdefault("SUPERADMIN_PWD", "admin123")
os.environ.setdefault("HIGHEST_PASSWORD", "highest123")

# Import after setting environment variables
from app.models.database import (
    Base, User, EmailVerification, KnowledgeBase, KnowledgeBaseFile,
    PersonaCard, PersonaCardFile, Message, StarRecord, UploadRecord,
    DownloadRecord, Comment, CommentReaction
)
from app.core.database import get_db
from app.core.security import get_password_hash
from tests.test_data_factory import TestDataFactory

SQLALCHEMY_DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_db() -> Session:
    """Create a test database session"""
    # Use a simple session without transaction isolation for integration tests
    session = TestingSessionLocal()
    
    yield session
    
    # Clean up all data after test (in reverse order of foreign key dependencies)
    session.query(CommentReaction).delete()
    session.query(Comment).delete()
    session.query(DownloadRecord).delete()
    session.query(UploadRecord).delete()
    session.query(EmailVerification).delete()
    session.query(StarRecord).delete()
    session.query(Message).delete()
    session.query(PersonaCardFile).delete()
    session.query(PersonaCard).delete()
    session.query(KnowledgeBaseFile).delete()
    session.query(KnowledgeBase).delete()
    session.query(User).delete()
    session.commit()
    session.close()


@pytest.fixture(scope="function")
def factory(test_db: Session):
    """Create a TestDataFactory instance"""
    return TestDataFactory(test_db)


@pytest.fixture(scope="function")
def test_user(test_db: Session):
    """Create a test user"""
    user = User(
        id=str(uuid.uuid4()),
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
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


@pytest.fixture(scope="function")
def admin_user(test_db: Session):
    """Create a test admin user"""
    user = User(
        id=str(uuid.uuid4()),
        username="adminuser",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        is_active=True,
        is_admin=True,
        is_moderator=False,
        is_super_admin=False,
        created_at=datetime.now(),
        password_version=0
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def moderator_user(test_db: Session):
    """Create a test moderator user"""
    user = User(
        id=str(uuid.uuid4()),
        username="moderatoruser",
        email="moderator@example.com",
        hashed_password=get_password_hash("moderatorpassword123"),
        is_active=True,
        is_admin=False,
        is_moderator=True,
        is_super_admin=False,
        created_at=datetime.now(),
        password_version=0
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def super_admin_user(test_db: Session):
    """Create a test super admin user"""
    user = User(
        id=str(uuid.uuid4()),
        username="superadminuser",
        email="superadmin@example.com",
        hashed_password=get_password_hash("superadminpassword123"),
        is_active=True,
        is_admin=True,
        is_moderator=True,
        is_super_admin=True,
        created_at=datetime.now(),
        password_version=0
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


# Only import app if it exists (for integration tests)
try:
    from app.main import app
    
    app.dependency_overrides[get_db] = override_get_db
    _test_client = TestClient(app)
    
    @pytest.fixture(scope="function")
    def client():
        """Create unauthenticated test client"""
        return TestClient(app)
    
    @pytest.fixture(scope="function")
    def authenticated_client(test_user):
        """Create authenticated test client"""
        # Login to get token
        response = _test_client.post(
            "/api/auth/token",
            data={"username": "testuser", "password": "testpassword123"}
        )
        
        # Check if login was successful
        if response.status_code != 200:
            raise Exception(f"Login failed: {response.status_code} - {response.text}")
        
        resp_data = response.json()
        
        # Handle both response formats (with and without "data" wrapper)
        if "data" in resp_data:
            token = resp_data["data"]["access_token"]
        else:
            token = resp_data["access_token"]
        
        # Create client with auth header
        _test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield _test_client
        
        # Cleanup auth header
        _test_client.headers.pop("Authorization", None)
    
    @pytest.fixture(scope="function")
    def admin_client(admin_user):
        """Create authenticated admin test client"""
        # Login to get token
        response = _test_client.post(
            "/api/auth/token",
            data={"username": "adminuser", "password": "adminpassword123"}
        )
        
        # Check if login was successful
        if response.status_code != 200:
            raise Exception(f"Admin login failed: {response.status_code} - {response.text}")
        
        resp_data = response.json()
        
        # Handle both response formats (with and without "data" wrapper)
        if "data" in resp_data:
            token = resp_data["data"]["access_token"]
        else:
            token = resp_data["access_token"]
        
        # Create client with auth header
        _test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield _test_client
        
        # Cleanup auth header
        _test_client.headers.pop("Authorization", None)
    
    @pytest.fixture(scope="function")
    def moderator_client(moderator_user):
        """Create authenticated moderator test client"""
        # Login to get token
        response = _test_client.post(
            "/api/auth/token",
            data={"username": "moderatoruser", "password": "moderatorpassword123"}
        )
        
        # Check if login was successful
        if response.status_code != 200:
            raise Exception(f"Moderator login failed: {response.status_code} - {response.text}")
        
        resp_data = response.json()
        
        # Handle both response formats (with and without "data" wrapper)
        if "data" in resp_data:
            token = resp_data["data"]["access_token"]
        else:
            token = resp_data["access_token"]
        
        # Create client with auth header
        _test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield _test_client
        
        # Cleanup auth header
        _test_client.headers.pop("Authorization", None)
    
    @pytest.fixture(scope="function")
    def super_admin_client(super_admin_user):
        """Create authenticated super admin test client"""
        # Login to get token
        response = _test_client.post(
            "/api/auth/token",
            data={"username": "superadminuser", "password": "superadminpassword123"}
        )
        
        # Check if login was successful
        if response.status_code != 200:
            raise Exception(f"Super admin login failed: {response.status_code} - {response.text}")
        
        resp_data = response.json()
        
        # Handle both response formats (with and without "data" wrapper)
        if "data" in resp_data:
            token = resp_data["data"]["access_token"]
        else:
            token = resp_data["access_token"]
        
        # Create client with auth header
        _test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield _test_client
        
        # Cleanup auth header
        _test_client.headers.pop("Authorization", None)
except ImportError:
    # App not available, skip integration test fixtures
    pass


# Helper function for checking error responses
def assert_error_response(response, expected_status_codes, expected_message_keywords):
    """
    Helper function to check error responses from API.
    Handles both FastAPI validation errors (422 with 'detail') and custom API errors (with 'error').
    
    Args:
        response: The response object from TestClient
        expected_status_codes: int or list of ints for expected status codes
        expected_message_keywords: str or list of str - keywords that should appear in error message
    """
    # Normalize inputs to lists
    if isinstance(expected_status_codes, int):
        expected_status_codes = [expected_status_codes]
    if isinstance(expected_message_keywords, str):
        expected_message_keywords = [expected_message_keywords]
    
    # Check status code
    assert response.status_code in expected_status_codes, \
        f"Expected status code in {expected_status_codes}, got {response.status_code}"
    
    data = response.json()
    
    # Handle FastAPI validation errors (422)
    if "detail" in data:
        # FastAPI validation error format: {"detail": [...]}
        detail = data["detail"]
        if isinstance(detail, list):
            # Extract all error messages
            error_messages = []
            for error in detail:
                if isinstance(error, dict):
                    error_messages.append(error.get("msg", ""))
                    error_messages.append(str(error.get("loc", "")))
            combined_message = " ".join(error_messages).lower()
        else:
            combined_message = str(detail).lower()
        
        # Check if any keyword matches
        keyword_found = any(
            keyword.lower() in combined_message 
            for keyword in expected_message_keywords
        )
        
        assert keyword_found, \
            f"Expected one of {expected_message_keywords} in error message, got: {data}"
    
    # Handle custom API errors
    elif "error" in data:
        # Custom error format: {"success": False, "error": {"message": "..."}}
        error_message = data["error"].get("message", "").lower()
        
        # Check if any keyword matches
        keyword_found = any(
            keyword.lower() in error_message 
            for keyword in expected_message_keywords
        )
        
        assert keyword_found, \
            f"Expected one of {expected_message_keywords} in error message, got: {error_message}"
    
    else:
        # Unknown error format
        raise AssertionError(f"Unknown error response format: {data}")
