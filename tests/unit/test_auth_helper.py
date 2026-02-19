"""
Unit tests for AuthHelper
Tests the authentication helper methods for generating authenticated clients
"""

import pytest
from tests.auth_helper import AuthHelper
from tests.test_data_factory import TestDataFactory


def test_get_auth_headers_regular_user(test_db, factory):
    """Test generating auth headers for a regular user"""
    user = factory.create_user(
        username="regularuser",
        is_admin=False,
        is_moderator=False,
        is_super_admin=False
    )
    
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        
        headers = auth_helper.get_auth_headers(user)
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert len(headers["Authorization"]) > 20  # Token should be reasonably long
    except ImportError:
        pytest.skip("App not available")


def test_get_auth_headers_admin_user(test_db, factory):
    """Test generating auth headers for an admin user"""
    user = factory.create_user(
        username="adminuser",
        is_admin=True,
        is_moderator=False,
        is_super_admin=False
    )
    
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        
        headers = auth_helper.get_auth_headers(user)
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
    except ImportError:
        pytest.skip("App not available")


def test_get_auth_headers_moderator_user(test_db, factory):
    """Test generating auth headers for a moderator user"""
    user = factory.create_user(
        username="moderatoruser",
        is_admin=False,
        is_moderator=True,
        is_super_admin=False
    )
    
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        
        headers = auth_helper.get_auth_headers(user)
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
    except ImportError:
        pytest.skip("App not available")


def test_get_auth_headers_super_admin_user(test_db, factory):
    """Test generating auth headers for a super admin user"""
    user = factory.create_user(
        username="superadminuser",
        is_admin=True,
        is_moderator=True,
        is_super_admin=True
    )
    
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        
        headers = auth_helper.get_auth_headers(user)
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
    except ImportError:
        pytest.skip("App not available")


def test_create_authenticated_client(test_db, factory):
    """Test creating an authenticated client for a specific user"""
    user = factory.create_user(username="testuser")
    
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        
        authenticated_client = auth_helper.create_authenticated_client(user)
        
        assert "Authorization" in authenticated_client.headers
        assert authenticated_client.headers["Authorization"].startswith("Bearer ")
    except ImportError:
        pytest.skip("App not available")


def test_create_user_client(test_db):
    """Test creating an authenticated client for a regular user"""
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        
        user_client = auth_helper.create_user_client()
        
        assert "Authorization" in user_client.headers
        assert user_client.headers["Authorization"].startswith("Bearer ")
    except ImportError:
        pytest.skip("App not available")


def test_create_admin_client(test_db):
    """Test creating an authenticated client for an admin user"""
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        
        admin_client = auth_helper.create_admin_client()
        
        assert "Authorization" in admin_client.headers
        assert admin_client.headers["Authorization"].startswith("Bearer ")
    except ImportError:
        pytest.skip("App not available")


def test_create_moderator_client(test_db):
    """Test creating an authenticated client for a moderator user"""
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        
        moderator_client = auth_helper.create_moderator_client()
        
        assert "Authorization" in moderator_client.headers
        assert moderator_client.headers["Authorization"].startswith("Bearer ")
    except ImportError:
        pytest.skip("App not available")


def test_create_super_admin_client(test_db):
    """Test creating an authenticated client for a super admin user"""
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        
        super_admin_client = auth_helper.create_super_admin_client()
        
        assert "Authorization" in super_admin_client.headers
        assert super_admin_client.headers["Authorization"].startswith("Bearer ")
    except ImportError:
        pytest.skip("App not available")


def test_clear_auth(test_db, factory):
    """Test clearing authentication headers"""
    user = factory.create_user(username="testuser")
    
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        
        # Set auth headers
        auth_helper.create_authenticated_client(user)
        assert "Authorization" in client.headers
        
        # Clear auth headers
        auth_helper.clear_auth()
        assert "Authorization" not in client.headers
    except ImportError:
        pytest.skip("App not available")


def test_create_user_client_with_existing_user(test_db, factory):
    """Test creating an authenticated client with an existing user"""
    user = factory.create_user(
        username="existinguser",
        is_admin=False,
        is_moderator=False,
        is_super_admin=False
    )
    
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        
        user_client = auth_helper.create_user_client(user)
        
        assert "Authorization" in user_client.headers
        assert user_client.headers["Authorization"].startswith("Bearer ")
    except ImportError:
        pytest.skip("App not available")


def test_create_admin_client_with_existing_user(test_db, factory):
    """Test creating an authenticated admin client with an existing user"""
    user = factory.create_user(
        username="existingadmin",
        is_admin=True,
        is_moderator=False,
        is_super_admin=False
    )
    
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        auth_helper = AuthHelper(client, test_db)
        
        admin_client = auth_helper.create_admin_client(user)
        
        assert "Authorization" in admin_client.headers
        assert admin_client.headers["Authorization"].startswith("Bearer ")
    except ImportError:
        pytest.skip("App not available")
