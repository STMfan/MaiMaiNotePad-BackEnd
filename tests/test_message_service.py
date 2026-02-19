"""
Unit tests for message service
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from app.services.message_service import MessageService
from app.models.database import Message, User


class TestMessageService:
    """Test cases for MessageService"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return MagicMock(spec=Session)

    @pytest.fixture
    def message_service(self, mock_db):
        """Create MessageService instance with mock database"""
        return MessageService(mock_db)

    @pytest.fixture
    def sample_message(self):
        """Create a sample message object"""
        return Message(
            id=str(uuid.uuid4()),
            sender_id=str(uuid.uuid4()),
            recipient_id=str(uuid.uuid4()),
            title="Test Message",
            content="Test Content",
            summary="Test Summary",
            message_type="direct",
            is_read=False,
            created_at=datetime.now()
        )

    def test_get_message_by_id_success(self, message_service, mock_db, sample_message):
        """Test successful message retrieval by ID"""
        mock_db.query().filter().first.return_value = sample_message
        
        result = message_service.get_message_by_id(sample_message.id)
        
        assert result == sample_message

    def test_get_message_by_id_not_found(self, message_service, mock_db):
        """Test message retrieval when not found"""
        mock_db.query().filter().first.return_value = None
        
        result = message_service.get_message_by_id("nonexistent_id")
        
        assert result is None

    def test_get_user_messages(self, message_service, mock_db, sample_message):
        """Test getting user messages with pagination"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_message]
        mock_db.query.return_value = mock_query
        
        result = message_service.get_user_messages(sample_message.recipient_id, page=1, page_size=20)
        
        assert len(result) == 1
        assert result[0] == sample_message

    def test_get_conversation_messages(self, message_service, mock_db, sample_message):
        """Test getting conversation messages between two users"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_message]
        mock_db.query.return_value = mock_query
        
        result = message_service.get_conversation_messages(
            sample_message.sender_id,
            sample_message.recipient_id,
            page=1,
            page_size=20
        )
        
        assert len(result) == 1
        assert result[0] == sample_message

    def test_get_user_messages_by_type(self, message_service, mock_db, sample_message):
        """Test getting user messages filtered by type"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_message]
        mock_db.query.return_value = mock_query
        
        result = message_service.get_user_messages_by_type(
            sample_message.recipient_id,
            "direct",
            page=1,
            page_size=20
        )
        
        assert len(result) == 1
        assert result[0] == sample_message

    def test_generate_summary_short_content(self, message_service):
        """Test summary generation for short content"""
        content = "This is a short message"
        
        result = message_service.generate_summary(content)
        
        assert result == content

    def test_generate_summary_long_content(self, message_service):
        """Test summary generation for long content"""
        content = "A" * 200
        
        result = message_service.generate_summary(content)
        
        assert len(result) <= 153  # 150 + "..."
        assert result.endswith("...")

    def test_generate_summary_html_removal(self, message_service):
        """Test that HTML tags are removed from summary"""
        content = "<p>This is <strong>HTML</strong> content</p>"
        
        result = message_service.generate_summary(content)
        
        assert "<p>" not in result
        assert "<strong>" not in result
        assert "This is HTML content" in result

    def test_create_messages_success(self, message_service, mock_db):
        """Test successful message creation"""
        sender_id = str(uuid.uuid4())
        recipient_ids = {str(uuid.uuid4()), str(uuid.uuid4())}
        
        result = message_service.create_messages(
            sender_id=sender_id,
            recipient_ids=recipient_ids,
            title="Test Title",
            content="Test Content"
        )
        
        assert len(result) == 2
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_called_once()

    def test_create_messages_with_custom_summary(self, message_service, mock_db):
        """Test message creation with custom summary"""
        sender_id = str(uuid.uuid4())
        recipient_ids = {str(uuid.uuid4())}
        custom_summary = "Custom Summary"
        
        result = message_service.create_messages(
            sender_id=sender_id,
            recipient_ids=recipient_ids,
            title="Test Title",
            content="Test Content",
            summary=custom_summary
        )
        
        assert len(result) == 1
        assert result[0].summary == custom_summary

    def test_create_messages_announcement_type(self, message_service, mock_db):
        """Test creating announcement messages"""
        sender_id = str(uuid.uuid4())
        recipient_ids = {str(uuid.uuid4())}
        
        result = message_service.create_messages(
            sender_id=sender_id,
            recipient_ids=recipient_ids,
            title="Announcement",
            content="Important announcement",
            message_type="announcement",
            broadcast_scope="all_users"
        )
        
        assert len(result) == 1
        assert result[0].message_type == "announcement"
        assert result[0].broadcast_scope == "all_users"

    def test_mark_message_read_success(self, message_service, mock_db, sample_message):
        """Test successfully marking message as read"""
        mock_db.query().filter().first.return_value = sample_message
        
        result = message_service.mark_message_read(sample_message.id, sample_message.recipient_id)
        
        assert result is True
        assert sample_message.is_read is True
        mock_db.commit.assert_called_once()

    def test_mark_message_read_wrong_user(self, message_service, mock_db, sample_message):
        """Test marking message as read by wrong user"""
        mock_db.query().filter().first.return_value = sample_message
        
        result = message_service.mark_message_read(sample_message.id, str(uuid.uuid4()))
        
        assert result is False
        mock_db.commit.assert_not_called()

    def test_mark_message_read_not_found(self, message_service, mock_db):
        """Test marking non-existent message as read"""
        mock_db.query().filter().first.return_value = None
        
        result = message_service.mark_message_read("nonexistent_id", str(uuid.uuid4()))
        
        assert result is False

    def test_delete_message_success(self, message_service, mock_db, sample_message):
        """Test successfully deleting message"""
        mock_db.query().filter().first.return_value = sample_message
        
        result = message_service.delete_message(sample_message.id, sample_message.recipient_id)
        
        assert result is True
        mock_db.delete.assert_called_once_with(sample_message)
        mock_db.commit.assert_called_once()

    def test_delete_message_wrong_user(self, message_service, mock_db, sample_message):
        """Test deleting message by wrong user"""
        mock_db.query().filter().first.return_value = sample_message
        
        result = message_service.delete_message(sample_message.id, str(uuid.uuid4()))
        
        assert result is False
        mock_db.delete.assert_not_called()

    def test_delete_message_not_found(self, message_service, mock_db):
        """Test deleting non-existent message"""
        mock_db.query().filter().first.return_value = None
        
        result = message_service.delete_message("nonexistent_id", str(uuid.uuid4()))
        
        assert result is False

    def test_update_message_success(self, message_service, mock_db, sample_message):
        """Test successfully updating message"""
        mock_db.query().filter().first.return_value = sample_message
        
        result = message_service.update_message(
            message_id=sample_message.id,
            user_id=sample_message.recipient_id,
            title="Updated Title",
            content="Updated Content"
        )
        
        assert result is True
        assert sample_message.title == "Updated Title"
        assert sample_message.content == "Updated Content"
        mock_db.commit.assert_called_once()

    def test_update_message_wrong_user(self, message_service, mock_db, sample_message):
        """Test updating message by wrong user"""
        mock_db.query().filter().first.return_value = sample_message
        
        result = message_service.update_message(
            message_id=sample_message.id,
            user_id=str(uuid.uuid4()),
            title="Updated Title"
        )
        
        assert result is False
        mock_db.commit.assert_not_called()

    def test_delete_broadcast_messages_success(self, message_service, mock_db, sample_message):
        """Test successfully deleting broadcast messages"""
        sample_message.message_type = "announcement"
        sample_message.broadcast_scope = "all_users"
        
        # Create multiple messages with same broadcast
        messages = [sample_message]
        for _ in range(2):
            msg = Message(
                id=str(uuid.uuid4()),
                sender_id=sample_message.sender_id,
                recipient_id=str(uuid.uuid4()),
                title=sample_message.title,
                content=sample_message.content,
                message_type="announcement",
                broadcast_scope="all_users",
                created_at=sample_message.created_at
            )
            messages.append(msg)
        
        mock_db.query().filter().first.return_value = sample_message
        mock_db.query().filter().all.return_value = messages
        
        result = message_service.delete_broadcast_messages(sample_message.id, sample_message.sender_id)
        
        assert result == 3
        assert mock_db.delete.call_count == 3
        mock_db.commit.assert_called_once()

    def test_delete_broadcast_messages_wrong_sender(self, message_service, mock_db, sample_message):
        """Test deleting broadcast messages by wrong sender"""
        mock_db.query().filter().first.return_value = sample_message
        
        result = message_service.delete_broadcast_messages(sample_message.id, str(uuid.uuid4()))
        
        assert result == 0
        mock_db.delete.assert_not_called()

    def test_update_broadcast_messages_success(self, message_service, mock_db, sample_message):
        """Test successfully updating broadcast messages"""
        sample_message.message_type = "announcement"
        sample_message.broadcast_scope = "all_users"
        
        # Create multiple messages with same broadcast
        messages = [sample_message]
        for _ in range(2):
            msg = Message(
                id=str(uuid.uuid4()),
                sender_id=sample_message.sender_id,
                recipient_id=str(uuid.uuid4()),
                title=sample_message.title,
                content=sample_message.content,
                message_type="announcement",
                broadcast_scope="all_users",
                created_at=sample_message.created_at
            )
            messages.append(msg)
        
        mock_db.query().filter().first.return_value = sample_message
        mock_db.query().filter().all.return_value = messages
        
        result = message_service.update_broadcast_messages(
            message_id=sample_message.id,
            sender_id=sample_message.sender_id,
            title="Updated Title"
        )
        
        assert result == 3
        for msg in messages:
            assert msg.title == "Updated Title"
        mock_db.commit.assert_called_once()

    def test_get_broadcast_message_stats(self, message_service, mock_db, sample_message):
        """Test getting broadcast message statistics"""
        sample_message.message_type = "announcement"
        sample_message.broadcast_scope = "all_users"
        
        # Create messages with different read statuses
        messages = [sample_message]
        for i in range(4):
            msg = Message(
                id=str(uuid.uuid4()),
                sender_id=sample_message.sender_id,
                recipient_id=str(uuid.uuid4()),
                title=sample_message.title,
                content=sample_message.content,
                message_type="announcement",
                broadcast_scope="all_users",
                created_at=sample_message.created_at,
                is_read=(i < 2)  # First 2 are read
            )
            messages.append(msg)
        
        mock_db.query().filter().first.return_value = sample_message
        mock_db.query().filter().all.return_value = messages
        
        result = message_service.get_broadcast_message_stats(sample_message.id)
        
        assert result["total_sent"] == 5
        assert result["total_read"] == 2
        assert result["total_unread"] == 3

    def test_get_all_users(self, message_service, mock_db):
        """Test getting all users"""
        mock_users = [
            User(id=str(uuid.uuid4()), username="user1"),
            User(id=str(uuid.uuid4()), username="user2")
        ]
        mock_db.query().all.return_value = mock_users
        
        result = message_service.get_all_users()
        
        assert len(result) == 2
        assert result[0].username == "user1"

    def test_get_users_by_ids(self, message_service, mock_db):
        """Test getting users by IDs"""
        user_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        mock_users = [
            User(id=user_ids[0], username="user1"),
            User(id=user_ids[1], username="user2")
        ]
        mock_db.query().filter().all.return_value = mock_users
        
        result = message_service.get_users_by_ids(user_ids)
        
        assert len(result) == 2

    def test_get_user_messages_empty(self, message_service, mock_db):
        """Test getting user messages when none exist"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query
        
        result = message_service.get_user_messages(str(uuid.uuid4()), page=1, page_size=20)
        
        assert len(result) == 0

    def test_get_conversation_messages_empty(self, message_service, mock_db):
        """Test getting conversation messages when none exist"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query
        
        result = message_service.get_conversation_messages(
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            page=1,
            page_size=20
        )
        
        assert len(result) == 0

    def test_generate_summary_with_newlines(self, message_service):
        """Test summary generation with newlines"""
        content = "Line 1\nLine 2\nLine 3"
        
        result = message_service.generate_summary(content)
        
        assert "Line 1" in result

    def test_generate_summary_empty_content(self, message_service):
        """Test summary generation with empty content"""
        result = message_service.generate_summary("")
        
        assert result == ""

    def test_create_messages_single_recipient(self, message_service, mock_db):
        """Test creating message for single recipient"""
        sender_id = str(uuid.uuid4())
        recipient_ids = {str(uuid.uuid4())}
        
        result = message_service.create_messages(
            sender_id=sender_id,
            recipient_ids=recipient_ids,
            title="Test Title",
            content="Test Content"
        )
        
        assert len(result) == 1
        assert result[0].sender_id == sender_id

    def test_create_messages_empty_recipients(self, message_service, mock_db):
        """Test creating messages with empty recipient list"""
        sender_id = str(uuid.uuid4())
        recipient_ids = set()
        
        result = message_service.create_messages(
            sender_id=sender_id,
            recipient_ids=recipient_ids,
            title="Test Title",
            content="Test Content"
        )
        
        assert len(result) == 0

    def test_mark_message_read_already_read(self, message_service, mock_db, sample_message):
        """Test marking already read message as read"""
        sample_message.is_read = True
        mock_db.query().filter().first.return_value = sample_message
        
        result = message_service.mark_message_read(sample_message.id, sample_message.recipient_id)
        
        assert result is True
        assert sample_message.is_read is True

    def test_update_message_not_found(self, message_service, mock_db):
        """Test updating non-existent message"""
        mock_db.query().filter().first.return_value = None
        
        result = message_service.update_message(
            message_id="nonexistent",
            user_id=str(uuid.uuid4()),
            title="Updated Title"
        )
        
        assert result is False

    def test_update_message_only_title(self, message_service, mock_db, sample_message):
        """Test updating only message title"""
        mock_db.query().filter().first.return_value = sample_message
        original_content = sample_message.content
        
        result = message_service.update_message(
            message_id=sample_message.id,
            user_id=sample_message.recipient_id,
            title="New Title"
        )
        
        assert result is True
        assert sample_message.title == "New Title"
        assert sample_message.content == original_content

    def test_update_message_only_content(self, message_service, mock_db, sample_message):
        """Test updating only message content"""
        mock_db.query().filter().first.return_value = sample_message
        original_title = sample_message.title
        
        result = message_service.update_message(
            message_id=sample_message.id,
            user_id=sample_message.recipient_id,
            content="New Content"
        )
        
        assert result is True
        assert sample_message.title == original_title
        assert sample_message.content == "New Content"

    def test_delete_broadcast_messages_not_broadcast(self, message_service, mock_db, sample_message):
        """Test deleting broadcast messages for non-broadcast message"""
        sample_message.message_type = "direct"
        mock_db.query().filter().first.return_value = sample_message
        
        result = message_service.delete_broadcast_messages(sample_message.id, sample_message.sender_id)
        
        assert result == 0

    def test_update_broadcast_messages_not_found(self, message_service, mock_db):
        """Test updating broadcast messages when original not found"""
        mock_db.query().filter().first.return_value = None
        
        result = message_service.update_broadcast_messages(
            message_id="nonexistent",
            sender_id=str(uuid.uuid4()),
            title="Updated Title"
        )
        
        assert result == 0

    def test_get_broadcast_message_stats_not_found(self, message_service, mock_db):
        """Test getting broadcast stats when message not found"""
        mock_db.query().filter().first.return_value = None
        
        result = message_service.get_broadcast_message_stats("nonexistent")
        
        assert result is None or result["total_sent"] == 0

    def test_get_broadcast_message_stats_all_read(self, message_service, mock_db, sample_message):
        """Test broadcast stats when all messages are read"""
        sample_message.message_type = "announcement"
        sample_message.is_read = True
        
        messages = [sample_message]
        for _ in range(4):
            msg = Message(
                id=str(uuid.uuid4()),
                sender_id=sample_message.sender_id,
                recipient_id=str(uuid.uuid4()),
                title=sample_message.title,
                content=sample_message.content,
                message_type="announcement",
                broadcast_scope="all_users",
                created_at=sample_message.created_at,
                is_read=True
            )
            messages.append(msg)
        
        mock_db.query().filter().first.return_value = sample_message
        mock_db.query().filter().all.return_value = messages
        
        result = message_service.get_broadcast_message_stats(sample_message.id)
        
        assert result["total_sent"] == 5
        assert result["total_read"] == 5
        assert result["total_unread"] == 0

    def test_get_all_users_empty(self, message_service, mock_db):
        """Test getting all users when none exist"""
        mock_db.query().all.return_value = []
        
        result = message_service.get_all_users()
        
        assert len(result) == 0

    def test_get_users_by_ids_empty(self, message_service, mock_db):
        """Test getting users by empty ID list"""
        mock_db.query().filter().all.return_value = []
        
        result = message_service.get_users_by_ids([])
        
        assert len(result) == 0
