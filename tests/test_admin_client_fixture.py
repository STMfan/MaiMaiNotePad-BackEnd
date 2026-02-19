"""Test admin_client fixture authentication"""
import pytest


class TestAdminClientFixture:
    """Test that admin_client fixture works correctly"""
    
    def test_admin_client_authentication(self, admin_client, test_db):
        """Test that admin_client can authenticate and access admin endpoints"""
        # Try to access an admin endpoint
        response = admin_client.get("/api/admin/stats")
        
        # Should succeed (200) or return 404 if endpoint doesn't exist
        # Should NOT return 401 (unauthorized) or 403 (forbidden)
        assert response.status_code in [200, 404], \
            f"Admin client should be authenticated, got status {response.status_code}"
    
    def test_moderator_client_authentication(self, moderator_client, test_db):
        """Test that moderator_client can authenticate"""
        # Try to access a review endpoint (moderator-only)
        response = moderator_client.get("/api/review/knowledge")
        
        # Should succeed (200) or return 404 if no pending items
        # Should NOT return 401 (unauthorized) or 403 (forbidden)
        assert response.status_code in [200, 404], \
            f"Moderator client should be authenticated, got status {response.status_code}"
    
    def test_super_admin_client_authentication(self, super_admin_client, test_db):
        """Test that super_admin_client can authenticate"""
        # Try to access an admin endpoint
        response = super_admin_client.get("/api/admin/stats")
        
        # Should succeed (200) or return 404 if endpoint doesn't exist
        # Should NOT return 401 (unauthorized) or 403 (forbidden)
        assert response.status_code in [200, 404], \
            f"Super admin client should be authenticated, got status {response.status_code}"
    
    def test_regular_user_cannot_access_admin(self, authenticated_client, test_db):
        """Test that regular authenticated user cannot access admin endpoints"""
        # Try to access an admin endpoint with regular user
        response = authenticated_client.get("/api/admin/stats")
        
        # Should return 403 (forbidden) or 404 (not found) for regular users
        # Should NOT return 200 (success)
        assert response.status_code in [403, 404], \
            f"Regular user should not have full access to admin endpoints, got status {response.status_code}"
