"""
Unit tests for WebSocket utility functions

Tests connection manager, registration, removal, message sending,
broadcasting, and cleanup.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import WebSocket
from app.utils.websocket import MessageWebSocketManager
from app.models.database import Message


class TestWebSocketManagerInitialization:
    """Test WebSocket manager initialization"""
    
    def test_manager_initialization(self):
        """Test that manager initializes with empty connections"""
        manager = MessageWebSocketManager()
        assert manager.connections == {}
    
    def test_manager_connections_is_dict(self):
        """Test that connections is a dictionary"""
        manager = MessageWebSocketManager()
        assert isinstance(manager.connections, dict)


class TestConnectionRegistration:
    """Test WebSocket connection registration"""
    
    @pytest.mark.asyncio
    async def test_connect_new_user(self):
        """Test connecting a new user"""
        manager = MessageWebSocketManager()
        websocket = AsyncMock(spec=WebSocket)
        
        await manager.connect("user123", websocket)
        
        assert "user123" in manager.connections
        assert websocket in manager.connections["user123"]
        websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_multiple_connections_same_user(self):
        """Test multiple connections for same user"""
        manager = MessageWebSocketManager()
        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)
        
        await manager.connect("user123", ws1)
        await manager.connect("user123", ws2)
        
        assert len(manager.connections["user123"]) == 2
        assert ws1 in manager.connections["user123"]
        assert ws2 in manager.connections["user123"]
    
    @pytest.mark.asyncio
    async def test_connect_different_users(self):
        """Test connecting different users"""
        manager = MessageWebSocketManager()
        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)
        
        await manager.connect("user123", ws1)
        await manager.connect("user456", ws2)
        
        assert "user123" in manager.connections
        assert "user456" in manager.connections
        assert len(manager.connections) == 2


class TestConnectionRemoval:
    """Test WebSocket connection removal"""
    
    @pytest.mark.asyncio
    async def test_disconnect_existing_connection(self):
        """Test disconnecting existing connection"""
        manager = MessageWebSocketManager()
        websocket = AsyncMock(spec=WebSocket)
        
        await manager.connect("user123", websocket)
        manager.disconnect("user123", websocket)
        
        # User should be removed from connections
        assert "user123" not in manager.connections
    
    @pytest.mark.asyncio
    async def test_disconnect_one_of_multiple_connections(self):
        """Test disconnecting one connection when user has multiple"""
        manager = MessageWebSocketManager()
        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)
        
        await manager.connect("user123", ws1)
        await manager.connect("user123", ws2)
        
        manager.disconnect("user123", ws1)
        
        # User should still be in connections with ws2
        assert "user123" in manager.connections
        assert ws1 not in manager.connections["user123"]
        assert ws2 in manager.connections["user123"]
        assert len(manager.connections["user123"]) == 1
    
    @pytest.mark.asyncio
    async def test_disconnect_last_connection_removes_user(self):
        """Test that disconnecting last connection removes user"""
        manager = MessageWebSocketManager()
        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)
        
        await manager.connect("user123", ws1)
        await manager.connect("user123", ws2)
        
        manager.disconnect("user123", ws1)
        manager.disconnect("user123", ws2)
        
        # User should be completely removed
        assert "user123" not in manager.connections
    
    def test_disconnect_nonexistent_user(self):
        """Test disconnecting non-existent user doesn't raise error"""
        manager = MessageWebSocketManager()
        websocket = AsyncMock(spec=WebSocket)
        
        # Should not raise error
        manager.disconnect("nonexistent", websocket)
        
        assert "nonexistent" not in manager.connections
    
    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_websocket(self):
        """Test disconnecting non-existent websocket for existing user"""
        manager = MessageWebSocketManager()
        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)
        
        await manager.connect("user123", ws1)
        
        # Try to disconnect ws2 which was never connected
        manager.disconnect("user123", ws2)
        
        # ws1 should still be connected
        assert "user123" in manager.connections
        assert ws1 in manager.connections["user123"]


