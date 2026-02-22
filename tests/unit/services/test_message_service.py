"""
MessageService 单元测试

测试消息验证逻辑和权限检查

需求：1.2 - 消息服务单元测试
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from app.services.message_service import MessageService
from app.models.database import Message, User


class TestMessageValidation:
    """测试消息验证逻辑"""

    def test_generate_summary_short_content(self):
        """测试短内容的摘要生成"""
        db = Mock(spec=Session)
        service = MessageService(db)

        content = "This is a short message"
        summary = service.generate_summary(content)

        assert summary == "This is a short message"

    def test_generate_summary_long_content(self):
        """测试长内容（>150字符）的摘要生成"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # 创建长于150字符的内容
        content = "A" * 200
        summary = service.generate_summary(content)

        # 应该截断到150字符 + "..."
        assert len(summary) <= 153  # 150 + "..."
        assert summary.endswith("...")

    def test_generate_summary_with_html_tags(self):
        """测试摘要生成移除HTML标签"""
        db = Mock(spec=Session)
        service = MessageService(db)

        content = "<p>This is <strong>HTML</strong> content</p>"
        summary = service.generate_summary(content)

        # HTML标签应该被移除
        assert "<p>" not in summary
        assert "<strong>" not in summary
        assert "This is HTML content" in summary

    def test_generate_summary_with_punctuation(self):
        """测试摘要生成尊重标点符号"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # 创建在150字符前有标点符号的内容
        content = "A" * 100 + "。" + "B" * 100
        summary = service.generate_summary(content)

        # 如果在位置75之后找到标点符号，应该在标点符号处截断
        if "。" in summary:
            assert summary.endswith("。")

    def test_generate_summary_with_whitespace(self):
        """测试摘要生成规范化空格"""
        db = Mock(spec=Session)
        service = MessageService(db)

        content = "This   has    multiple     spaces"
        summary = service.generate_summary(content)

        # 多个空格应该规范化为单个空格
        assert "  " not in summary
        assert summary == "This has multiple spaces"


class TestMessageCreation:
    """测试消息创建逻辑"""

    def test_create_messages_single_recipient(self):
        """测试为单个收件人创建消息"""
        db = Mock(spec=Session)
        service = MessageService(db)

        sender_id = "sender-123"
        recipient_ids = {"recipient-456"}
        title = "Test Message"
        content = "Test content"

        # Mock数据库操作
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        messages = service.create_messages(
            sender_id=sender_id, recipient_ids=recipient_ids, title=title, content=content
        )

        assert len(messages) == 1
        assert messages[0].sender_id == sender_id
        assert messages[0].recipient_id == "recipient-456"
        assert messages[0].title == title
        assert messages[0].content == content
        assert messages[0].is_read is False
        assert db.add.called
        assert db.commit.called

    def test_create_messages_multiple_recipients(self):
        """测试为多个收件人创建消息"""
        db = Mock(spec=Session)
        service = MessageService(db)

        sender_id = "sender-123"
        recipient_ids = {"recipient-1", "recipient-2", "recipient-3"}
        title = "Group Message"
        content = "Group content"

        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        messages = service.create_messages(
            sender_id=sender_id, recipient_ids=recipient_ids, title=title, content=content
        )

        assert len(messages) == 3
        recipient_ids_created = {msg.recipient_id for msg in messages}
        assert recipient_ids_created == recipient_ids

        # 所有消息应该有相同的发件人和内容
        for msg in messages:
            assert msg.sender_id == sender_id
            assert msg.title == title
            assert msg.content == content

    def test_create_messages_with_custom_summary(self):
        """Test creating message with custom summary"""
        db = Mock(spec=Session)
        service = MessageService(db)

        custom_summary = "Custom summary"

        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        messages = service.create_messages(
            sender_id="sender-123",
            recipient_ids={"recipient-456"},
            title="Title",
            content="Content",
            summary=custom_summary,
        )

        assert messages[0].summary == custom_summary

    def test_create_messages_auto_generates_summary(self):
        """Test creating message auto-generates summary if not provided"""
        db = Mock(spec=Session)
        service = MessageService(db)

        content = "This is the message content"

        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        messages = service.create_messages(
            sender_id="sender-123",
            recipient_ids={"recipient-456"},
            title="Title",
            content=content,
            summary=None,  # No summary provided
        )

        # Summary should be auto-generated from content
        assert messages[0].summary == content

    def test_create_messages_announcement_type(self):
        """Test creating announcement type message"""
        db = Mock(spec=Session)
        service = MessageService(db)

        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        messages = service.create_messages(
            sender_id="admin-123",
            recipient_ids={"user-1", "user-2"},
            title="Announcement",
            content="System announcement",
            message_type="announcement",
            broadcast_scope="all_users",
        )

        assert len(messages) == 2
        for msg in messages:
            assert msg.message_type == "announcement"
            assert msg.broadcast_scope == "all_users"

    def test_create_messages_direct_type_no_broadcast_scope(self):
        """Test direct message does not set broadcast_scope"""
        db = Mock(spec=Session)
        service = MessageService(db)

        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        messages = service.create_messages(
            sender_id="sender-123",
            recipient_ids={"recipient-456"},
            title="Direct Message",
            content="Direct content",
            message_type="direct",
            broadcast_scope="all_users",  # Should be ignored for direct messages
        )

        # Direct messages should not have broadcast_scope
        assert messages[0].broadcast_scope is None


class TestMessagePermissions:
    """Test message permission checks"""

    def test_mark_message_read_valid_recipient(self):
        """Test recipient can mark message as read"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # Create mock message
        message = Mock(spec=Message)
        message.id = "msg-123"
        message.recipient_id = "user-456"
        message.is_read = False

        service.get_message_by_id = Mock(return_value=message)
        db.commit = Mock()

        result = service.mark_message_read("msg-123", "user-456")

        assert result is True
        assert message.is_read is True
        assert db.commit.called

    def test_mark_message_read_invalid_recipient(self):
        """Test non-recipient cannot mark message as read"""
        db = Mock(spec=Session)
        service = MessageService(db)

        message = Mock(spec=Message)
        message.id = "msg-123"
        message.recipient_id = "user-456"
        message.is_read = False

        service.get_message_by_id = Mock(return_value=message)

        # Different user tries to mark as read
        result = service.mark_message_read("msg-123", "user-789")

        assert result is False
        assert message.is_read is False  # Should not be changed

    def test_mark_message_read_nonexistent_message(self):
        """Test marking nonexistent message as read returns False"""
        db = Mock(spec=Session)
        service = MessageService(db)

        service.get_message_by_id = Mock(return_value=None)

        result = service.mark_message_read("nonexistent-id", "user-123")

        assert result is False

    def test_delete_message_valid_recipient(self):
        """Test recipient can delete their message"""
        db = Mock(spec=Session)
        service = MessageService(db)

        message = Mock(spec=Message)
        message.id = "msg-123"
        message.recipient_id = "user-456"

        service.get_message_by_id = Mock(return_value=message)
        db.delete = Mock()
        db.commit = Mock()

        result = service.delete_message("msg-123", "user-456")

        assert result is True
        db.delete.assert_called_with(message)
        assert db.commit.called

    def test_delete_message_invalid_recipient(self):
        """Test non-recipient cannot delete message"""
        db = Mock(spec=Session)
        service = MessageService(db)

        message = Mock(spec=Message)
        message.id = "msg-123"
        message.recipient_id = "user-456"

        service.get_message_by_id = Mock(return_value=message)

        result = service.delete_message("msg-123", "user-789")

        assert result is False

    def test_delete_message_nonexistent(self):
        """Test deleting nonexistent message returns False"""
        db = Mock(spec=Session)
        service = MessageService(db)

        service.get_message_by_id = Mock(return_value=None)

        result = service.delete_message("nonexistent-id", "user-123")

        assert result is False

    def test_update_message_valid_recipient(self):
        """Test recipient can update their message"""
        db = Mock(spec=Session)
        service = MessageService(db)

        message = Mock(spec=Message)
        message.id = "msg-123"
        message.recipient_id = "user-456"
        message.title = "Old Title"
        message.content = "Old Content"

        service.get_message_by_id = Mock(return_value=message)
        db.commit = Mock()

        result = service.update_message("msg-123", "user-456", title="New Title", content="New Content")

        assert result is True
        assert message.title == "New Title"
        assert message.content == "New Content"
        assert db.commit.called

    def test_update_message_invalid_recipient(self):
        """Test non-recipient cannot update message"""
        db = Mock(spec=Session)
        service = MessageService(db)

        message = Mock(spec=Message)
        message.id = "msg-123"
        message.recipient_id = "user-456"
        message.title = "Original Title"

        service.get_message_by_id = Mock(return_value=message)

        result = service.update_message("msg-123", "user-789", title="Hacked Title")  # Different user

        assert result is False
        assert message.title == "Original Title"  # Should not be changed

    def test_update_message_nonexistent(self):
        """Test updating nonexistent message returns False"""
        db = Mock(spec=Session)
        service = MessageService(db)

        service.get_message_by_id = Mock(return_value=None)

        result = service.update_message("nonexistent-id", "user-123", title="New Title")

        assert result is False


