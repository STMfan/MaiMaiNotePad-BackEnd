"""
Tests for MockServiceFactory

Validates that all mock objects are created correctly and behave as expected.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from tests.mock_service_factory import MockServiceFactory


class TestEmailServiceMock:
    """Tests for email service mock creation"""
    
    def test_create_email_service_mock_default(self):
        """Test creating email service mock with default settings"""
        mock_email = MockServiceFactory.create_email_service_mock()
        
        # Verify it's a Mock object
        assert isinstance(mock_email, Mock)
        
        # Verify attributes are set
        assert mock_email.mail_host == "smtp.example.com"
        assert mock_email.mail_user == "test@example.com"
        assert mock_email.mail_port == 465
        assert mock_email.mail_pwd == "test_password"
        assert mock_email.mail_timeout == 10
        
        # Verify send_email method exists and can be called
        mock_email.send_email("recipient@example.com", "Test Subject", "Test Content")
        mock_email.send_email.assert_called_once_with(
            "recipient@example.com", "Test Subject", "Test Content"
        )
    
    def test_create_email_service_mock_with_error(self):
        """Test creating email service mock that raises an error"""
        test_error = RuntimeError("Email sending failed")
        mock_email = MockServiceFactory.create_email_service_mock(raise_error=test_error)
        
        # Verify calling send_email raises the error
        with pytest.raises(RuntimeError, match="Email sending failed"):
            mock_email.send_email("recipient@example.com", "Subject", "Content")
    
    def test_email_service_mock_call_tracking(self):
        """Test that email service mock tracks method calls"""
        mock_email = MockServiceFactory.create_email_service_mock()
        
        # Make multiple calls
        mock_email.send_email("user1@example.com", "Subject 1", "Content 1")
        mock_email.send_email("user2@example.com", "Subject 2", "Content 2")
        
        # Verify call count
        assert mock_email.send_email.call_count == 2
        
        # Verify call arguments
        calls = mock_email.send_email.call_args_list
        assert calls[0][0] == ("user1@example.com", "Subject 1", "Content 1")
        assert calls[1][0] == ("user2@example.com", "Subject 2", "Content 2")


class TestFileServiceMock:
    """Tests for file service mock creation"""
    
    def test_create_file_service_mock_default(self):
        """Test creating file service mock with default settings"""
        mock_file = MockServiceFactory.create_file_service_mock()
        
        # Verify it's a Mock object
        assert isinstance(mock_file, Mock)
        
        # Verify attributes are set
        assert mock_file.upload_dir == "/test/uploads"
        assert mock_file.knowledge_dir == "/test/uploads/knowledge"
        assert mock_file.persona_dir == "/test/uploads/persona"
        assert mock_file.MAX_FILE_SIZE == 100 * 1024 * 1024
        assert mock_file.MAX_KNOWLEDGE_FILES == 100
        assert mock_file.MAX_PERSONA_FILES == 1
        assert mock_file.ALLOWED_KNOWLEDGE_TYPES == [".txt", ".json"]
        assert mock_file.ALLOWED_PERSONA_TYPES == [".toml"]
    
    def test_file_service_mock_upload_knowledge_base(self):
        """Test file service mock upload_knowledge_base method"""
        mock_file = MockServiceFactory.create_file_service_mock()
        
        files = [("test.txt", b"test content")]
        result = mock_file.upload_knowledge_base(
            files, "Test KB", "Description", "user123"
        )
        
        # Verify method was called
        mock_file.upload_knowledge_base.assert_called_once()
        
        # Verify return value
        assert result is not None
        assert result.id == "kb_123"
        assert result.name == "Test Knowledge Base"
        assert result.is_pending is True
    
    def test_file_service_mock_upload_persona_card(self):
        """Test file service mock upload_persona_card method"""
        mock_file = MockServiceFactory.create_file_service_mock()
        
        files = [("bot_config.toml", b"test content")]
        result = mock_file.upload_persona_card(
            files, "Test Persona", "Description", "user123", "Owner"
        )
        
        # Verify method was called
        mock_file.upload_persona_card.assert_called_once()
        
        # Verify return value
        assert result is not None
        assert result.id == "pc_123"
        assert result.name == "Test Persona Card"
        assert result.version == "1.0"
    
    def test_file_service_mock_get_knowledge_base_content(self):
        """Test file service mock get_knowledge_base_content method"""
        mock_file = MockServiceFactory.create_file_service_mock(file_exists=True)
        
        result = mock_file.get_knowledge_base_content("kb_123")
        
        # Verify return value structure
        assert "knowledge_base" in result
        assert "files" in result
        assert result["knowledge_base"]["id"] == "kb_123"
        assert len(result["files"]) == 1
        assert result["files"][0]["file_id"] == "file_123"
    
    def test_file_service_mock_get_persona_card_content(self):
        """Test file service mock get_persona_card_content method"""
        mock_file = MockServiceFactory.create_file_service_mock(file_exists=True)
        
        result = mock_file.get_persona_card_content("pc_123")
        
        # Verify return value structure
        assert "persona_card" in result
        assert "files" in result
        assert result["persona_card"]["id"] == "pc_123"
        assert result["persona_card"]["version"] == "1.0"
        assert len(result["files"]) == 1
    
    def test_file_service_mock_file_not_exists(self):
        """Test file service mock when files don't exist"""
        mock_file = MockServiceFactory.create_file_service_mock(file_exists=False)
        
        # Verify methods return None when files don't exist
        assert mock_file.get_knowledge_base_content("kb_123") is None
        assert mock_file.get_persona_card_content("pc_123") is None
        assert mock_file.get_knowledge_base_file_path("kb_123", "file_123") is None
        assert mock_file.get_persona_card_file_path("pc_123", "file_123") is None
    
    def test_file_service_mock_with_error(self):
        """Test file service mock that raises an error"""
        test_error = Exception("File operation failed")
        mock_file = MockServiceFactory.create_file_service_mock(raise_error=test_error)
        
        # Verify operations raise the error
        with pytest.raises(Exception, match="File operation failed"):
            mock_file.upload_knowledge_base([], "Test", "Desc", "user123")
        
        with pytest.raises(Exception, match="File operation failed"):
            mock_file.upload_persona_card([], "Test", "Desc", "user123", "Owner")
    
    def test_file_service_mock_delete_operations(self):
        """Test file service mock delete operations"""
        mock_file = MockServiceFactory.create_file_service_mock()
        
        # Test delete file
        result = mock_file.delete_file_from_knowledge_base("kb_123", "file_123", "user123")
        assert result is True
        mock_file.delete_file_from_knowledge_base.assert_called_once()
        
        # Test delete knowledge base
        result = mock_file.delete_knowledge_base("kb_123", "user123")
        assert result is True
        mock_file.delete_knowledge_base.assert_called_once()
    
    def test_file_service_mock_zip_creation(self):
        """Test file service mock zip creation methods"""
        mock_file = MockServiceFactory.create_file_service_mock()
        
        # Test knowledge base zip
        result = mock_file.create_knowledge_base_zip("kb_123")
        assert "zip_path" in result
        assert "zip_filename" in result
        assert result["zip_path"] == "/tmp/test.zip"
        
        # Test persona card zip
        result = mock_file.create_persona_card_zip("pc_123")
        assert "zip_path" in result
        assert "zip_filename" in result
        assert result["zip_path"] == "/tmp/test.zip"


