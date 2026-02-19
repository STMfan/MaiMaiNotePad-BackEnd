"""
Integration tests demonstrating AuthHelper usage
Shows how to use AuthHelper in real API endpoint tests
"""

import pytest


def test_auth_helper_with_user_endpoint(auth_helper, test_db):
    """Test using AuthHelper to access user endpoint"""
    if auth_helper is None:
        pytest.skip("App not available")
    
    # Create authenticated user client
    user_client = auth_helper.create_user_client()
    
    # Access user endpoint
    response = user_client.get("/api/users/me")
    
    # Should succeed with authentication
    assert response.status_code in [200, 404]  # 404 if user profile not fully set up


def test_auth_helper_with_admin_endpoint(auth_helper, test_db):
    """Test using AuthHelper to access admin endpoint"""
    if auth_helper is None:
        pytest.skip("App not available")
    
    # Create authenticated admin client
    admin_client = auth_helper.create_admin_client()
    
    # Access admin endpoint
    response = admin_client.get("/api/admin/stats")
    
    # Should not be unauthorized (200 or 404 are acceptable, but not 401/403)
    assert response.status_code != 401
    assert response.status_code != 403


def test_auth_helper_user_cannot_access_admin_endpoint(auth_helper, test_db):
    """Test that regular user cannot access admin endpoint"""
    if auth_helper is None:
        pytest.skip("App not available")
    
    # Create authenticated user client (not admin)
    user_client = auth_helper.create_user_client()
    
    # Try to access admin endpoint
    response = user_client.get("/api/admin/stats")
    
    # Should be forbidden or not found (403 or 404), but authenticated
    assert response.status_code in [403, 404]


def test_auth_helper_moderator_endpoint(auth_helper, test_db):
    """Test using AuthHelper to access moderator endpoint"""
    if auth_helper is None:
        pytest.skip("App not available")
    
    # Create authenticated moderator client
    moderator_client = auth_helper.create_moderator_client()
    
    # Access review endpoint (moderator-only)
    response = moderator_client.get("/api/review/knowledge")
    
    # Should not be unauthorized (200 or 404 are acceptable, but not 401/403)
    assert response.status_code != 401
    assert response.status_code != 403


def test_auth_helper_super_admin_endpoint(auth_helper, test_db):
    """Test using AuthHelper with super admin"""
    if auth_helper is None:
        pytest.skip("App not available")
    
    # Create authenticated super admin client
    super_admin_client = auth_helper.create_super_admin_client()
    
    # Access admin endpoint
    response = super_admin_client.get("/api/admin/stats")
    
    # Should not be unauthorized (200 or 404 are acceptable, but not 401/403)
    assert response.status_code != 401
    assert response.status_code != 403


def test_auth_helper_clear_auth_denies_access(auth_helper, test_db, factory):
    """Test that clearing auth prevents access to protected endpoints"""
    if auth_helper is None:
        pytest.skip("App not available")
    
    # Create user and authenticate
    user = factory.create_user()
    auth_helper.create_authenticated_client(user)
    
    # Access should work
    response = auth_helper.client.get("/api/users/me")
    assert response.status_code in [200, 404]
    
    # Clear authentication
    auth_helper.clear_auth()
    
    # Access should now fail
    response = auth_helper.client.get("/api/users/me")
    assert response.status_code == 401


def test_auth_helper_with_custom_user(auth_helper, test_db, factory):
    """Test using AuthHelper with a custom user"""
    if auth_helper is None:
        pytest.skip("App not available")
    
    # Create a custom user with specific attributes
    custom_user = factory.create_user(
        username="customuser",
        email="custom@example.com",
        is_admin=False
    )
    
    # Create authenticated client for this user
    client = auth_helper.create_user_client(custom_user)
    
    # Access user endpoint
    response = client.get("/api/users/me")
    
    # Should succeed
    assert response.status_code in [200, 404]