class TestBroadcastMessages:
    """Test broadcast message operations"""

    def test_delete_broadcast_messages_valid_sender(self):
        """Test sender can delete broadcast messages"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # Create original message
        original_message = Mock(spec=Message)
        original_message.id = "msg-123"
        original_message.sender_id = "admin-456"
        original_message.title = "Broadcast Title"
        original_message.message_type = "announcement"
        original_message.broadcast_scope = "all_users"
        original_message.created_at = datetime(2024, 1, 1, 12, 0, 0)

        # Create related broadcast messages
        msg1 = Mock(spec=Message)
        msg1.sender_id = "admin-456"
        msg1.title = "Broadcast Title"
        msg1.message_type = "announcement"
        msg1.broadcast_scope = "all_users"
        msg1.created_at = datetime(2024, 1, 1, 12, 0, 0)

        msg2 = Mock(spec=Message)
        msg2.sender_id = "admin-456"
        msg2.title = "Broadcast Title"
        msg2.message_type = "announcement"
        msg2.broadcast_scope = "all_users"
        msg2.created_at = datetime(2024, 1, 1, 12, 0, 0)

        service.get_message_by_id = Mock(return_value=original_message)

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[msg1, msg2])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        db.delete = Mock()
        db.commit = Mock()

        count = service.delete_broadcast_messages("msg-123", "admin-456")

        assert count == 2
        assert db.delete.call_count == 2
        assert db.commit.called

    def test_delete_broadcast_messages_invalid_sender(self):
        """Test non-sender cannot delete broadcast messages"""
        db = Mock(spec=Session)
        service = MessageService(db)

        original_message = Mock(spec=Message)
        original_message.sender_id = "admin-456"

        service.get_message_by_id = Mock(return_value=original_message)

        count = service.delete_broadcast_messages("msg-123", "user-789")

        assert count == 0

    def test_delete_broadcast_messages_nonexistent(self):
        """Test deleting nonexistent broadcast returns 0"""
        db = Mock(spec=Session)
        service = MessageService(db)

        service.get_message_by_id = Mock(return_value=None)

        count = service.delete_broadcast_messages("nonexistent-id", "admin-123")

        assert count == 0

    def test_update_broadcast_messages_valid_sender(self):
        """Test sender can update broadcast messages"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # Create original message
        original_message = Mock(spec=Message)
        original_message.id = "msg-123"
        original_message.sender_id = "admin-456"
        original_message.title = "Old Title"
        original_message.message_type = "announcement"
        original_message.broadcast_scope = "all_users"
        original_message.created_at = datetime(2024, 1, 1, 12, 0, 0)

        # Create related broadcast messages
        msg1 = Mock(spec=Message)
        msg1.sender_id = "admin-456"
        msg1.title = "Old Title"
        msg1.message_type = "announcement"
        msg1.broadcast_scope = "all_users"
        msg1.created_at = datetime(2024, 1, 1, 12, 0, 0)

        msg2 = Mock(spec=Message)
        msg2.sender_id = "admin-456"
        msg2.title = "Old Title"
        msg2.message_type = "announcement"
        msg2.broadcast_scope = "all_users"
        msg2.created_at = datetime(2024, 1, 1, 12, 0, 0)

        service.get_message_by_id = Mock(return_value=original_message)

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[msg1, msg2])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)
        db.commit = Mock()

        count = service.update_broadcast_messages("msg-123", "admin-456", title="New Title", content="New Content")

        assert count == 2
        assert msg1.title == "New Title"
        assert msg1.content == "New Content"
        assert msg2.title == "New Title"
        assert msg2.content == "New Content"
        assert db.commit.called

    def test_update_broadcast_messages_invalid_sender(self):
        """Test non-sender cannot update broadcast messages"""
        db = Mock(spec=Session)
        service = MessageService(db)

        original_message = Mock(spec=Message)
        original_message.sender_id = "admin-456"

        service.get_message_by_id = Mock(return_value=original_message)

        count = service.update_broadcast_messages("msg-123", "user-789", title="Hacked Title")  # Different user

        assert count == 0

    def test_update_broadcast_messages_nonexistent(self):
        """Test updating nonexistent broadcast returns 0"""
        db = Mock(spec=Session)
        service = MessageService(db)

        service.get_message_by_id = Mock(return_value=None)

        count = service.update_broadcast_messages("nonexistent-id", "admin-123", title="New Title")

        assert count == 0