class TestWebSocketMock:
    """Tests for WebSocket mock creation"""
    
    @pytest.mark.asyncio
    async def test_create_websocket_mock_default(self):
        """Test creating WebSocket mock with default settings"""
        mock_ws = MockServiceFactory.create_websocket_mock()
        
        # Verify it's an AsyncMock object
        assert isinstance(mock_ws, AsyncMock)
        
        # Verify state attributes
        assert mock_ws.client_state == "CONNECTED"
        assert mock_ws.application_state == "CONNECTED"
        
        # Verify accept method works
        await mock_ws.accept()
        mock_ws.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_mock_send_operations(self):
        """Test WebSocket mock send operations"""
        mock_ws = MockServiceFactory.create_websocket_mock()
        
        # Test send_json
        await mock_ws.send_json({"type": "test", "data": "value"})
        mock_ws.send_json.assert_called_once_with({"type": "test", "data": "value"})
        
        # Test send_text
        await mock_ws.send_text("test message")
        mock_ws.send_text.assert_called_once_with("test message")
        
        # Test send_bytes
        await mock_ws.send_bytes(b"test bytes")
        mock_ws.send_bytes.assert_called_once_with(b"test bytes")
    
    @pytest.mark.asyncio
    async def test_websocket_mock_receive_operations(self):
        """Test WebSocket mock receive operations"""
        mock_ws = MockServiceFactory.create_websocket_mock()
        
        # Test receive_json
        result = await mock_ws.receive_json()
        assert result == {"type": "ping"}
        
        # Test receive_text
        result = await mock_ws.receive_text()
        assert result == "ping"
        
        # Test receive_bytes
        result = await mock_ws.receive_bytes()
        assert result == b"ping"
    
    @pytest.mark.asyncio
    async def test_websocket_mock_close(self):
        """Test WebSocket mock close operation"""
        mock_ws = MockServiceFactory.create_websocket_mock()
        
        await mock_ws.close()
        mock_ws.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_mock_accept_failure(self):
        """Test WebSocket mock with accept failure"""
        mock_ws = MockServiceFactory.create_websocket_mock(auto_accept=False)
        
        with pytest.raises(Exception, match="Connection failed"):
            await mock_ws.accept()
    
    @pytest.mark.asyncio
    async def test_websocket_mock_send_failure(self):
        """Test WebSocket mock with send failure"""
        mock_ws = MockServiceFactory.create_websocket_mock(send_success=False)
        
        with pytest.raises(Exception, match="Send failed"):
            await mock_ws.send_json({"type": "test"})
        
        with pytest.raises(Exception, match="Send failed"):
            await mock_ws.send_text("test")
        
        with pytest.raises(Exception, match="Send failed"):
            await mock_ws.send_bytes(b"test")


