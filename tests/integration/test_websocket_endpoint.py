"""
Integration tests for WebSocket endpoint

Tests the message_websocket_endpoint function for real-time messaging.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, AsyncMock

from app.main import app
from app.models.database import User


class TestWebSocketEndpoint:
    """Test WebSocket endpoint functionality"""

    def test_websocket_connection_with_valid_token(self, test_user):
        """Test WebSocket connection with valid JWT token"""
        # Generate token
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(test_user.id)})
        
        # Connect to WebSocket
        client = TestClient(app)
        with client.websocket_connect(f"/api/ws/{token}") as websocket:
            # Connection should be established
            # Send a message to keep connection alive
            websocket.send_text("ping")
            
            # Close connection
            websocket.close()

    def test_websocket_connection_with_invalid_token(self):
        """Test WebSocket connection with invalid token"""
        client = TestClient(app)
        
        # Try to connect with invalid token
        with pytest.raises(Exception):
            with client.websocket_connect("/api/ws/invalid_token"):
                pass

    def test_websocket_connection_without_token(self):
        """Test WebSocket connection without token"""
        client = TestClient(app)
        
        # Try to connect without token (should fail at routing level)
        with pytest.raises(Exception):
            with client.websocket_connect("/api/ws/"):
                pass

    def test_websocket_disconnect_cleanup(self, test_user):
        """Test that WebSocket disconnection cleans up resources"""
        # Generate token
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(test_user.id)})
        
        # Connect and disconnect
        client = TestClient(app)
        with client.websocket_connect(f"/api/ws/{token}") as websocket:
            websocket.send_text("ping")
        
        # Verify connection is cleaned up
        from app.utils.websocket import message_ws_manager
        assert str(test_user.id) not in message_ws_manager.connections or \
               len(message_ws_manager.connections[str(test_user.id)]) == 0

    @patch('app.api.websocket.message_ws_manager.send_message_update')
    def test_websocket_sends_initial_message_update(self, mock_send_update, test_user):
        """Test that WebSocket sends initial message update on connection"""
        # Generate token
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(test_user.id)})
        
        # Make send_message_update async
        mock_send_update.return_value = AsyncMock()
        
        # Connect to WebSocket
        client = TestClient(app)
        with client.websocket_connect(f"/api/ws/{token}") as websocket:
            websocket.send_text("ping")
        
        # Verify initial message update was sent
        mock_send_update.assert_called_once_with(str(test_user.id))

    def test_websocket_connection_with_expired_token(self, test_user):
        """Test WebSocket connection with expired token"""
        # Generate expired token (negative expiration)
        from app.core.security import create_access_token
        from datetime import timedelta
        token = create_access_token({"sub": str(test_user.id)}, expires_delta=timedelta(seconds=-1))
        
        # Try to connect with expired token
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/ws/{token}"):
                pass

    def test_websocket_connection_with_malformed_token(self):
        """Test WebSocket connection with malformed token"""
        client = TestClient(app)
        
        # Try to connect with malformed token
        with pytest.raises(Exception):
            with client.websocket_connect("/api/ws/not.a.valid.jwt"):
                pass

    def test_websocket_connection_with_missing_user_id(self):
        """Test WebSocket connection with token missing user ID"""
        # Generate token without user ID
        from app.core.security import create_access_token
        token = create_access_token({"other_field": "value"})
        
        # Try to connect
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/ws/{token}"):
                pass

    def test_websocket_handles_client_disconnect(self, test_user):
        """Test that WebSocket handles client disconnect gracefully"""
        # Generate token
        from app.core.security import create_access_token
        token = create_access_token({"sub": str(test_user.id)})
        
        # Connect and abruptly close
        client = TestClient(app)
        with client.websocket_connect(f"/api/ws/{token}") as websocket:
            # Simulate client disconnect by closing without proper cleanup
            pass
        
        # Verify connection is cleaned up
        from app.utils.websocket import message_ws_manager
        assert str(test_user.id) not in message_ws_manager.connections or \
               len(message_ws_manager.connections[str(test_user.id)]) == 0