class TestExceptionHandling:
    """Test exception handling in message_service"""

    def test_get_message_by_id_database_exception(self):
        """Test database exception in get_message_by_id"""
        from sqlalchemy.exc import SQLAlchemyError

        db = Mock(spec=Session)
        service = MessageService(db)

        # Mock database exception
        mock_query = Mock()
        mock_query.filter.side_effect = SQLAlchemyError("Database error")
        db.query = Mock(return_value=mock_query)

        # Should raise exception (no exception handling in this method)
        with pytest.raises(SQLAlchemyError):
            service.get_message_by_id("msg-123")

    def test_get_user_messages_database_exception(self):
        """Test database exception in get_user_messages"""
        from sqlalchemy.exc import SQLAlchemyError

        db = Mock(spec=Session)
        service = MessageService(db)

        # Mock database exception
        mock_query = Mock()
        mock_query.filter.side_effect = SQLAlchemyError("Database error")
        db.query = Mock(return_value=mock_query)

        # Should raise exception
        with pytest.raises(SQLAlchemyError):
            service.get_user_messages("user-123")

    def test_create_messages_database_exception_on_commit(self):
        """Test database exception during commit in create_messages"""
        from sqlalchemy.exc import SQLAlchemyError

        db = Mock(spec=Session)
        service = MessageService(db)

        db.add = Mock()
        db.commit = Mock(side_effect=SQLAlchemyError("Commit failed"))
        db.refresh = Mock()

        # Should raise exception when commit fails
        with pytest.raises(SQLAlchemyError):
            service.create_messages(
                sender_id="sender-123", recipient_ids={"recipient-456"}, title="Test", content="Content"
            )

    def test_create_messages_database_exception_on_refresh(self):
        """Test database exception during refresh in create_messages"""
        from sqlalchemy.exc import SQLAlchemyError

        db = Mock(spec=Session)
        service = MessageService(db)

        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock(side_effect=SQLAlchemyError("Refresh failed"))

        # Should raise exception when refresh fails
        with pytest.raises(SQLAlchemyError):
            service.create_messages(
                sender_id="sender-123", recipient_ids={"recipient-456"}, title="Test", content="Content"
            )

    def test_mark_message_read_database_exception(self):
        """Test database exception in mark_message_read"""
        from sqlalchemy.exc import SQLAlchemyError

        db = Mock(spec=Session)
        service = MessageService(db)

        message = Mock(spec=Message)
        message.recipient_id = "user-456"

        service.get_message_by_id = Mock(return_value=message)
        db.commit = Mock(side_effect=SQLAlchemyError("Commit failed"))

        # Should raise exception
        with pytest.raises(SQLAlchemyError):
            service.mark_message_read("msg-123", "user-456")

    def test_delete_message_database_exception(self):
        """Test database exception in delete_message"""
        from sqlalchemy.exc import SQLAlchemyError

        db = Mock(spec=Session)
        service = MessageService(db)

        message = Mock(spec=Message)
        message.recipient_id = "user-456"

        service.get_message_by_id = Mock(return_value=message)
        db.delete = Mock()
        db.commit = Mock(side_effect=SQLAlchemyError("Delete failed"))

        # Should raise exception
        with pytest.raises(SQLAlchemyError):
            service.delete_message("msg-123", "user-456")

    def test_update_message_database_exception(self):
        """Test database exception in update_message"""
        from sqlalchemy.exc import SQLAlchemyError

        db = Mock(spec=Session)
        service = MessageService(db)

        message = Mock(spec=Message)
        message.recipient_id = "user-456"

        service.get_message_by_id = Mock(return_value=message)
        db.commit = Mock(side_effect=SQLAlchemyError("Update failed"))

        # Should raise exception
        with pytest.raises(SQLAlchemyError):
            service.update_message("msg-123", "user-456", title="New Title")

    def test_delete_broadcast_messages_database_exception(self):
        """Test database exception in delete_broadcast_messages"""
        from sqlalchemy.exc import SQLAlchemyError
        from datetime import datetime

        db = Mock(spec=Session)
        service = MessageService(db)

        original_message = Mock(spec=Message)
        original_message.sender_id = "admin-456"
        original_message.title = "Broadcast"
        original_message.message_type = "announcement"
        original_message.broadcast_scope = "all_users"
        original_message.created_at = datetime(2024, 1, 1, 12, 0, 0)

        service.get_message_by_id = Mock(return_value=original_message)

        # Mock query to return messages
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[original_message])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        db.delete = Mock()
        db.commit = Mock(side_effect=SQLAlchemyError("Delete failed"))

        # Should raise exception
        with pytest.raises(SQLAlchemyError):
            service.delete_broadcast_messages("msg-123", "admin-456")

    def test_update_broadcast_messages_database_exception(self):
        """Test database exception in update_broadcast_messages"""
        from sqlalchemy.exc import SQLAlchemyError
        from datetime import datetime

        db = Mock(spec=Session)
        service = MessageService(db)

        original_message = Mock(spec=Message)
        original_message.sender_id = "admin-456"
        original_message.title = "Old Title"
        original_message.message_type = "announcement"
        original_message.broadcast_scope = "all_users"
        original_message.created_at = datetime(2024, 1, 1, 12, 0, 0)

        service.get_message_by_id = Mock(return_value=original_message)

        # Mock query to return messages
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[original_message])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        db.commit = Mock(side_effect=SQLAlchemyError("Update failed"))

        # Should raise exception
        with pytest.raises(SQLAlchemyError):
            service.update_broadcast_messages("msg-123", "admin-456", title="New Title")


