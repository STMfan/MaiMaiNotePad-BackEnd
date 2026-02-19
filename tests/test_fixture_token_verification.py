"""Verify token generation and header injection for authentication fixtures"""
import pytest
import jwt
import os


class TestFixtureTokenVerification:
    """Verify that authentication fixtures properly generate and inject tokens"""
    
    def test_admin_client_has_valid_token(self, admin_client, admin_user, test_db):
        """Verify admin_client has a valid JWT token in headers"""
        # Check that Authorization header is set
        assert "Authorization" in admin_client.headers, \
            "Admin client should have Authorization header"
        
        auth_header = admin_client.headers["Authorization"]
        assert auth_header.startswith("Bearer "), \
            "Authorization header should start with 'Bearer '"
        
        # Extract token
        token = auth_header.replace("Bearer ", "")
        
        # Decode token (without verification for testing)
        jwt_secret = os.environ.get("JWT_SECRET_KEY", "test_secret_key_for_testing_only")
        decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        
        # Verify token contains correct user info
        assert decoded["sub"] == admin_user.id, \
            "Token should contain admin user ID"
        assert decoded["role"] == "admin", \
            "Token should have admin role"
    
    def test_moderator_client_has_valid_token(self, moderator_client, moderator_user, test_db):
        """Verify moderator_client has a valid JWT token in headers"""
        # Check that Authorization header is set
        assert "Authorization" in moderator_client.headers, \
            "Moderator client should have Authorization header"
        
        auth_header = moderator_client.headers["Authorization"]
        assert auth_header.startswith("Bearer "), \
            "Authorization header should start with 'Bearer '"
        
        # Extract token
        token = auth_header.replace("Bearer ", "")
        
        # Decode token (without verification for testing)
        jwt_secret = os.environ.get("JWT_SECRET_KEY", "test_secret_key_for_testing_only")
        decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        
        # Verify token contains correct user info
        assert decoded["sub"] == moderator_user.id, \
            "Token should contain moderator user ID"
        assert decoded["role"] == "moderator", \
            "Token should have moderator role"
    
    def test_super_admin_client_has_valid_token(self, super_admin_client, super_admin_user, test_db):
        """Verify super_admin_client has a valid JWT token in headers"""
        # Check that Authorization header is set
        assert "Authorization" in super_admin_client.headers, \
            "Super admin client should have Authorization header"
        
        auth_header = super_admin_client.headers["Authorization"]
        assert auth_header.startswith("Bearer "), \
            "Authorization header should start with 'Bearer '"
        
        # Extract token
        token = auth_header.replace("Bearer ", "")
        
        # Decode token (without verification for testing)
        jwt_secret = os.environ.get("JWT_SECRET_KEY", "test_secret_key_for_testing_only")
        decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        
        # Verify token contains correct user info
        assert decoded["sub"] == super_admin_user.id, \
            "Token should contain super admin user ID"
        assert decoded["role"] == "super_admin", \
            "Token should have super_admin role"
    
    def test_authenticated_client_has_valid_token(self, authenticated_client, test_user, test_db):
        """Verify authenticated_client has a valid JWT token in headers"""
        # Check that Authorization header is set
        assert "Authorization" in authenticated_client.headers, \
            "Authenticated client should have Authorization header"
        
        auth_header = authenticated_client.headers["Authorization"]
        assert auth_header.startswith("Bearer "), \
            "Authorization header should start with 'Bearer '"
        
        # Extract token
        token = auth_header.replace("Bearer ", "")
        
        # Decode token (without verification for testing)
        jwt_secret = os.environ.get("JWT_SECRET_KEY", "test_secret_key_for_testing_only")
        decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        
        # Verify token contains correct user info
        assert decoded["sub"] == test_user.id, \
            "Token should contain test user ID"
        assert decoded["role"] == "user", \
            "Token should have user role"