class TestWebSocketManagerMock:
    """Tests for WebSocket manager mock creation"""
    
    def test_create_websocket_manager_mock_default(self):
        """Test creating WebSocket manager mock with default settings"""
        mock_manager = MockServiceFactory.create_websocket_manager_mock()
        
        # Verify it's a Mock object
        assert isinstance(mock_manager, Mock)
        
        # Verify connections dictionary is initialized
        assert hasattr(mock_manager, "connections")
        assert isinstance(mock_manager.connections, dict)
        assert len(mock_manager.connections) == 0
        
        # Verify methods exist
        assert hasattr(mock_manager, "connect")
        assert hasattr(mock_manager, "disconnect")
        assert hasattr(mock_manager, "send_message_update")
        assert hasattr(mock_manager, "broadcast_user_update")
    
    def test_create_websocket_manager_mock_with_users(self):
        """Test creating WebSocket manager mock with connected users"""
        mock_manager = MockServiceFactory.create_websocket_manager_mock(
            connected_users=["user123", "user456"]
        )
        
        # Verify connections are initialized
        assert "user123" in mock_manager.connections
        assert "user456" in mock_manager.connections
        assert len(mock_manager.connections) == 2
    
    @pytest.mark.asyncio
    async def test_websocket_manager_mock_connect(self):
        """Test WebSocket manager mock connect method"""
        mock_manager = MockServiceFactory.create_websocket_manager_mock()
        mock_ws = MockServiceFactory.create_websocket_mock()
        
        # Connect a user
        await mock_manager.connect("user123", mock_ws)
        
        # Verify connection was added
        assert "user123" in mock_manager.connections
        assert mock_ws in mock_manager.connections["user123"]
        
        # Verify method was called
        mock_manager.connect.assert_called_once_with("user123", mock_ws)
    
    @pytest.mark.asyncio
    async def test_websocket_manager_mock_disconnect(self):
        """Test WebSocket manager mock disconnect method"""
        mock_manager = MockServiceFactory.create_websocket_manager_mock()
        mock_ws = MockServiceFactory.create_websocket_mock()
        
        # Connect then disconnect
        await mock_manager.connect("user123", mock_ws)
        mock_manager.disconnect("user123", mock_ws)
        
        # Verify connection was removed
        assert "user123" not in mock_manager.connections
        
        # Verify method was called
        mock_manager.disconnect.assert_called_once_with("user123", mock_ws)
    
    @pytest.mark.asyncio
    async def test_websocket_manager_mock_multiple_connections(self):
        """Test WebSocket manager mock with multiple connections per user"""
        mock_manager = MockServiceFactory.create_websocket_manager_mock()
        mock_ws1 = MockServiceFactory.create_websocket_mock()
        mock_ws2 = MockServiceFactory.create_websocket_mock()
        
        # Connect same user twice
        await mock_manager.connect("user123", mock_ws1)
        await mock_manager.connect("user123", mock_ws2)
        
        # Verify both connections exist
        assert len(mock_manager.connections["user123"]) == 2
        assert mock_ws1 in mock_manager.connections["user123"]
        assert mock_ws2 in mock_manager.connections["user123"]
        
        # Disconnect one
        mock_manager.disconnect("user123", mock_ws1)
        
        # Verify only one connection remains
        assert len(mock_manager.connections["user123"]) == 1
        assert mock_ws2 in mock_manager.connections["user123"]
    
    @pytest.mark.asyncio
    async def test_websocket_manager_mock_send_message_update(self):
        """Test WebSocket manager mock send_message_update method"""
        mock_manager = MockServiceFactory.create_websocket_manager_mock()
        
        await mock_manager.send_message_update("user123")
        
        # Verify method was called
        mock_manager.send_message_update.assert_called_once_with("user123")
    
    @pytest.mark.asyncio
    async def test_websocket_manager_mock_broadcast_user_update(self):
        """Test WebSocket manager mock broadcast_user_update method"""
        mock_manager = MockServiceFactory.create_websocket_manager_mock()
        
        user_ids = ["user123", "user456", "user789"]
        await mock_manager.broadcast_user_update(user_ids)
        
        # Verify method was called
        mock_manager.broadcast_user_update.assert_called_once_with(user_ids)