class TestValidationFailures:
    """Test validation failures and edge cases"""

    def test_create_messages_empty_recipient_ids(self):
        """Test creating messages with empty recipient list"""
        db = Mock(spec=Session)
        service = MessageService(db)

        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        messages = service.create_messages(
            sender_id="sender-123", recipient_ids=set(), title="Test", content="Content"  # Empty set
        )

        # Should return empty list
        assert messages == []
        # add should not be called for empty list
        assert not db.add.called
        # commit is still called even with empty list (current implementation)
        assert db.commit.called

    def test_create_messages_with_empty_content(self):
        """Test creating messages with empty content"""
        db = Mock(spec=Session)
        service = MessageService(db)

        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()

        messages = service.create_messages(
            sender_id="sender-123", recipient_ids={"recipient-456"}, title="Test", content=""  # Empty content
        )

        # Should still create message with empty content
        assert len(messages) == 1
        assert messages[0].content == ""

    def test_generate_summary_empty_content(self):
        """Test generating summary from empty content"""
        db = Mock(spec=Session)
        service = MessageService(db)

        summary = service.generate_summary("")

        assert summary == ""

    def test_generate_summary_only_html_tags(self):
        """Test generating summary from content with only HTML tags"""
        db = Mock(spec=Session)
        service = MessageService(db)

        content = "<p></p><div></div>"
        summary = service.generate_summary(content)

        # After removing HTML tags and whitespace, should be empty
        assert summary == ""

    def test_update_message_with_empty_summary(self):
        """Test updating message with empty summary (should be allowed)"""
        db = Mock(spec=Session)
        service = MessageService(db)

        message = Mock(spec=Message)
        message.recipient_id = "user-456"
        message.summary = "Old summary"

        service.get_message_by_id = Mock(return_value=message)
        db.commit = Mock()

        result = service.update_message("msg-123", "user-456", summary="")  # Empty string should be allowed

        assert result is True
        assert message.summary == ""

    def test_update_message_no_fields_to_update(self):
        """Test updating message with no fields specified"""
        db = Mock(spec=Session)
        service = MessageService(db)

        message = Mock(spec=Message)
        message.recipient_id = "user-456"
        message.title = "Original Title"
        message.content = "Original Content"

        service.get_message_by_id = Mock(return_value=message)
        db.commit = Mock()

        result = service.update_message("msg-123", "user-456")

        # Should still return True and commit
        assert result is True
        assert message.title == "Original Title"
        assert message.content == "Original Content"
        assert db.commit.called


