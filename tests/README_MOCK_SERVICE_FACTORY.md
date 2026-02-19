# MockServiceFactory Documentation

## Overview

The `MockServiceFactory` provides factory methods for creating mock objects for external services used in testing. This allows tests to run in isolation without requiring actual external dependencies like SMTP servers, file systems, or WebSocket connections.

## Purpose

- **Isolation**: Test components independently without external dependencies
- **Speed**: Tests run faster without network I/O or file system operations
- **Reliability**: Tests are deterministic and don't fail due to external service issues
- **Flexibility**: Configure mocks to simulate various scenarios (success, failure, edge cases)

## Available Mocks

### 1. Email Service Mock

Creates a mock `EmailService` object for testing email functionality.

#### Basic Usage

```python
from tests.mock_service_factory import MockServiceFactory

# Create a mock that succeeds
mock_email = MockServiceFactory.create_email_service_mock()
mock_email.send_email("user@example.com", "Subject", "Content")

# Verify the call
mock_email.send_email.assert_called_once_with(
    "user@example.com", "Subject", "Content"
)
```

#### Simulating Errors

```python
# Create a mock that raises an error
error = RuntimeError("SMTP connection failed")
mock_email = MockServiceFactory.create_email_service_mock(raise_error=error)

# This will raise the error
with pytest.raises(RuntimeError):
    mock_email.send_email("user@example.com", "Subject", "Content")
```

#### Available Attributes

- `mail_host`: SMTP server host
- `mail_user`: Email username
- `mail_port`: SMTP port
- `mail_pwd`: Email password
- `mail_timeout`: Connection timeout

### 2. File Service Mock

Creates a mock `FileService` object for testing file operations.

#### Basic Usage

```python
from tests.mock_service_factory import MockServiceFactory

# Create a mock file service
mock_file = MockServiceFactory.create_file_service_mock()

# Upload a knowledge base
files = [("test.txt", b"test content")]
kb = mock_file.upload_knowledge_base(
    files, "Test KB", "Description", "user123"
)

# Verify the upload
assert kb.id == "kb_123"
assert kb.name == "Test Knowledge Base"
```

#### Simulating File Not Found

```python
# Create a mock where files don't exist
mock_file = MockServiceFactory.create_file_service_mock(file_exists=False)

# These will return None
result = mock_file.get_knowledge_base_content("kb_123")
assert result is None
```

#### Simulating Errors

```python
# Create a mock that raises errors
error = Exception("Disk full")
mock_file = MockServiceFactory.create_file_service_mock(raise_error=error)

# This will raise the error
with pytest.raises(Exception):
    mock_file.upload_knowledge_base(files, "Test", "Desc", "user123")
```

#### Available Methods

- `upload_knowledge_base()`: Upload knowledge base files
- `upload_persona_card()`: Upload persona card files
- `get_knowledge_base_content()`: Get knowledge base info
- `get_persona_card_content()`: Get persona card info
- `add_files_to_knowledge_base()`: Add files to existing KB
- `delete_file_from_knowledge_base()`: Delete a file
- `delete_knowledge_base()`: Delete entire KB
- `create_knowledge_base_zip()`: Create ZIP archive
- `create_persona_card_zip()`: Create ZIP archive
- `get_knowledge_base_file_path()`: Get file path
- `get_persona_card_file_path()`: Get file path

### 3. WebSocket Mock

Creates a mock WebSocket connection for testing real-time communication.

#### Basic Usage

```python
import pytest
from tests.mock_service_factory import MockServiceFactory

@pytest.mark.asyncio
async def test_websocket():
    # Create a mock WebSocket
    mock_ws = MockServiceFactory.create_websocket_mock()
    
    # Accept connection
    await mock_ws.accept()
    
    # Send data
    await mock_ws.send_json({"type": "message", "data": "Hello"})
    
    # Verify the call
    mock_ws.send_json.assert_called_once()
```

#### Simulating Connection Failure

```python
@pytest.mark.asyncio
async def test_websocket_connection_failure():
    # Create a mock that fails to accept
    mock_ws = MockServiceFactory.create_websocket_mock(auto_accept=False)
    
    # This will raise an error
    with pytest.raises(Exception, match="Connection failed"):
        await mock_ws.accept()
```

#### Simulating Send Failure

```python
@pytest.mark.asyncio
async def test_websocket_send_failure():
    # Create a mock that fails to send
    mock_ws = MockServiceFactory.create_websocket_mock(send_success=False)
    
    # This will raise an error
    with pytest.raises(Exception, match="Send failed"):
        await mock_ws.send_json({"type": "test"})
```

#### Available Methods

- `accept()`: Accept WebSocket connection
- `send_json()`: Send JSON data
- `send_text()`: Send text data
- `send_bytes()`: Send binary data
- `receive_json()`: Receive JSON data
- `receive_text()`: Receive text data
- `receive_bytes()`: Receive binary data
- `close()`: Close connection

### 4. WebSocket Manager Mock

Creates a mock `MessageWebSocketManager` for testing WebSocket connection management.

#### Basic Usage

