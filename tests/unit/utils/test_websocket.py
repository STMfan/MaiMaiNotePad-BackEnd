"""
app/utils/websocket.py 单元测试

测试WebSocket连接管理和消息广播。
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import WebSocket

from app.utils.websocket import MessageWebSocketManager, message_ws_manager

# Mark all tests in this file as serial to avoid WebSocket state conflicts
pytestmark = pytest.mark.serial


class TestMessageWebSocketManager:
    """Tests for MessageWebSocketManager class"""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh WebSocket manager for each test"""
        return MessageWebSocketManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection"""
        ws = Mock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        return ws
    
    @pytest.mark.asyncio
    async def test_connect_new_user(self, manager, mock_websocket):
        """Test connecting a new user creates connection list"""
        user_id = "user123"
        
        await manager.connect(user_id, mock_websocket)
        
        assert user_id in manager.connections
        assert mock_websocket in manager.connections[user_id]
        assert len(manager.connections[user_id]) == 1
        mock_websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_multiple_connections_same_user(self, manager, mock_websocket):
        """Test same user can have multiple concurrent connections"""
        user_id = "user123"
        ws2 = Mock(spec=WebSocket)
        ws2.accept = AsyncMock()
        
        await manager.connect(user_id, mock_websocket)
        await manager.connect(user_id, ws2)
        
        assert len(manager.connections[user_id]) == 2
        assert mock_websocket in manager.connections[user_id]
        assert ws2 in manager.connections[user_id]
    
    @pytest.mark.asyncio
    async def test_connect_converts_user_id_to_string(self, manager, mock_websocket):
        """Test user_id is converted to string for consistency"""
        user_id = 12345  # Integer user ID
        
        await manager.connect(user_id, mock_websocket)
        
        assert "12345" in manager.connections
        assert mock_websocket in manager.connections["12345"]
    
    def test_disconnect_removes_connection(self, manager, mock_websocket):
        """Test disconnecting removes specific connection"""
        user_id = "user123"
        manager.connections[user_id] = [mock_websocket]
        
        manager.disconnect(user_id, mock_websocket)
        
        assert user_id not in manager.connections
    
    def test_disconnect_keeps_other_connections(self, manager, mock_websocket):
        """Test disconnecting one connection keeps others for same user"""
        user_id = "user123"
        ws2 = Mock(spec=WebSocket)
        manager.connections[user_id] = [mock_websocket, ws2]
        
        manager.disconnect(user_id, mock_websocket)
        
        assert user_id in manager.connections
        assert mock_websocket not in manager.connections[user_id]
        assert ws2 in manager.connections[user_id]
        assert len(manager.connections[user_id]) == 1
    
    def test_disconnect_nonexistent_user(self, manager, mock_websocket):
        """Test disconnecting nonexistent user doesn't raise error"""
        # Should not raise exception
        manager.disconnect("nonexistent_user", mock_websocket)
        
        assert "nonexistent_user" not in manager.connections
    
    def test_disconnect_nonexistent_connection(self, manager, mock_websocket):
        """Test disconnecting nonexistent connection for existing user"""
        user_id = "user123"
        ws2 = Mock(spec=WebSocket)
        manager.connections[user_id] = [ws2]
        
        # Should not raise exception
        manager.disconnect(user_id, mock_websocket)
        
        # ws2 should still be there
        assert ws2 in manager.connections[user_id]
    
    def test_disconnect_converts_user_id_to_string(self, manager, mock_websocket):
        """Test disconnect converts user_id to string"""
        user_id = 12345
        manager.connections["12345"] = [mock_websocket]
        
        manager.disconnect(user_id, mock_websocket)
        
        assert "12345" not in manager.connections
    
    @pytest.mark.asyncio
    async def test_send_message_update_no_connections(self, manager):
        """Test sending update to user with no connections does nothing"""
        # Should not raise exception
        await manager.send_message_update("user123")
        
        # No assertions needed, just verify it doesn't crash
    
    @pytest.mark.asyncio
    async def test_send_message_update_with_messages(self, manager, mock_websocket, test_db):
        """Test sending message update with unread messages"""
        from app.models.database import Message, User
        from app.core.security import get_password_hash
        import uuid
        from datetime import datetime
        from contextlib import contextmanager
        
        # Create test users
        sender = User(
            id=str(uuid.uuid4()),
            username="sender",
            email="sender@test.com",
            hashed_password=get_password_hash("password"),
            is_active=True,
            created_at=datetime.now(),
            password_version=0
        )
        recipient = User(
            id=str(uuid.uuid4()),
            username="recipient",
            email="recipient@test.com",
            hashed_password=get_password_hash("password"),
            is_active=True,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add_all([sender, recipient])
        test_db.commit()
        
        # Create test messages
        msg1 = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=recipient.id,
            title="Test Title 1",
            content="Test message 1",
            is_read=False,
            created_at=datetime.now()
        )
        msg2 = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=recipient.id,
            title="Test Title 2",
            content="Test message 2",
            is_read=False,
            created_at=datetime.now()
        )
        test_db.add_all([msg1, msg2])
        test_db.commit()
        
        # Setup manager with connection
        manager.connections[recipient.id] = [mock_websocket]
        
        # Mock get_db_context to return the test database session
        @contextmanager
        def mock_get_db_context():
            yield test_db
        
        # Mock the to_dict method on Message instances
        def mock_to_dict(self):
            return {
                "id": self.id,
                "title": self.title,
                "content": self.content,
                "sender_id": self.sender_id,
                "is_read": self.is_read,
                "created_at": self.created_at.isoformat() if self.created_at else None
            }
        
        with patch('app.utils.websocket.get_db_context', mock_get_db_context), \
             patch.object(Message, 'to_dict', mock_to_dict, create=True):
            await manager.send_message_update(recipient.id)
        
        # Verify WebSocket was called
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        
        assert call_args["type"] == "message_update"
        assert call_args["unread"] == 2
        assert "last_message" in call_args
    
    @pytest.mark.asyncio
    async def test_send_message_update_no_messages(self, manager, mock_websocket, test_db):
        """Test sending message update when user has no messages"""
        from app.models.database import User
        from app.core.security import get_password_hash
        import uuid
        from datetime import datetime
        
        # Create test user with no messages
        user = User(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@test.com",
            hashed_password=get_password_hash("password"),
            is_active=True,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(user)
        test_db.commit()
        
        # Setup manager with connection
        manager.connections[user.id] = [mock_websocket]
        
        await manager.send_message_update(user.id)
        
        # Verify WebSocket was called
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        
        assert call_args["type"] == "message_update"
        assert call_args["unread"] == 0
        assert "last_message" not in call_args
    
    @pytest.mark.asyncio
    async def test_send_message_update_handles_send_failure(self, manager, mock_websocket):
        """Test send_message_update handles WebSocket send failures"""
        from app.models.database import User
        from app.core.security import get_password_hash
        import uuid
        from datetime import datetime
        
        user_id = "user123"
        manager.connections[user_id] = [mock_websocket]
        
        # Make send_json raise exception
        mock_websocket.send_json.side_effect = Exception("Connection closed")
        
        # Should not raise exception, but should disconnect the websocket
        await manager.send_message_update(user_id)
        
        # Connection should be removed
        assert user_id not in manager.connections
    
    @pytest.mark.asyncio
    async def test_send_message_update_multiple_connections(self, manager, test_db):
        """Test sending update to user with multiple connections"""
        from app.models.database import User
        from app.core.security import get_password_hash
        import uuid
        from datetime import datetime
        
        # Create test user
        user = User(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@test.com",
            hashed_password=get_password_hash("password"),
            is_active=True,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(user)
        test_db.commit()
        
        # Create multiple mock connections
        ws1 = Mock(spec=WebSocket)
        ws1.send_json = AsyncMock()
        ws2 = Mock(spec=WebSocket)
        ws2.send_json = AsyncMock()
        
        manager.connections[user.id] = [ws1, ws2]
        
        await manager.send_message_update(user.id)
        
        # Both connections should receive the update
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_user_update_multiple_users(self, manager, test_db):
        """Test broadcasting updates to multiple users"""
        from app.models.database import User
        from app.core.security import get_password_hash
        import uuid
        from datetime import datetime
        
        # Create test users
        users = []
        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                username=f"user{i}",
                email=f"user{i}@test.com",
                hashed_password=get_password_hash("password"),
                is_active=True,
                created_at=datetime.now(),
                password_version=0
            )
            users.append(user)
            test_db.add(user)
        test_db.commit()
        
        # Setup connections for each user
        for user in users:
            ws = Mock(spec=WebSocket)
            ws.send_json = AsyncMock()
            manager.connections[user.id] = [ws]
        
        # Broadcast to all users
        user_ids = [user.id for user in users]
        await manager.broadcast_user_update(user_ids)
        
        # Verify all connections received updates
        for user in users:
            ws = manager.connections[user.id][0]
            ws.send_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_user_update_deduplicates_ids(self, manager, test_db):
        """Test broadcast deduplicates user IDs"""
        from app.models.database import User
        from app.core.security import get_password_hash
        import uuid
        from datetime import datetime
        
        # Create test user
        user = User(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@test.com",
            hashed_password=get_password_hash("password"),
            is_active=True,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(user)
        test_db.commit()
        
        # Setup connection
        ws = Mock(spec=WebSocket)
        ws.send_json = AsyncMock()
        manager.connections[user.id] = [ws]
        
        # Broadcast with duplicate IDs
        await manager.broadcast_user_update([user.id, user.id, user.id])
        
        # Should only send once despite duplicates
        ws.send_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_user_update_filters_none_values(self, manager):
        """Test broadcast filters out None values from user_ids"""
        # Should not raise exception with None values
        await manager.broadcast_user_update([None, "user123", None])
        
        # No assertions needed, just verify it doesn't crash
    
    @pytest.mark.asyncio
    async def test_broadcast_user_update_empty_list(self, manager):
        """Test broadcast with empty list doesn't raise error"""
        # Should not raise exception
        await manager.broadcast_user_update([])
        
        # No assertions needed, just verify it doesn't crash


class TestGlobalManagerInstance:
    """Tests for the global message_ws_manager instance"""
    
    def test_global_manager_exists(self):
        """Test global manager instance is created"""
        assert message_ws_manager is not None
        assert isinstance(message_ws_manager, MessageWebSocketManager)
    
    def test_global_manager_has_connections_dict(self):
        """Test global manager has connections dictionary"""
        assert hasattr(message_ws_manager, 'connections')
        assert isinstance(message_ws_manager.connections, dict)