class TestMessageRetrieval:
    """Test message retrieval logic"""

    def test_get_message_by_id(self):
        """Test getting message by ID"""
        db = Mock(spec=Session)
        service = MessageService(db)

        expected_message = Mock(spec=Message)
        expected_message.id = "msg-123"

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first = Mock(return_value=expected_message)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        message = service.get_message_by_id("msg-123")

        assert message == expected_message

    def test_get_user_messages_with_pagination(self):
        """Test getting user messages with pagination"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_offset = Mock()
        mock_limit = Mock()

        expected_messages = [Mock(spec=Message), Mock(spec=Message)]
        mock_limit.all = Mock(return_value=expected_messages)
        mock_offset.limit = Mock(return_value=mock_limit)
        mock_order.offset = Mock(return_value=mock_offset)
        mock_filter.order_by = Mock(return_value=mock_order)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        messages = service.get_user_messages("user-123", page=2, page_size=10)

        assert messages == expected_messages
        # Verify offset calculation: (page - 1) * page_size = (2 - 1) * 10 = 10
        mock_order.offset.assert_called_with(10)
        mock_offset.limit.assert_called_with(10)

    def test_get_conversation_messages(self):
        """Test getting conversation messages between two users"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_offset = Mock()
        mock_limit = Mock()

        expected_messages = [Mock(spec=Message)]
        mock_limit.all = Mock(return_value=expected_messages)
        mock_offset.limit = Mock(return_value=mock_limit)
        mock_order.offset = Mock(return_value=mock_offset)
        mock_filter.order_by = Mock(return_value=mock_order)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        messages = service.get_conversation_messages("user-1", "user-2", page=1, page_size=20)

        assert messages == expected_messages

    def test_get_user_messages_by_type(self):
        """Test getting user messages filtered by type"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_offset = Mock()
        mock_limit = Mock()

        expected_messages = [Mock(spec=Message)]
        mock_limit.all = Mock(return_value=expected_messages)
        mock_offset.limit = Mock(return_value=mock_limit)
        mock_order.offset = Mock(return_value=mock_offset)
        mock_filter.order_by = Mock(return_value=mock_order)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        messages = service.get_user_messages_by_type("user-123", "announcement", page=1, page_size=20)

        assert messages == expected_messages

    def test_get_all_users(self):
        """Test getting all users"""
        db = Mock(spec=Session)
        service = MessageService(db)

        expected_users = [Mock(spec=User), Mock(spec=User)]

        # Mock query chain
        mock_query = Mock()
        mock_query.all = Mock(return_value=expected_users)
        db.query = Mock(return_value=mock_query)

        users = service.get_all_users()

        assert users == expected_users
        db.query.assert_called_once_with(User)

    def test_get_users_by_ids(self):
        """Test getting users by IDs"""
        db = Mock(spec=Session)
        service = MessageService(db)

        user_ids = ["user-1", "user-2", "user-3"]
        expected_users = [Mock(spec=User), Mock(spec=User), Mock(spec=User)]

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=expected_users)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        users = service.get_users_by_ids(user_ids)

        assert users == expected_users

    def test_get_users_by_ids_empty_list(self):
        """Test getting users with empty ID list"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        users = service.get_users_by_ids([])

        assert users == []

    def test_get_broadcast_messages(self):
        """Test getting broadcast messages with deduplication"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # Create mock messages with same broadcast (same sender, title, time)
        msg1 = Mock(spec=Message)
        msg1.sender_id = "admin-1"
        msg1.title = "Broadcast 1"
        msg1.message_type = "announcement"
        msg1.broadcast_scope = "all_users"
        msg1.created_at = datetime(2024, 1, 1, 12, 0, 0)

        msg2 = Mock(spec=Message)
        msg2.sender_id = "admin-1"
        msg2.title = "Broadcast 1"
        msg2.message_type = "announcement"
        msg2.broadcast_scope = "all_users"
        msg2.created_at = datetime(2024, 1, 1, 12, 0, 0)  # Same time

        msg3 = Mock(spec=Message)
        msg3.sender_id = "admin-1"
        msg3.title = "Broadcast 2"
        msg3.message_type = "announcement"
        msg3.broadcast_scope = "all_users"
        msg3.created_at = datetime(2024, 1, 1, 13, 0, 0)  # Different time

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_order.all = Mock(return_value=[msg1, msg2, msg3])
        mock_filter.order_by = Mock(return_value=mock_order)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        messages = service.get_broadcast_messages(page=1, page_size=20)

        # Should return only 2 unique broadcasts (msg1/msg2 are same broadcast)
        assert len(messages) == 2

    def test_get_broadcast_messages_pagination(self):
        """Test broadcast messages pagination"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # Create 5 unique broadcasts
        messages = []
        for i in range(5):
            msg = Mock(spec=Message)
            msg.sender_id = "admin-1"
            msg.title = f"Broadcast {i}"
            msg.message_type = "announcement"
            msg.broadcast_scope = "all_users"
            msg.created_at = datetime(2024, 1, 1, 12, i, 0)
            messages.append(msg)

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_order.all = Mock(return_value=messages)
        mock_filter.order_by = Mock(return_value=mock_order)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        # Get page 2 with page_size 2
        result = service.get_broadcast_messages(page=2, page_size=2)

        # Should return messages at index 2 and 3
        assert len(result) == 2

    def test_get_broadcast_message_stats(self):
        """Test getting broadcast message statistics"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # Create original message
        original_message = Mock(spec=Message)
        original_message.id = "msg-123"
        original_message.sender_id = "admin-1"
        original_message.title = "Broadcast"
        original_message.message_type = "announcement"
        original_message.broadcast_scope = "all_users"
        original_message.created_at = datetime(2024, 1, 1, 12, 0, 0)

        # Create related messages (2 read, 1 unread)
        msg1 = Mock(spec=Message)
        msg1.sender_id = "admin-1"
        msg1.title = "Broadcast"
        msg1.message_type = "announcement"
        msg1.broadcast_scope = "all_users"
        msg1.created_at = datetime(2024, 1, 1, 12, 0, 0)
        msg1.is_read = True

        msg2 = Mock(spec=Message)
        msg2.sender_id = "admin-1"
        msg2.title = "Broadcast"
        msg2.message_type = "announcement"
        msg2.broadcast_scope = "all_users"
        msg2.created_at = datetime(2024, 1, 1, 12, 0, 0)
        msg2.is_read = True

        msg3 = Mock(spec=Message)
        msg3.sender_id = "admin-1"
        msg3.title = "Broadcast"
        msg3.message_type = "announcement"
        msg3.broadcast_scope = "all_users"
        msg3.created_at = datetime(2024, 1, 1, 12, 0, 0)
        msg3.is_read = False

        service.get_message_by_id = Mock(return_value=original_message)

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all = Mock(return_value=[msg1, msg2, msg3])
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        stats = service.get_broadcast_message_stats("msg-123")

        assert stats["total_sent"] == 3
        assert stats["total_read"] == 2
        assert stats["total_unread"] == 1

    def test_get_broadcast_message_stats_nonexistent(self):
        """Test getting stats for nonexistent broadcast"""
        db = Mock(spec=Session)
        service = MessageService(db)

        service.get_message_by_id = Mock(return_value=None)

        stats = service.get_broadcast_message_stats("nonexistent-id")

        assert stats["total_sent"] == 0
        assert stats["total_read"] == 0
        assert stats["total_unread"] == 0

    def test_count_broadcast_messages(self):
        """Test counting total broadcast messages"""
        db = Mock(spec=Session)
        service = MessageService(db)

        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.count = Mock(return_value=42)
        mock_query.filter = Mock(return_value=mock_filter)
        db.query = Mock(return_value=mock_query)

        count = service.count_broadcast_messages()

        assert count == 42