class TestMessageSending:
    """Test sending messages to single connection"""
    
    @pytest.mark.asyncio
    async def test_send_message_update_to_connected_user(self):
        """Test sending message update to connected user"""
        manager = MessageWebSocketManager()
        websocket = AsyncMock(spec=WebSocket)
        
        await manager.connect("user123", websocket)
        
        # Mock database query
        with patch('app.utils.websocket.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            
            # Mock unread count query
            mock_query = MagicMock()
            mock_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 5
            
            # Mock latest message query
            mock_query.order_by.return_value = mock_query
            mock_message = Mock()
            mock_message.to_dict = Mock(return_value={
                "id": "msg1",
                "content": "Test message"
            })
            mock_query.first.return_value = mock_message
            
            await manager.send_message_update("user123")
            
            # Verify message was sent
            websocket.send_json.assert_called_once()
            call_args = websocket.send_json.call_args[0][0]
            assert call_args["type"] == "message_update"
            assert call_args["unread"] == 5
            assert "last_message" in call_args
    
    @pytest.mark.asyncio
    async def test_send_message_update_no_connections(self):
        """Test sending message update when user has no connections"""
        manager = MessageWebSocketManager()
        
        # Should not raise error
        with patch('app.utils.websocket.get_db_context'):
            await manager.send_message_update("user123")
    
    @pytest.mark.asyncio
    async def test_send_message_update_no_latest_message(self):
        """Test sending message update when no latest message exists"""
        manager = MessageWebSocketManager()
        websocket = AsyncMock(spec=WebSocket)
        
        await manager.connect("user123", websocket)
        
        with patch('app.utils.websocket.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            
            mock_query = MagicMock()
            mock_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 0
            mock_query.order_by.return_value = mock_query
            mock_query.first.return_value = None  # No latest message
            
            await manager.send_message_update("user123")
            
            # Verify message was sent without last_message
            websocket.send_json.assert_called_once()
            call_args = websocket.send_json.call_args[0][0]
            assert call_args["type"] == "message_update"
            assert call_args["unread"] == 0
            assert "last_message" not in call_args


class TestMessageBroadcasting:
    """Test broadcasting messages to multiple connections"""
    
    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_users(self):
        """Test broadcasting to multiple users"""
        manager = MessageWebSocketManager()
        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)
        ws3 = AsyncMock(spec=WebSocket)
        
        await manager.connect("user1", ws1)
        await manager.connect("user2", ws2)
        await manager.connect("user3", ws3)
        
        with patch.object(manager, 'send_message_update', new_callable=AsyncMock) as mock_send:
            await manager.broadcast_user_update(["user1", "user2", "user3"])
            
            # Verify send_message_update was called for each user
            assert mock_send.call_count == 3
            called_users = {call[0][0] for call in mock_send.call_args_list}
            assert called_users == {"user1", "user2", "user3"}
    
    @pytest.mark.asyncio
    async def test_broadcast_deduplicates_user_ids(self):
        """Test that broadcast deduplicates user IDs"""
        manager = MessageWebSocketManager()
        
        with patch.object(manager, 'send_message_update', new_callable=AsyncMock) as mock_send:
            # Pass duplicate user IDs
            await manager.broadcast_user_update(["user1", "user1", "user2", "user2"])
            
            # Should only call once per unique user
            assert mock_send.call_count == 2
            called_users = {call[0][0] for call in mock_send.call_args_list}
            assert called_users == {"user1", "user2"}
    
    @pytest.mark.asyncio
    async def test_broadcast_filters_empty_user_ids(self):
        """Test that broadcast filters out empty user IDs"""
        manager = MessageWebSocketManager()
        
        with patch.object(manager, 'send_message_update', new_callable=AsyncMock) as mock_send:
            await manager.broadcast_user_update(["user1", "", None, "user2"])
            
            # Should only call for valid users
            assert mock_send.call_count == 2
            called_users = {call[0][0] for call in mock_send.call_args_list}
            assert called_users == {"user1", "user2"}
    
    @pytest.mark.asyncio
    async def test_broadcast_empty_list(self):
        """Test broadcasting to empty list"""
        manager = MessageWebSocketManager()
        
        with patch.object(manager, 'send_message_update', new_callable=AsyncMock) as mock_send:
            await manager.broadcast_user_update([])
            
            # Should not call send_message_update
            mock_send.assert_not_called()


class TestConnectionCleanup:
    """Test connection cleanup on errors"""
    
    @pytest.mark.asyncio
    async def test_cleanup_on_send_error(self):
        """Test that connection is cleaned up when send fails"""
        manager = MessageWebSocketManager()
        websocket = AsyncMock(spec=WebSocket)
        websocket.send_json.side_effect = Exception("Connection closed")
        
        await manager.connect("user123", websocket)
        
        with patch('app.utils.websocket.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            
            mock_query = MagicMock()
            mock_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 0
            mock_query.order_by.return_value = mock_query
            mock_query.first.return_value = None
            
            await manager.send_message_update("user123")
            
            # Connection should be removed after error
            assert "user123" not in manager.connections
    
    @pytest.mark.asyncio
    async def test_cleanup_one_failed_connection_keeps_others(self):
        """Test that only failed connection is cleaned up"""
        manager = MessageWebSocketManager()
        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)
        
        # ws1 will fail, ws2 will succeed
        ws1.send_json.side_effect = Exception("Connection closed")
        ws2.send_json.return_value = None
        
        await manager.connect("user123", ws1)
        await manager.connect("user123", ws2)
        
        with patch('app.utils.websocket.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            
            mock_query = MagicMock()
            mock_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 0
            mock_query.order_by.return_value = mock_query
            mock_query.first.return_value = None
            
            await manager.send_message_update("user123")
            
            # ws1 should be removed, ws2 should remain
            assert "user123" in manager.connections
            assert ws1 not in manager.connections["user123"]
            assert ws2 in manager.connections["user123"]
            assert len(manager.connections["user123"]) == 1


class TestGlobalManagerInstance:
    """Test global manager instance"""
    
    def test_global_manager_exists(self):
        """Test that global manager instance exists"""
        from app.utils.websocket import message_ws_manager
        
        assert message_ws_manager is not None
        assert isinstance(message_ws_manager, MessageWebSocketManager)
    
    def test_global_manager_is_singleton(self):
        """Test that global manager is a singleton"""
        from app.utils.websocket import message_ws_manager
        
        # Import again
        from app.utils.websocket import message_ws_manager as manager2
        
        # Should be the same instance
        assert message_ws_manager is manager2
