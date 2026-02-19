"""
Integration tests demonstrating the use of mock service fixtures

These tests show how to use the mock service fixtures provided by conftest.py
in actual test scenarios.
"""

import pytest


class TestMockEmailServiceFixture:
    """Tests demonstrating email service mock fixture usage"""
    
    def test_email_service_fixture_basic(self, mock_email_service):
        """Test that email service fixture is properly configured"""
        # Verify fixture provides a mock
        assert mock_email_service is not None
        
        # Use the mock
        mock_email_service.send_email(
            "recipient@example.com",
            "Test Subject",
            "Test Content"
        )
        
        # Verify the call
        mock_email_service.send_email.assert_called_once_with(
            "recipient@example.com",
            "Test Subject",
            "Test Content"
        )
    
    def test_email_service_fixture_attributes(self, mock_email_service):
        """Test that email service fixture has expected attributes"""
        assert mock_email_service.mail_host == "smtp.example.com"
        assert mock_email_service.mail_user == "test@example.com"
        assert mock_email_service.mail_port == 465


class TestMockFileServiceFixture:
    """Tests demonstrating file service mock fixture usage"""
    
    def test_file_service_fixture_basic(self, mock_file_service):
        """Test that file service fixture is properly configured"""
        # Verify fixture provides a mock
        assert mock_file_service is not None
        
        # Use the mock
        files = [("test.txt", b"test content")]
        result = mock_file_service.upload_knowledge_base(
            files, "Test KB", "Description", "user123"
        )
        
        # Verify the result
        assert result is not None
        assert result.id == "kb_123"
        assert result.name == "Test Knowledge Base"
    
    def test_file_service_fixture_attributes(self, mock_file_service):
        """Test that file service fixture has expected attributes"""
        assert mock_file_service.upload_dir == "/test/uploads"
        assert mock_file_service.MAX_FILE_SIZE == 100 * 1024 * 1024
        assert mock_file_service.ALLOWED_KNOWLEDGE_TYPES == [".txt", ".json"]


class TestMockWebSocketFixture:
    """Tests demonstrating WebSocket mock fixture usage"""
    
    @pytest.mark.asyncio
    async def test_websocket_fixture_basic(self, mock_websocket):
        """Test that WebSocket fixture is properly configured"""
        # Verify fixture provides a mock
        assert mock_websocket is not None
        
        # Use the mock
        await mock_websocket.accept()
        await mock_websocket.send_json({"type": "test", "data": "value"})
        
        # Verify the calls
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_json.assert_called_once_with(
            {"type": "test", "data": "value"}
        )
    
    @pytest.mark.asyncio
    async def test_websocket_fixture_state(self, mock_websocket):
        """Test that WebSocket fixture has expected state"""
        assert mock_websocket.client_state == "CONNECTED"
        assert mock_websocket.application_state == "CONNECTED"


class TestMockWebSocketManagerFixture:
    """Tests demonstrating WebSocket manager mock fixture usage"""
    
    @pytest.mark.asyncio
    async def test_websocket_manager_fixture_basic(
        self, mock_websocket_manager, mock_websocket
    ):
        """Test that WebSocket manager fixture is properly configured"""
        # Verify fixture provides a mock
        assert mock_websocket_manager is not None
        
        # Use the mock
        await mock_websocket_manager.connect("user123", mock_websocket)
        
        # Verify connection was added
        assert "user123" in mock_websocket_manager.connections
        
        # Send update
        await mock_websocket_manager.send_message_update("user123")
        
        # Verify the call
        mock_websocket_manager.send_message_update.assert_called_once_with("user123")
    
    def test_websocket_manager_fixture_initialization(self, mock_websocket_manager):
        """Test that WebSocket manager fixture is properly initialized"""
        assert hasattr(mock_websocket_manager, "connections")
        assert isinstance(mock_websocket_manager.connections, dict)


class TestMultipleFixturesCombined:
    """Tests demonstrating combined usage of multiple mock fixtures"""
    
    def test_email_and_file_service_together(
        self, mock_email_service, mock_file_service
    ):
        """Test using email and file service mocks together"""
        # Upload a file
        files = [("test.txt", b"content")]
        kb = mock_file_service.upload_knowledge_base(
            files, "Test KB", "Description", "user123"
        )
        
        # Send notification email
        mock_email_service.send_email(
            "user@example.com",
            "Upload Complete",
            f"Your knowledge base {kb.name} has been uploaded"
        )
        
        # Verify both operations
        mock_file_service.upload_knowledge_base.assert_called_once()
        mock_email_service.send_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_all_mocks_together(
        self,
        mock_email_service,
        mock_file_service,
        mock_websocket,
        mock_websocket_manager
    ):
        """Test using all mock fixtures together"""
        # File operation
        files = [("test.txt", b"content")]
        kb = mock_file_service.upload_knowledge_base(
            files, "Test KB", "Description", "user123"
        )
        
        # Email notification
        mock_email_service.send_email(
            "user@example.com",
            "Upload Complete",
            f"KB {kb.name} uploaded"
        )
        
        # WebSocket notification
        await mock_websocket_manager.connect("user123", mock_websocket)
        await mock_websocket_manager.send_message_update("user123")
        
        # Verify all operations
        assert mock_file_service.upload_knowledge_base.called
        assert mock_email_service.send_email.called
        assert mock_websocket_manager.send_message_update.called


class TestFixtureIsolation:
    """Tests verifying that fixtures are properly isolated between tests"""
    
    def test_email_service_first_test(self, mock_email_service):
        """First test using email service"""
        mock_email_service.send_email("test1@example.com", "Subject 1", "Content 1")
        assert mock_email_service.send_email.call_count == 1
    
    def test_email_service_second_test(self, mock_email_service):
        """Second test using email service - should have fresh mock"""
        # This should be a fresh mock with no previous calls
        assert mock_email_service.send_email.call_count == 0
        
        mock_email_service.send_email("test2@example.com", "Subject 2", "Content 2")
        assert mock_email_service.send_email.call_count == 1
    
    @pytest.mark.asyncio
    async def test_websocket_manager_first_test(
        self, mock_websocket_manager, mock_websocket
    ):
        """First test using WebSocket manager"""
        await mock_websocket_manager.connect("user1", mock_websocket)
        assert "user1" in mock_websocket_manager.connections
    
    @pytest.mark.asyncio
    async def test_websocket_manager_second_test(
        self, mock_websocket_manager, mock_websocket
    ):
        """Second test using WebSocket manager - should have fresh mock"""
        # This should be a fresh mock with no previous connections
        assert len(mock_websocket_manager.connections) == 0
        
        await mock_websocket_manager.connect("user2", mock_websocket)
        assert "user2" in mock_websocket_manager.connections
        assert "user1" not in mock_websocket_manager.connections
