"""
Integration tests for message routes
Tests message creation, retrieval, management, and broadcasting

Requirements: 1.3, 2.5 - Message routes coverage
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.database import Message
from tests.test_data_factory import TestDataFactory


class TestCreateMessage:
    """Test POST /api/messages/send endpoint"""
    
    def test_send_direct_message_to_single_recipient(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test sending a direct message to a single recipient"""
        recipient = factory.create_user(username="recipient1")
        
        message_data = {
            "title": "Test Message",
            "content": "This is a test message",
            "message_type": "direct",
            "recipient_id": recipient.id
        }
        
        response = authenticated_client.post("/api/messages/messages/send", json=message_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "消息发送成功"
        assert data["data"]["status"] == "sent"
        assert data["data"]["count"] == 1
        assert len(data["data"]["message_ids"]) == 1
        
        # Verify message was created in database
        message_id = data["data"]["message_ids"][0]
        message = test_db.query(Message).filter(Message.id == message_id).first()
        assert message is not None
        assert message.title == "Test Message"
        assert message.content == "This is a test message"
        assert message.recipient_id == recipient.id
        assert message.sender_id == test_user.id
        assert message.message_type == "direct"
        assert message.is_read is False
    
    def test_send_direct_message_to_multiple_recipients(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test sending a direct message to multiple recipients"""
        recipient1 = factory.create_user(username="recipient1")
        recipient2 = factory.create_user(username="recipient2")
        recipient3 = factory.create_user(username="recipient3")
        
        message_data = {
            "title": "Group Message",
            "content": "Message to multiple users",
            "message_type": "direct",
            "recipient_ids": [recipient1.id, recipient2.id, recipient3.id]
        }
        
        response = authenticated_client.post("/api/messages/messages/send", json=message_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["count"] == 3
        assert len(data["data"]["message_ids"]) == 3
        
        # Verify all messages were created
        for recipient in [recipient1, recipient2, recipient3]:
            message = test_db.query(Message).filter(
                Message.recipient_id == recipient.id,
                Message.title == "Group Message"
            ).first()
            assert message is not None
            assert message.sender_id == test_user.id
    
    def test_send_message_with_summary(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test sending a message with a custom summary"""
        recipient = factory.create_user()
        
        message_data = {
            "title": "Important Update",
            "content": "This is a very long message content that needs a summary...",
            "summary": "Important update summary",
            "message_type": "direct",
            "recipient_id": recipient.id
        }
        
        response = authenticated_client.post("/api/messages/messages/send", json=message_data)
        
        assert response.status_code == 200
        message_id = response.json()["data"]["message_ids"][0]
        message = test_db.query(Message).filter(Message.id == message_id).first()
        assert message.summary == "Important update summary"
    
    def test_send_message_empty_title_fails(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test sending message with empty title fails"""
        from tests.conftest import assert_error_response
        recipient = factory.create_user()
        
        message_data = {
            "title": "",
            "content": "Test content",
            "message_type": "direct",
            "recipient_id": recipient.id
        }
        
        response = authenticated_client.post("/api/messages/messages/send", json=message_data)
        
        assert_error_response(response, 422, ["消息标题", "填写"])
    
    def test_send_message_empty_content_fails(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test sending message with empty content fails"""
        from tests.conftest import assert_error_response
        recipient = factory.create_user()
        
        message_data = {
            "title": "Test Title",
            "content": "",
            "message_type": "direct",
            "recipient_id": recipient.id
        }
        
        response = authenticated_client.post("/api/messages/messages/send", json=message_data)
        
        assert_error_response(response, 422, ["消息内容", "填写"])
    
    def test_send_message_no_recipient_fails(self, authenticated_client, test_db: Session):
        """Test sending direct message without recipient fails"""
        from tests.conftest import assert_error_response
        message_data = {
            "title": "Test Title",
            "content": "Test content",
            "message_type": "direct"
        }
        
        response = authenticated_client.post("/api/messages/messages/send", json=message_data)
        
        assert_error_response(response, 422, ["recipient", "接收者", "required", "field"])
    
    def test_send_message_nonexistent_recipient_fails(self, authenticated_client, test_db: Session):
        """Test sending message to nonexistent recipient fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        message_data = {
            "title": "Test Title",
            "content": "Test content",
            "message_type": "direct",
            "recipient_id": fake_id
        }
        
        response = authenticated_client.post("/api/messages/messages/send", json=message_data)
        
        assert response.status_code == 404
        data = response.json()
        assert "接收者不存在" in data["error"]["message"]
    
    def test_send_message_unauthenticated_fails(self, test_db: Session, factory: TestDataFactory):
        """Test unauthenticated user cannot send messages"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        recipient = factory.create_user()
        
        message_data = {
            "title": "Test Title",
            "content": "Test content",
            "message_type": "direct",
            "recipient_id": recipient.id
        }
        
        response = client.post("/api/messages/messages/send", json=message_data)
        
        assert response.status_code == 401


class TestGetMessages:
    """Test GET /api/messages endpoint"""
    
    def test_get_user_messages(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test getting all messages for current user"""
        sender = factory.create_user(username="sender1")
        
        # Create messages to test user
        message1 = factory.create_message(recipient=test_user, sender=sender, title="Message 1")
        message2 = factory.create_message(recipient=test_user, sender=sender, title="Message 2")
        
        response = authenticated_client.get("/api/messages/messages")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "消息列表获取成功"
        messages = data["data"]
        
        # Verify messages are returned
        assert len(messages) >= 2
        message_titles = [m["title"] for m in messages]
        assert "Message 1" in message_titles
        assert "Message 2" in message_titles
        
        # Verify message structure
        message = messages[0]
        assert "id" in message
        assert "sender_id" in message
        assert "recipient_id" in message
        assert "title" in message
        assert "content" in message
        assert "message_type" in message
        assert "is_read" in message
        assert "created_at" in message
    
    def test_get_messages_with_pagination(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test getting messages with pagination"""
        sender = factory.create_user()
        
        # Create multiple messages
        for i in range(5):
            factory.create_message(recipient=test_user, sender=sender, title=f"Message {i}")
        
        # Get first page
        response = authenticated_client.get("/api/messages/messages?page=1&page_size=2")
        
        assert response.status_code == 200
        data = response.json()
        messages = data["data"]
        assert len(messages) <= 2
    
    def test_get_conversation_messages(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test getting messages from conversation with specific user"""
        other_user = factory.create_user(username="other_user")
        third_user = factory.create_user(username="third_user")
        
        # Create messages between test_user and other_user
        message1 = factory.create_message(recipient=test_user, sender=other_user, title="From other")
        message2 = factory.create_message(recipient=other_user, sender=test_user, title="To other")
        
        # Create message from third user (should not appear)
        message3 = factory.create_message(recipient=test_user, sender=third_user, title="From third")
        
        response = authenticated_client.get(f"/api/messages/messages?other_user_id={other_user.id}")
        
        assert response.status_code == 200
        messages = response.json()["data"]
        
        # Should only contain messages between test_user and other_user
        message_titles = [m["title"] for m in messages]
        assert "From other" in message_titles or "To other" in message_titles
        # Third user message should not appear
        assert "From third" not in message_titles
    
    def test_get_messages_invalid_pagination_fails(self, authenticated_client, test_db: Session):
        """Test getting messages with invalid pagination parameters fails"""
        from tests.conftest import assert_error_response
        response = authenticated_client.get("/api/messages/messages?page=0&page_size=20")
        
        assert_error_response(response, 422, ["page", "page_size", "大于", "0"])
    
    def test_get_messages_page_size_too_large_fails(self, authenticated_client, test_db: Session):
        """Test getting messages with page_size > 100 fails"""
        from tests.conftest import assert_error_response
        response = authenticated_client.get("/api/messages/messages?page=1&page_size=101")
        
        assert_error_response(response, 422, ["page_size", "100"])
    
    def test_get_messages_empty_list(self, authenticated_client, test_db: Session):
        """Test getting messages when user has no messages returns empty list"""
        response = authenticated_client.get("/api/messages/messages")
        
        assert response.status_code == 200
        data = response.json()
        # May have messages from other tests, but should be a list
        assert isinstance(data["data"], list)


class TestGetMessageDetail:
    """Test GET /api/messages/{message_id} endpoint"""
    
    def test_get_message_detail(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test getting message detail"""
        sender = factory.create_user()
        message = factory.create_message(
            recipient=test_user,
            sender=sender,
            title="Test Message",
            content="Test content",
            summary="Test summary"
        )
        
        response = authenticated_client.get(f"/api/messages/messages/{message.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "消息详情获取成功"
        message_data = data["data"]
        
        assert message_data["id"] == message.id
        assert message_data["title"] == "Test Message"
        assert message_data["content"] == "Test content"
        assert message_data["summary"] == "Test summary"
        assert message_data["sender_id"] == sender.id
        assert message_data["recipient_id"] == test_user.id
    
    def test_get_message_detail_nonexistent_fails(self, authenticated_client, test_db: Session):
        """Test getting nonexistent message fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = authenticated_client.get(f"/api/messages/messages/{fake_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "消息不存在" in data["error"]["message"]
    
    def test_get_message_detail_unauthorized_fails(self, test_db: Session, factory: TestDataFactory):
        """Test user cannot view another user's message"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create message between two other users
        user1 = factory.create_user(username="user1", password="password123")
        user2 = factory.create_user(username="user2", password="password123")
        message = factory.create_message(recipient=user2, sender=user1)
        
        # Login as a third user
        user3 = factory.create_user(username="user3", password="password123")
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "user3", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to view message
        response = client.get(f"/api/messages/messages/{message.id}")
        
        assert response.status_code == 403
        data = response.json()
        assert "没有权限查看此消息" in data["error"]["message"]


class TestGetMessagesByType:
    """Test GET /api/messages/by-type/{message_type} endpoint"""
    
    def test_get_messages_by_type_direct(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test getting direct messages"""
        sender = factory.create_user()
        
        # Create direct and announcement messages
        direct_msg = factory.create_message(recipient=test_user, sender=sender, message_type="direct", title="Direct")
        announcement_msg = factory.create_message(recipient=test_user, sender=sender, message_type="announcement", title="Announcement")
        
        response = authenticated_client.get("/api/messages/messages/by-type/direct")
        
        assert response.status_code == 200
        messages = response.json()["data"]
        
        # Should contain direct messages
        message_titles = [m["title"] for m in messages]
        assert "Direct" in message_titles
        
        # Verify all returned messages are direct type
        for msg in messages:
            assert msg["message_type"] == "direct"
    
    def test_get_messages_by_type_announcement(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test getting announcement messages"""
        sender = factory.create_user()
        
        announcement_msg = factory.create_message(
            recipient=test_user,
            sender=sender,
            message_type="announcement",
            title="System Announcement"
        )
        
        response = authenticated_client.get("/api/messages/messages/by-type/announcement")
        
        assert response.status_code == 200
        messages = response.json()["data"]
        
        # Verify all returned messages are announcement type
        for msg in messages:
            assert msg["message_type"] == "announcement"
    
    def test_get_messages_by_type_with_pagination(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test getting messages by type with pagination"""
        sender = factory.create_user()
        
        # Create multiple direct messages
        for i in range(5):
            factory.create_message(recipient=test_user, sender=sender, message_type="direct", title=f"Direct {i}")
        
        response = authenticated_client.get("/api/messages/messages/by-type/direct?page=1&page_size=2")
        
        assert response.status_code == 200
        messages = response.json()["data"]
        assert len(messages) <= 2


class TestMarkMessageRead:
    """Test POST /api/messages/{message_id}/read endpoint"""
    
    def test_mark_message_as_read(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test marking message as read"""
        sender = factory.create_user()
        message = factory.create_message(recipient=test_user, sender=sender, is_read=False)
        
        response = authenticated_client.post(f"/api/messages/messages/{message.id}/read")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "消息已标记为已读"
        
        # Verify message is marked as read in database
        test_db.refresh(message)
        assert message.is_read is True
    
    def test_mark_already_read_message(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test marking already read message as read (idempotent)"""
        sender = factory.create_user()
        message = factory.create_message(recipient=test_user, sender=sender, is_read=True)
        
        response = authenticated_client.post(f"/api/messages/messages/{message.id}/read")
        
        assert response.status_code == 200
        test_db.refresh(message)
        assert message.is_read is True
    
    def test_mark_message_read_nonexistent_fails(self, authenticated_client, test_db: Session):
        """Test marking nonexistent message as read fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = authenticated_client.post(f"/api/messages/messages/{fake_id}/read")
        
        assert response.status_code == 404
        data = response.json()
        assert "消息不存在" in data["error"]["message"]
    
    def test_mark_message_read_unauthorized_fails(self, test_db: Session, factory: TestDataFactory):
        """Test user cannot mark another user's message as read"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create message to user1
        user1 = factory.create_user(username="user1", password="password123")
        user2 = factory.create_user(username="user2", password="password123")
        message = factory.create_message(recipient=user1, sender=user2)
        
        # Login as user2 and try to mark user1's message as read
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "user2", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        response = client.post(f"/api/messages/messages/{message.id}/read")
        
        assert response.status_code == 403
        data = response.json()
        assert "没有权限标记此消息为已读" in data["error"]["message"]



class TestUpdateMessage:
    """Test PUT /api/messages/{message_id} endpoint"""
    
    def test_update_message_title(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test updating message title"""
        sender = factory.create_user()
        message = factory.create_message(recipient=test_user, sender=sender, title="Old Title", content="Content")
        
        update_data = {
            "title": "New Title"
        }
        
        response = authenticated_client.put(f"/api/messages/messages/{message.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "消息已更新"
        assert data["data"]["updated_count"] == 1
        
        # Verify update in database
        test_db.refresh(message)
        assert message.title == "New Title"
        assert message.content == "Content"  # Content unchanged
    
    def test_update_message_content(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test updating message content"""
        sender = factory.create_user()
        message = factory.create_message(recipient=test_user, sender=sender, title="Title", content="Old Content")
        
        update_data = {
            "content": "New Content"
        }
        
        response = authenticated_client.put(f"/api/messages/messages/{message.id}", json=update_data)
        
        assert response.status_code == 200
        test_db.refresh(message)
        assert message.content == "New Content"
        assert message.title == "Title"  # Title unchanged
    
    def test_update_message_summary(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test updating message summary"""
        sender = factory.create_user()
        message = factory.create_message(recipient=test_user, sender=sender, summary="Old Summary")
        
        update_data = {
            "summary": "New Summary"
        }
        
        response = authenticated_client.put(f"/api/messages/messages/{message.id}", json=update_data)
        
        assert response.status_code == 200
        test_db.refresh(message)
        assert message.summary == "New Summary"
    
    def test_update_message_multiple_fields(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test updating multiple message fields at once"""
        sender = factory.create_user()
        message = factory.create_message(recipient=test_user, sender=sender)
        
        update_data = {
            "title": "Updated Title",
            "content": "Updated Content",
            "summary": "Updated Summary"
        }
        
        response = authenticated_client.put(f"/api/messages/messages/{message.id}", json=update_data)
        
        assert response.status_code == 200
        test_db.refresh(message)
        assert message.title == "Updated Title"
        assert message.content == "Updated Content"
        assert message.summary == "Updated Summary"
    
    def test_update_message_empty_data_fails(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test updating message with no data fails"""
        from tests.conftest import assert_error_response
        sender = factory.create_user()
        message = factory.create_message(recipient=test_user, sender=sender)
        
        update_data = {}
        
        response = authenticated_client.put(f"/api/messages/messages/{message.id}", json=update_data)
        
        assert_error_response(response, 422, ["至少", "提供", "标题", "内容", "简介"])
    
    def test_update_message_nonexistent_fails(self, authenticated_client, test_db: Session):
        """Test updating nonexistent message fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        update_data = {
            "title": "New Title"
        }
        
        response = authenticated_client.put(f"/api/messages/messages/{fake_id}", json=update_data)
        
        assert response.status_code == 404
        data = response.json()
        assert "消息不存在" in data["error"]["message"]
    
    def test_update_message_unauthorized_fails(self, test_db: Session, factory: TestDataFactory):
        """Test user cannot update another user's message"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create message to user1
        user1 = factory.create_user(username="user1", password="password123")
        user2 = factory.create_user(username="user2", password="password123")
        message = factory.create_message(recipient=user1, sender=user2)
        
        # Login as user2 and try to update user1's message
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "user2", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        update_data = {
            "title": "Hacked Title"
        }
        
        response = client.put(f"/api/messages/messages/{message.id}", json=update_data)
        
        assert response.status_code == 403
        data = response.json()
        assert "没有权限修改此消息" in data["error"]["message"]


class TestDeleteMessage:
    """Test DELETE /api/messages/{message_id} endpoint"""
    
    def test_delete_message_as_recipient(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test recipient can delete their message"""
        sender = factory.create_user()
        message = factory.create_message(recipient=test_user, sender=sender)
        message_id = message.id
        
        response = authenticated_client.delete(f"/api/messages/messages/{message_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "消息已删除"
        assert data["data"]["deleted_count"] == 1
        
        # Verify message is deleted (hard delete)
        deleted_message = test_db.query(Message).filter(Message.id == message_id).first()
        assert deleted_message is None
    
    def test_delete_message_nonexistent_fails(self, authenticated_client, test_db: Session):
        """Test deleting nonexistent message fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = authenticated_client.delete(f"/api/messages/messages/{fake_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "消息不存在" in data["error"]["message"]
    
    def test_delete_message_unauthorized_fails(self, test_db: Session, factory: TestDataFactory):
        """Test user cannot delete another user's message"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create message to user1
        user1 = factory.create_user(username="user1", password="password123")
        user2 = factory.create_user(username="user2", password="password123")
        message = factory.create_message(recipient=user1, sender=user2)
        
        # Login as user2 and try to delete user1's message
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "user2", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        response = client.delete(f"/api/messages/messages/{message.id}")
        
        assert response.status_code == 403
        data = response.json()
        assert "没有权限删除此消息" in data["error"]["message"]


class TestBroadcastMessages:
    """Test POST /api/messages/send with broadcast functionality"""
    
    def test_broadcast_to_all_users_as_admin(self, admin_client, test_db: Session, factory: TestDataFactory, admin_user):
        """Test admin can broadcast message to all users"""
        # Create some users
        user1 = factory.create_user(username="user1")
        user2 = factory.create_user(username="user2")
        user3 = factory.create_user(username="user3")
        
        message_data = {
            "title": "System Announcement",
            "content": "Important system update for all users",
            "message_type": "announcement",
            "broadcast_scope": "all_users"
        }
        
        response = admin_client.post("/api/messages/messages/send", json=message_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "sent"
        # Should create messages for all users except sender
        assert data["data"]["count"] >= 3
        
        # Verify messages were created for users
        for user in [user1, user2, user3]:
            message = test_db.query(Message).filter(
                Message.recipient_id == user.id,
                Message.title == "System Announcement"
            ).first()
            assert message is not None
            assert message.message_type == "announcement"
            assert message.broadcast_scope == "all_users"
    
    def test_broadcast_to_all_users_as_moderator(self, moderator_client, test_db: Session, factory: TestDataFactory, moderator_user):
        """Test moderator can broadcast message to all users"""
        user1 = factory.create_user(username="user1")
        user2 = factory.create_user(username="user2")
        
        message_data = {
            "title": "Moderator Announcement",
            "content": "Important announcement from moderator",
            "message_type": "announcement",
            "broadcast_scope": "all_users"
        }
        
        response = moderator_client.post("/api/messages/messages/send", json=message_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "sent"
        assert data["data"]["count"] >= 2
    
    def test_broadcast_to_all_users_as_regular_user_fails(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test regular user cannot broadcast to all users"""
        from tests.conftest import assert_error_response
        message_data = {
            "title": "Unauthorized Broadcast",
            "content": "This should fail",
            "message_type": "announcement",
            "broadcast_scope": "all_users"
        }
        
        response = authenticated_client.post("/api/messages/messages/send", json=message_data)
        
        assert_error_response(response, [400, 403], ["管理员", "审核员", "广播", "发送消息失败"])
    
    def test_broadcast_scope_requires_announcement_type(self, admin_client, test_db: Session):
        """Test broadcast_scope can only be used with announcement type"""
        from tests.conftest import assert_error_response
        message_data = {
            "title": "Test",
            "content": "Test content",
            "message_type": "direct",
            "broadcast_scope": "all_users",
            "recipient_id": "some-id"
        }
        
        response = admin_client.post("/api/messages/messages/send", json=message_data)
        
        assert_error_response(response, 422, ["公告", "类型", "广播"])
    
    def test_admin_can_delete_broadcast_announcement(self, admin_client, test_db: Session, factory: TestDataFactory, admin_user):
        """Test admin can delete their broadcast announcement"""
        # Create broadcast message
        user1 = factory.create_user(username="user1")
        user2 = factory.create_user(username="user2")
        
        message_data = {
            "title": "Deletable Announcement",
            "content": "This will be deleted",
            "message_type": "announcement",
            "broadcast_scope": "all_users"
        }
        
        response = admin_client.post("/api/messages/messages/send", json=message_data)
        assert response.status_code == 200
        message_ids = response.json()["data"]["message_ids"]
        
        # Delete the broadcast (should delete all copies)
        first_message_id = message_ids[0]
        delete_response = admin_client.delete(f"/api/messages/messages/{first_message_id}")
        
        assert delete_response.status_code == 200
        data = delete_response.json()
        # Should delete multiple messages (all copies of the broadcast)
        assert data["data"]["deleted_count"] >= 1
    
    def test_admin_can_update_broadcast_announcement(self, admin_client, test_db: Session, factory: TestDataFactory, admin_user):
        """Test admin can update their broadcast announcement"""
        # Create broadcast message
        user1 = factory.create_user(username="user1")
        
        message_data = {
            "title": "Original Announcement",
            "content": "Original content",
            "message_type": "announcement",
            "broadcast_scope": "all_users"
        }
        
        response = admin_client.post("/api/messages/messages/send", json=message_data)
        assert response.status_code == 200
        message_ids = response.json()["data"]["message_ids"]
        
        # Update the broadcast (should update all copies)
        first_message_id = message_ids[0]
        update_data = {
            "title": "Updated Announcement",
            "content": "Updated content"
        }
        
        update_response = admin_client.put(f"/api/messages/messages/{first_message_id}", json=update_data)
        
        assert update_response.status_code == 200
        data = update_response.json()
        # Should update multiple messages
        assert data["data"]["updated_count"] >= 1


class TestGetBroadcastMessages:
    """Test GET /api/admin/broadcast-messages endpoint"""
    
    def test_get_broadcast_messages_as_admin(self, admin_client, test_db: Session, factory: TestDataFactory, admin_user):
        """Test admin can get broadcast message history"""
        # Create a broadcast message
        user1 = factory.create_user(username="user1")
        
        message_data = {
            "title": "Test Broadcast",
            "content": "Test broadcast content",
            "message_type": "announcement",
            "broadcast_scope": "all_users"
        }
        
        admin_client.post("/api/messages/messages/send", json=message_data)
        
        # Get broadcast history
        response = admin_client.get("/api/messages/admin/broadcast-messages")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "广播消息历史获取成功"
        assert "data" in data
        assert "pagination" in data
        assert "total" in data["pagination"]
        assert "page" in data["pagination"]
        assert "page_size" in data["pagination"]
        
        # Verify broadcast message is in the list
        broadcasts = data["data"]
        assert len(broadcasts) >= 1
        
        # Verify broadcast structure
        broadcast = broadcasts[0]
        assert "id" in broadcast
        assert "sender_id" in broadcast
        assert "sender" in broadcast
        assert "title" in broadcast
        assert "content" in broadcast
        assert "message_type" in broadcast
        assert "broadcast_scope" in broadcast
        assert "created_at" in broadcast
        assert "stats" in broadcast
    
    def test_get_broadcast_messages_with_pagination(self, admin_client, test_db: Session, factory: TestDataFactory):
        """Test getting broadcast messages with pagination"""
        response = admin_client.get("/api/messages/admin/broadcast-messages?page=1&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 10
    
    def test_get_broadcast_messages_as_moderator(self, moderator_client, test_db: Session):
        """Test moderator can get broadcast message history"""
        response = moderator_client.get("/api/messages/admin/broadcast-messages")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    def test_get_broadcast_messages_as_regular_user_fails(self, authenticated_client, test_db: Session):
        """Test regular user cannot get broadcast message history"""
        from tests.conftest import assert_error_response
        response = authenticated_client.get("/api/messages/admin/broadcast-messages")
        
        assert_error_response(response, 403, ["管理员", "审核员", "权限"])
    
    def test_get_broadcast_messages_invalid_page_size_fails(self, admin_client, test_db: Session):
        """Test getting broadcast messages with invalid page_size fails"""
        from tests.conftest import assert_error_response
        response = admin_client.get("/api/messages/admin/broadcast-messages?page=1&page_size=101")
        
        assert_error_response(response, 422, ["page_size", "100"])


class TestWebSocketNotifications:
    """Test WebSocket notifications on message operations"""
    
    def test_websocket_notification_on_new_message(self, authenticated_client, test_db: Session, factory: TestDataFactory, mock_websocket_manager):
        """Test WebSocket notification is sent when new message is created"""
        # Note: This test verifies the WebSocket manager is called
        # Actual WebSocket connection testing would require more complex setup
        
        recipient = factory.create_user(username="recipient1")
        
        # Mock the WebSocket manager
        import unittest.mock as mock
        with mock.patch('app.api.routes.messages.message_ws_manager', mock_websocket_manager):
            message_data = {
                "title": "Test Message",
                "content": "Test content",
                "message_type": "direct",
                "recipient_id": recipient.id
            }
            
            response = authenticated_client.post("/api/messages/messages/send", json=message_data)
            
            assert response.status_code == 200
            
            # Verify WebSocket manager was called to broadcast update
            mock_websocket_manager.broadcast_user_update.assert_called_once()
    
    def test_websocket_notification_on_mark_read(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user, mock_websocket_manager):
        """Test WebSocket notification is sent when message is marked as read"""
        sender = factory.create_user()
        message = factory.create_message(recipient=test_user, sender=sender, is_read=False)
        
        import unittest.mock as mock
        with mock.patch('app.api.routes.messages.message_ws_manager', mock_websocket_manager):
            response = authenticated_client.post(f"/api/messages/messages/{message.id}/read")
            
            assert response.status_code == 200
            
            # Verify WebSocket manager was called
            mock_websocket_manager.broadcast_user_update.assert_called_once()
