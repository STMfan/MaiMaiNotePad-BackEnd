"""
MockServiceFactory for creating mock objects for external services

Provides factory methods for creating configured mock objects for:
- Email service
- File service  
- WebSocket connections

These mocks are used to isolate components during testing without requiring
actual external dependencies.
"""

from typing import Optional, Dict, Any, List
from unittest.mock import Mock, MagicMock, AsyncMock
from datetime import datetime


class MockServiceFactory:
    """Factory for creating mock objects for external services"""
    
    @staticmethod
    def create_email_service_mock(
        send_success: bool = True,
        raise_error: Optional[Exception] = None
    ) -> Mock:
        """
        Create a mock EmailService object
        
        Args:
            send_success: Whether send_email should succeed (default: True)
            raise_error: Optional exception to raise when send_email is called
        
        Returns:
            Mock: Configured EmailService mock
        
        Example:
            >>> mock_email = MockServiceFactory.create_email_service_mock()
            >>> mock_email.send_email("test@example.com", "Subject", "Content")
            >>> mock_email.send_email.assert_called_once()
        """
        mock_service = Mock()
        
        if raise_error:
            mock_service.send_email.side_effect = raise_error
        else:
            mock_service.send_email.return_value = None
        
        # Set up attributes
        mock_service.mail_host = "smtp.example.com"
        mock_service.mail_user = "test@example.com"
        mock_service.mail_port = 465
        mock_service.mail_pwd = "test_password"
        mock_service.mail_timeout = 10
        
        return mock_service
    
    @staticmethod
    def create_file_service_mock(
        upload_success: bool = True,
        file_exists: bool = True,
        raise_error: Optional[Exception] = None
    ) -> Mock:
        """
        Create a mock FileService object
        
        Args:
            upload_success: Whether file uploads should succeed (default: True)
            file_exists: Whether files should exist when queried (default: True)
            raise_error: Optional exception to raise on operations
        
        Returns:
            Mock: Configured FileService mock
        
        Example:
            >>> mock_file = MockServiceFactory.create_file_service_mock()
            >>> result = mock_file.upload_knowledge_base(files, "Test", "Desc", "user123")
            >>> assert result is not None
        """
        mock_service = Mock()
        
        # Configure upload methods
        if raise_error:
            mock_service.upload_knowledge_base.side_effect = raise_error
            mock_service.upload_persona_card.side_effect = raise_error
            mock_service.add_files_to_knowledge_base.side_effect = raise_error
        else:
            # Create mock knowledge base return value
            mock_kb = Mock()
            mock_kb.id = "kb_123"
            mock_kb.name = "Test Knowledge Base"
            mock_kb.description = "Test description"
            mock_kb.uploader_id = "user_123"
            mock_kb.is_public = False
            mock_kb.is_pending = True
            mock_kb.base_path = "/test/path"
            mock_kb.created_at = datetime.now()
            mock_kb.updated_at = datetime.now()
            
            # Create mock persona card return value
            mock_pc = Mock()
            mock_pc.id = "pc_123"
            mock_pc.name = "Test Persona Card"
            mock_pc.description = "Test description"
            mock_pc.uploader_id = "user_123"
            mock_pc.is_public = False
            mock_pc.is_pending = True
            mock_pc.base_path = "/test/path"
            mock_pc.version = "1.0"
            mock_pc.created_at = datetime.now()
            mock_pc.updated_at = datetime.now()
            
            mock_service.upload_knowledge_base.return_value = mock_kb
            mock_service.upload_persona_card.return_value = mock_pc
            mock_service.add_files_to_knowledge_base.return_value = mock_kb
        
        # Configure get methods
        if file_exists:
            mock_service.get_knowledge_base_content.return_value = {
                "knowledge_base": {
                    "id": "kb_123",
                    "name": "Test Knowledge Base",
                    "description": "Test description",
                    "uploader_id": "user_123",
                    "is_public": False,
                    "is_pending": True,
                },
                "files": [
                    {
                        "file_id": "file_123",
                        "original_name": "test.txt",
                        "file_size": 1024,
                    }
                ],
            }
            
            mock_service.get_persona_card_content.return_value = {
                "persona_card": {
                    "id": "pc_123",
                    "name": "Test Persona Card",
                    "description": "Test description",
                    "uploader_id": "user_123",
                    "is_public": False,
                    "is_pending": True,
                    "version": "1.0",
                },
                "files": [
                    {
                        "file_id": "file_123",
                        "original_name": "bot_config.toml",
                        "file_size": 512,
                    }
                ],
            }
            
            mock_service.get_knowledge_base_file_path.return_value = {
                "file_name": "test.txt",
                "file_path": "/test/path/test.txt"
            }
            
            mock_service.get_persona_card_file_path.return_value = {
                "file_id": "file_123",
                "file_name": "bot_config.toml",
                "file_path": "/test/path/bot_config.toml"
            }
        else:
            mock_service.get_knowledge_base_content.return_value = None
            mock_service.get_persona_card_content.return_value = None
            mock_service.get_knowledge_base_file_path.return_value = None
            mock_service.get_persona_card_file_path.return_value = None
        
        # Configure delete methods
        mock_service.delete_file_from_knowledge_base.return_value = True
        mock_service.delete_knowledge_base.return_value = True
        
        # Configure zip creation methods
        mock_service.create_knowledge_base_zip.return_value = {
            "zip_path": "/tmp/test.zip",
            "zip_filename": "test.zip"
        }
        mock_service.create_persona_card_zip.return_value = {
            "zip_path": "/tmp/test.zip",
            "zip_filename": "test.zip"
        }
        
        # Set up attributes
        mock_service.upload_dir = "/test/uploads"
        mock_service.knowledge_dir = "/test/uploads/knowledge"
        mock_service.persona_dir = "/test/uploads/persona"
        mock_service.MAX_FILE_SIZE = 100 * 1024 * 1024
        mock_service.MAX_KNOWLEDGE_FILES = 100
        mock_service.MAX_PERSONA_FILES = 1
        mock_service.ALLOWED_KNOWLEDGE_TYPES = [".txt", ".json"]
        mock_service.ALLOWED_PERSONA_TYPES = [".toml"]
        
        return mock_service
    
    @staticmethod
    def create_websocket_mock(
        auto_accept: bool = True,
        send_success: bool = True
    ) -> AsyncMock:
        """
        Create a mock WebSocket connection object
        
        Args:
            auto_accept: Whether accept() should succeed automatically (default: True)
            send_success: Whether send operations should succeed (default: True)
        
        Returns:
            AsyncMock: Configured WebSocket mock
        
        Example:
            >>> mock_ws = MockServiceFactory.create_websocket_mock()
            >>> await mock_ws.accept()
            >>> await mock_ws.send_json({"type": "test"})
            >>> mock_ws.send_json.assert_called_once()
        """
        mock_websocket = AsyncMock()
        
        # Configure accept method
        if auto_accept:
            mock_websocket.accept.return_value = None
        else:
            mock_websocket.accept.side_effect = Exception("Connection failed")
        
        # Configure send methods
        if send_success:
            mock_websocket.send_json.return_value = None
            mock_websocket.send_text.return_value = None
            mock_websocket.send_bytes.return_value = None
        else:
            mock_websocket.send_json.side_effect = Exception("Send failed")
            mock_websocket.send_text.side_effect = Exception("Send failed")
            mock_websocket.send_bytes.side_effect = Exception("Send failed")
        
        # Configure receive methods
        mock_websocket.receive_json.return_value = {"type": "ping"}
        mock_websocket.receive_text.return_value = "ping"
        mock_websocket.receive_bytes.return_value = b"ping"
        
        # Configure close method
        mock_websocket.close.return_value = None
        
        # Set up client state
        mock_websocket.client_state = "CONNECTED"
        mock_websocket.application_state = "CONNECTED"
        
        return mock_websocket
    
    @staticmethod
    def create_websocket_manager_mock(
        connected_users: Optional[List[str]] = None
    ) -> Mock:
        """
        Create a mock MessageWebSocketManager object
        
        Args:
            connected_users: List of user IDs that should be considered connected
        
        Returns:
            Mock: Configured MessageWebSocketManager mock
        
        Example:
            >>> mock_manager = MockServiceFactory.create_websocket_manager_mock(["user123"])
            >>> await mock_manager.connect("user123", websocket)
            >>> await mock_manager.send_message_update("user123")
            >>> mock_manager.disconnect("user123", websocket)
        """
        mock_manager = Mock()
        
        # Initialize connections dictionary
        if connected_users:
            mock_manager.connections = {user_id: [] for user_id in connected_users}
        else:
            mock_manager.connections = {}
        
        # Configure async methods as AsyncMock
        mock_manager.connect = AsyncMock()
        mock_manager.send_message_update = AsyncMock()
        mock_manager.broadcast_user_update = AsyncMock()
        
        # Configure sync methods
        mock_manager.disconnect = Mock()
        
        # Set up default behaviors
        async def mock_connect(user_id: str, websocket):
            key = str(user_id)
            if key not in mock_manager.connections:
                mock_manager.connections[key] = []
            mock_manager.connections[key].append(websocket)
        
        def mock_disconnect(user_id: str, websocket):
            key = str(user_id)
            if key in mock_manager.connections:
                if websocket in mock_manager.connections[key]:
                    mock_manager.connections[key].remove(websocket)
                if not mock_manager.connections[key]:
                    del mock_manager.connections[key]
        
        mock_manager.connect.side_effect = mock_connect
        mock_manager.disconnect.side_effect = mock_disconnect
        
        return mock_manager