```python
import pytest
from tests.mock_service_factory import MockServiceFactory

@pytest.mark.asyncio
async def test_websocket_manager():
    # Create a mock manager
    mock_manager = MockServiceFactory.create_websocket_manager_mock()
    mock_ws = MockServiceFactory.create_websocket_mock()
    
    # Connect a user
    await mock_manager.connect("user123", mock_ws)
    
    # Verify connection exists
    assert "user123" in mock_manager.connections
    assert mock_ws in mock_manager.connections["user123"]
    
    # Send update
    await mock_manager.send_message_update("user123")
    
    # Disconnect
    mock_manager.disconnect("user123", mock_ws)
    
    # Verify connection removed
    assert "user123" not in mock_manager.connections
```

#### Pre-configured Connections

```python
# Create a manager with existing connections
mock_manager = MockServiceFactory.create_websocket_manager_mock(
    connected_users=["user123", "user456"]
)

# Verify users are connected
assert "user123" in mock_manager.connections
assert "user456" in mock_manager.connections
```

#### Available Methods

- `connect()`: Connect a user's WebSocket
- `disconnect()`: Disconnect a user's WebSocket
- `send_message_update()`: Send update to a user
- `broadcast_user_update()`: Broadcast to multiple users

## Integration with Tests

### Using with pytest Fixtures

```python
import pytest
from tests.mock_service_factory import MockServiceFactory

@pytest.fixture
def mock_email_service():
    """Fixture providing a mock email service"""
    return MockServiceFactory.create_email_service_mock()

@pytest.fixture
def mock_file_service():
    """Fixture providing a mock file service"""
    return MockServiceFactory.create_file_service_mock()

def test_my_feature(mock_email_service, mock_file_service):
    # Use the mocks in your test
    mock_email_service.send_email("test@example.com", "Subject", "Content")
    assert mock_email_service.send_email.called
```

### Patching with Mocks

```python
from unittest.mock import patch
from tests.mock_service_factory import MockServiceFactory

def test_with_patching():
    mock_email = MockServiceFactory.create_email_service_mock()
    
    with patch('app.services.email_service.EmailService', return_value=mock_email):
        # Your code that uses EmailService
        # It will use the mock instead
        pass
```

## Best Practices

1. **Use Appropriate Mock Configuration**: Configure mocks to match your test scenario (success, failure, edge cases)

2. **Verify Mock Interactions**: Always verify that mocks were called with expected arguments

3. **Reset Mocks Between Tests**: Use pytest fixtures with `function` scope to get fresh mocks for each test

4. **Test Both Success and Failure Paths**: Use mocks to test error handling by simulating failures

5. **Keep Tests Isolated**: Don't rely on external state; use mocks to control all dependencies

## Examples

### Testing Email Sending with Retry Logic

```python
import pytest
from tests.mock_service_factory import MockServiceFactory

def test_email_retry_on_failure():
    # First call fails, second succeeds
    mock_email = MockServiceFactory.create_email_service_mock()
    mock_email.send_email.side_effect = [
        RuntimeError("Temporary failure"),
        None  # Success
    ]
    
    # Your retry logic here
    # ...
    
    # Verify it was called twice
    assert mock_email.send_email.call_count == 2
```

### Testing File Upload Validation

```python
def test_file_upload_validation():
    mock_file = MockServiceFactory.create_file_service_mock()
    
    # Test with invalid file type
    from app.services.file_service import FileValidationError
    mock_file.upload_knowledge_base.side_effect = FileValidationError(
        "Invalid file type", code="INVALID_FILE_TYPE"
    )
    
    with pytest.raises(FileValidationError):
        mock_file.upload_knowledge_base(
            [("test.exe", b"content")], "Test", "Desc", "user123"
        )
```

### Testing WebSocket Broadcasting

```python
@pytest.mark.asyncio
async def test_websocket_broadcast():
    mock_manager = MockServiceFactory.create_websocket_manager_mock()
    
    # Connect multiple users
    ws1 = MockServiceFactory.create_websocket_mock()
    ws2 = MockServiceFactory.create_websocket_mock()
    
    await mock_manager.connect("user1", ws1)
    await mock_manager.connect("user2", ws2)
    
    # Broadcast to all
    await mock_manager.broadcast_user_update(["user1", "user2"])
    
    # Verify broadcast was called
    mock_manager.broadcast_user_update.assert_called_once()
```

## Requirements Validation

This MockServiceFactory implementation validates the following requirements:

- **Requirement 11.1**: Provides Mock_Objects for database connections (via file service)
- **Requirement 11.2**: Provides Mock_Objects for email services
- **Requirement 11.3**: Provides Mock_Objects for file system operations
- **Requirement 11.4**: Provides Mock_Objects for external API calls (WebSocket)

## Related Documentation

- [TestDataFactory Documentation](README_TEST_DATA_FACTORY.md) - For creating test database records
- [AuthHelper Documentation](README_AUTH_HELPER.md) - For authentication in tests
- [Testing Guide](../docs/TESTING.md) - Overall testing strategy
