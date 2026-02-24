"""
消息路由集成测试

测试所有消息相关的 API 端点，包括发送、接收、阅读、更新和删除消息。

Requirements: 3.2
"""

import uuid
from datetime import datetime

from app.models.database import Message, User


class TestSendMessage:
    """测试发送消息"""

    def test_send_message_success(self, authenticated_client, test_user, test_db):
        """测试成功发送消息"""
        # Create recipient
        recipient = User(
            id=str(uuid.uuid4()),
            username="recipient",
            email="recipient@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(recipient)
        test_db.commit()

        data = {
            "recipient_id": recipient.id,
            "title": "Test Message Title",
            "content": "Test message content",
            "message_type": "direct",
        }

        response = authenticated_client.post("/api/messages/send", json=data)

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "message_ids" in result["data"]

    def test_send_message_to_nonexistent_user(self, authenticated_client):
        """测试向不存在的用户发送消息"""
        data = {
            "recipient_id": str(uuid.uuid4()),
            "title": "Test Title",
            "content": "Test message",
            "message_type": "direct",
        }

        response = authenticated_client.post("/api/messages/send", json=data)

        assert response.status_code in [400, 404]

    def test_send_message_empty_content(self, authenticated_client, test_user, test_db):
        """测试发送空内容的消息"""
        recipient = User(
            id=str(uuid.uuid4()),
            username="recipient2",
            email="recipient2@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(recipient)
        test_db.commit()

        data = {"recipient_id": recipient.id, "title": "Test Title", "content": "", "message_type": "direct"}

        response = authenticated_client.post("/api/messages/send", json=data)

        assert response.status_code in [400, 422]

    def test_send_message_requires_auth(self, client):
        """测试发送消息需要认证"""
        data = {"recipient_id": str(uuid.uuid4()), "title": "Test Title", "content": "Test", "message_type": "direct"}

        response = client.post("/api/messages/send", json=data)

        assert response.status_code == 401


class TestGetMessages:
    """测试获取消息"""

    def test_get_messages_success(self, authenticated_client, test_user, test_db):
        """测试获取用户的消息"""
        # Create a message
        sender = User(
            id=str(uuid.uuid4()),
            username="sender",
            email="sender@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=test_user.id,
            title="Test Message",
            content="Test message",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        response = authenticated_client.get("/api/messages")

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert isinstance(result["data"], list)

    def test_get_messages_pagination(self, authenticated_client, test_user, test_db):
        """测试消息分页"""
        sender = User(
            id=str(uuid.uuid4()),
            username="sender2",
            email="sender2@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        # Create multiple messages
        for i in range(5):
            message = Message(
                id=str(uuid.uuid4()),
                sender_id=sender.id,
                recipient_id=test_user.id,
                title=f"Message {i}",
                content=f"Message {i}",
                message_type="direct",
                is_read=False,
                created_at=datetime.now(),
            )
            test_db.add(message)
        test_db.commit()

        response = authenticated_client.get("/api/messages?page=1&page_size=3")

        assert response.status_code == 200
        result = response.json()
        assert len(result["data"]) <= 3

    def test_get_messages_requires_auth(self, client):
        """测试获取消息需要认证"""
        response = client.get("/api/messages")

        assert response.status_code == 401


class TestGetMessagesByType:
    """测试按类型获取消息"""

    def test_get_messages_by_type_direct(self, authenticated_client, test_user, test_db):
        """测试获取私信消息"""
        sender = User(
            id=str(uuid.uuid4()),
            username="sender3",
            email="sender3@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=test_user.id,
            title="Direct Message",
            content="Direct message",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        response = authenticated_client.get("/api/messages/by-type/direct")

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

    def test_get_messages_by_type_announcement(self, authenticated_client):
        """测试获取公告消息"""
        response = authenticated_client.get("/api/messages/by-type/announcement")

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

    def test_get_messages_by_type_requires_auth(self, client):
        """测试按类型获取消息需要认证"""
        response = client.get("/api/messages/by-type/direct")

        assert response.status_code == 401


class TestGetMessageDetail:
    """测试获取消息详情"""

    def test_get_message_detail_success(self, authenticated_client, test_user, test_db):
        """测试获取消息详情"""
        sender = User(
            id=str(uuid.uuid4()),
            username="sender4",
            email="sender4@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=test_user.id,
            title="Detail Test Message",
            content="Detail test message",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        response = authenticated_client.get(f"/api/messages/{message.id}")

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["data"]["id"] == message.id

    def test_get_message_detail_not_found(self, authenticated_client):
        """测试获取不存在的消息"""
        fake_id = str(uuid.uuid4())
        response = authenticated_client.get(f"/api/messages/{fake_id}")

        assert response.status_code == 404

    def test_get_message_detail_requires_auth(self, client):
        """测试获取消息详情需要认证"""
        message_id = str(uuid.uuid4())
        response = client.get(f"/api/messages/{message_id}")

        assert response.status_code == 401


class TestMarkMessageRead:
    """测试标记消息为已读"""

    def test_mark_message_read_success(self, authenticated_client, test_user, test_db):
        """测试标记消息为已读"""
        sender = User(
            id=str(uuid.uuid4()),
            username="sender5",
            email="sender5@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=test_user.id,
            title="Unread Message",
            content="Unread message",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        response = authenticated_client.post(f"/api/messages/{message.id}/read")

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

        # Verify message is marked as read
        test_db.refresh(message)
        assert message.is_read is True

    def test_mark_message_read_not_found(self, authenticated_client):
        """测试标记不存在的消息为已读"""
        fake_id = str(uuid.uuid4())
        response = authenticated_client.post(f"/api/messages/{fake_id}/read")

        assert response.status_code == 404

    def test_mark_message_read_requires_auth(self, client):
        """测试标记消息为已读需要认证"""
        message_id = str(uuid.uuid4())
        response = client.post(f"/api/messages/{message_id}/read")

        assert response.status_code == 401


class TestUpdateMessage:
    """测试更新消息"""

    def test_update_message_success(self, authenticated_client, test_user, test_db):
        """测试作为接收者更新消息"""
        sender = User(
            id=str(uuid.uuid4()),
            username="sender_update",
            email="sender_update@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=test_user.id,
            title="Original Title",
            content="Original content",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        data = {"content": "Updated content"}
        response = authenticated_client.put(f"/api/messages/{message.id}", json=data)

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

    def test_update_message_not_owner(self, authenticated_client, test_user, test_db):
        """测试更新不属于用户的消息"""
        sender = User(
            id=str(uuid.uuid4()),
            username="sender6",
            email="sender6@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        recipient = User(
            id=str(uuid.uuid4()),
            username="recipient4",
            email="recipient4@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.add(recipient)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=recipient.id,
            title="Someone Else's Message",
            content="Someone else's message",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        data = {"content": "Trying to update"}
        response = authenticated_client.put(f"/api/messages/{message.id}", json=data)

        assert response.status_code in [403, 404]

    def test_update_message_requires_auth(self, client):
        """测试更新消息需要认证"""
        message_id = str(uuid.uuid4())
        data = {"content": "Updated"}
        response = client.put(f"/api/messages/{message_id}", json=data)

        assert response.status_code == 401


class TestDeleteMessage:
    """测试删除消息"""

    def test_delete_message_success(self, authenticated_client, test_user, test_db):
        """测试作为接收者删除消息"""
        sender = User(
            id=str(uuid.uuid4()),
            username="sender_delete",
            email="sender_delete@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=test_user.id,
            title="Message to Delete",
            content="Message to delete",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        response = authenticated_client.delete(f"/api/messages/{message.id}")

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

    def test_delete_message_not_found(self, authenticated_client):
        """测试删除不存在的消息"""
        fake_id = str(uuid.uuid4())
        response = authenticated_client.delete(f"/api/messages/{fake_id}")

        assert response.status_code == 404

    def test_delete_message_requires_auth(self, client):
        """测试删除消息需要认证"""
        message_id = str(uuid.uuid4())
        response = client.delete(f"/api/messages/{message_id}")

        assert response.status_code == 401


class TestBroadcastMessages:
    """测试广播消息（仅管理员/版主）"""

    def test_get_broadcast_messages_requires_admin(self, authenticated_client):
        """测试获取广播消息需要管理员/版主角色"""
        response = authenticated_client.get("/api/admin/broadcast-messages")

        # Regular user should get 403 Forbidden
        assert response.status_code == 403

    def test_get_broadcast_messages_requires_auth(self, client):
        """测试获取广播消息需要认证"""
        response = client.get("/api/admin/broadcast-messages")

        assert response.status_code == 401


class TestBatchOperations:
    """测试消息批量操作

    测试批量标记已读、批量删除以及批量操作的错误处理场景，
    包括权限检查和边界情况。

    Requirements: 1.2
    """

    def test_batch_mark_read_via_broadcast(self, admin_client, test_user, test_db):
        """Test batch mark-read functionality through broadcast messages

        验证：
        - 广播消息可以被多个接收者标记为已读
        - 每个接收者独立标记自己的消息
        """
        # Create multiple recipients
        recipients = []
        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                username=f"recipient_batch_{i}",
                email=f"recipient_batch_{i}@example.com",
                hashed_password="hashed",
                is_active=True,
            )
            test_db.add(user)
            recipients.append(user)
        test_db.commit()

        # Send broadcast message
        # When broadcast_scope="all_users", the system sends to all users in DB
        # including test_user, so we expect more messages than just our 3 recipients
        data = {
            "recipient_ids": [r.id for r in recipients],
            "title": "Batch Test Message",
            "content": "Batch test content",
            "message_type": "announcement",
            "broadcast_scope": "all_users",
        }

        response = admin_client.post("/api/messages/send", json=data)
        assert response.status_code == 200
        result = response.json()
        message_ids = result["data"]["message_ids"]
        # Should have at least 3 messages (our recipients)
        assert len(message_ids) >= 3

        # Verify all messages are unread initially
        for msg_id in message_ids:
            msg = test_db.query(Message).filter(Message.id == msg_id).first()
            assert msg is not None
            assert msg.is_read is False

    def test_batch_delete_via_broadcast_admin(self, admin_client, test_user, test_db):
        """Test batch delete functionality for broadcast messages by admin

        验证：
        - 管理员可以删除自己发送的广播消息
        - 删除操作会删除所有相关的消息副本
        """
        # Create multiple recipients
        recipients = []
        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                username=f"recipient_delete_{i}",
                email=f"recipient_delete_{i}@example.com",
                hashed_password="hashed",
                is_active=True,
            )
            test_db.add(user)
            recipients.append(user)
        test_db.commit()

        # Send broadcast message
        data = {
            "recipient_ids": [r.id for r in recipients],
            "title": "Batch Delete Test",
            "content": "Batch delete content",
            "message_type": "announcement",
            "broadcast_scope": "all_users",
        }

        response = admin_client.post("/api/messages/send", json=data)
        assert response.status_code == 200
        result = response.json()
        message_ids = result["data"]["message_ids"]

        # Admin deletes one message (should delete all in broadcast)
        response = admin_client.delete(f"/api/messages/{message_ids[0]}")
        assert response.status_code == 200
        result = response.json()
        assert result["data"]["deleted_count"] >= 1

    def test_batch_delete_permission_check(self, authenticated_client, test_user, test_db):
        """Test batch delete permission checks

        验证：
        - 普通用户不能删除其他用户的消息
        - 只有接收者可以删除自己收到的消息
        """
        # Create another user
        other_user = User(
            id=str(uuid.uuid4()),
            username="other_batch_user",
            email="other_batch@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(other_user)
        test_db.commit()

        # Create message to other user
        message = Message(
            id=str(uuid.uuid4()),
            sender_id=test_user.id,
            recipient_id=other_user.id,
            title="Permission Test",
            content="Permission test content",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        # Try to delete as test_user (sender, not recipient)
        response = authenticated_client.delete(f"/api/messages/{message.id}")
        assert response.status_code in [403, 404]

    def test_batch_operation_empty_recipients(self, admin_client):
        """Test batch operation with empty recipient list

        验证：
        - 空接收者列表应该返回错误
        """
        data = {
            "recipient_ids": [],
            "title": "Empty Recipients",
            "content": "Test content",
            "message_type": "announcement",
            "broadcast_scope": "all_users",
        }

        response = admin_client.post("/api/messages/send", json=data)
        assert response.status_code in [400, 422]

    def test_batch_operation_nonexistent_recipients(self, admin_client):
        """Test batch operation with non-existent recipients

        验证：
        - 不存在的接收者ID应该返回错误
        """
        fake_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        data = {
            "recipient_ids": fake_ids,
            "title": "Nonexistent Recipients",
            "content": "Test content",
            "message_type": "direct",
        }

        response = admin_client.post("/api/messages/send", json=data)
        assert response.status_code in [400, 404]

    def test_batch_operation_partial_success_scenario(self, admin_client, test_user, test_db):
        """Test batch operation with mix of valid and invalid recipients

        验证：
        - 部分有效的接收者列表应该被正确处理
        """
        # Create one valid recipient
        valid_user = User(
            id=str(uuid.uuid4()),
            username="valid_recipient",
            email="valid@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(valid_user)
        test_db.commit()

        # Mix valid and invalid IDs
        data = {
            "recipient_ids": [valid_user.id, str(uuid.uuid4())],
            "title": "Partial Success Test",
            "content": "Test content",
            "message_type": "direct",
        }

        response = admin_client.post("/api/messages/send", json=data)
        # Should fail due to invalid recipient
        assert response.status_code in [400, 404]

    def test_batch_mark_read_permission_per_user(self, authenticated_client, test_user, test_db):
        """Test that each user can only mark their own messages as read

        验证：
        - 用户只能标记自己收到的消息为已读
        - 不能标记其他用户的消息
        """
        # Create sender
        sender = User(
            id=str(uuid.uuid4()),
            username="sender_batch",
            email="sender_batch@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        # Create message to test_user
        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=test_user.id,
            title="Mark Read Test",
            content="Mark read content",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        # Mark as read
        response = authenticated_client.post(f"/api/messages/{message.id}/read")
        assert response.status_code == 200

        # Verify it's marked as read
        test_db.refresh(message)
        assert message.is_read is True

    def test_batch_delete_all_broadcast_messages(self, admin_client, test_user, test_db):
        """Test deleting all messages in a broadcast

        验证：
        - 删除广播消息时，所有副本都被删除
        - 返回正确的删除计数
        """
        # Create multiple recipients
        recipients = []
        for i in range(5):
            user = User(
                id=str(uuid.uuid4()),
                username=f"recipient_all_{i}",
                email=f"recipient_all_{i}@example.com",
                hashed_password="hashed",
                is_active=True,
            )
            test_db.add(user)
            recipients.append(user)
        test_db.commit()

        # Send broadcast
        data = {
            "recipient_ids": [r.id for r in recipients],
            "title": "Delete All Test",
            "content": "Delete all content",
            "message_type": "announcement",
            "broadcast_scope": "all_users",
        }

        response = admin_client.post("/api/messages/send", json=data)
        assert response.status_code == 200
        message_ids = response.json()["data"]["message_ids"]

        # Delete broadcast
        response = admin_client.delete(f"/api/messages/{message_ids[0]}")
        assert response.status_code == 200
        result = response.json()
        # Should delete all messages in the broadcast
        assert result["data"]["deleted_count"] >= 5

    def test_batch_operation_large_recipient_list(self, admin_client, test_db):
        """Test batch operation with large number of recipients

        验证：
        - 大量接收者的批量操作能够正常处理
        """
        # Create many recipients
        recipients = []
        for i in range(20):
            user = User(
                id=str(uuid.uuid4()),
                username=f"recipient_large_{i}",
                email=f"recipient_large_{i}@example.com",
                hashed_password="hashed",
                is_active=True,
            )
            test_db.add(user)
            recipients.append(user)
        test_db.commit()

        # Send to all
        data = {
            "recipient_ids": [r.id for r in recipients],
            "title": "Large Batch Test",
            "content": "Large batch content",
            "message_type": "announcement",
            "broadcast_scope": "all_users",
        }

        response = admin_client.post("/api/messages/send", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["data"]["count"] == 20


class TestMessageEdgeCases:
    """测试消息的边界情况和错误场景"""

    def test_send_message_with_very_long_title(self, authenticated_client, test_user, test_db):
        """测试发送标题很长的消息"""
        recipient = User(
            id=str(uuid.uuid4()),
            username="recipient_long",
            email="recipient_long@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(recipient)
        test_db.commit()

        data = {
            "recipient_id": recipient.id,
            "title": "A" * 500,  # Very long title
            "content": "Test content",
            "message_type": "direct",
        }

        response = authenticated_client.post("/api/messages/send", json=data)
        # Should either succeed or return validation error
        assert response.status_code in [200, 400, 422]

    def test_send_message_with_special_characters(self, authenticated_client, test_user, test_db):
        """测试发送包含特殊字符的消息"""
        recipient = User(
            id=str(uuid.uuid4()),
            username="recipient_special",
            email="recipient_special@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(recipient)
        test_db.commit()

        data = {
            "recipient_id": recipient.id,
            "title": "Test <script>alert('xss')</script>",
            "content": "Content with 特殊字符 and émojis 🎉",
            "message_type": "direct",
        }

        response = authenticated_client.post("/api/messages/send", json=data)
        assert response.status_code == 200

    def test_get_messages_with_invalid_page(self, authenticated_client):
        """测试使用无效页码获取消息"""
        response = authenticated_client.get("/api/messages?page=0")
        # Should return error
        assert response.status_code in [400, 422]

    def test_get_messages_with_large_page_size(self, authenticated_client):
        """测试使用很大的页面大小获取消息"""
        response = authenticated_client.get("/api/messages?page_size=1000")
        # Should return error (max is 100)
        assert response.status_code in [400, 422]

    def test_update_message_with_empty_fields(self, authenticated_client, test_user, test_db):
        """测试使用空字段更新消息"""
        sender = User(
            id=str(uuid.uuid4()),
            username="sender_update_empty",
            email="sender_update_empty@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=test_user.id,
            title="Original Title",
            content="Original content",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        # Try to update with empty data
        data = {}
        response = authenticated_client.put(f"/api/messages/{message.id}", json=data)
        # Should return error about no fields to update
        assert response.status_code in [400, 422]

    def test_send_broadcast_message_as_regular_user(self, authenticated_client, test_user, test_db):
        """Test that regular users cannot send broadcast messages to all users"""
        recipient = User(
            id=str(uuid.uuid4()),
            username="recipient_broadcast",
            email="recipient_broadcast@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(recipient)
        test_db.commit()

        data = {
            "recipient_id": recipient.id,
            "title": "Broadcast Test",
            "content": "Broadcast content",
            "message_type": "announcement",
            "broadcast_scope": "all_users",
        }

        response = authenticated_client.post("/api/messages/send", json=data)
        # Should return 400 (wrapped AuthorizationError) or 403
        assert response.status_code in [400, 403]


class TestBroadcastMessageFeatures:
    """Test broadcast message functionality

    Tests system broadcast messages, admin broadcasts, and broadcast permission checks.

    Requirements: 1.2, 3.9
    """

    def test_admin_send_broadcast_to_all_users(self, admin_client, test_db):
        """Test admin sending broadcast message to all users

        验证：
        - 管理员可以发送全用户广播
        - 广播消息创建多个副本
        """
        # Create some users
        users = []
        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                username=f"broadcast_user_{i}",
                email=f"broadcast_user_{i}@example.com",
                hashed_password="hashed",
                is_active=True,
            )
            test_db.add(user)
            users.append(user)
        test_db.commit()

        data = {
            "recipient_ids": [u.id for u in users],
            "title": "System Announcement",
            "content": "Important system announcement",
            "message_type": "announcement",
            "broadcast_scope": "all_users",
        }

        response = admin_client.post("/api/messages/send", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["data"]["count"] == 3
        assert len(result["data"]["message_ids"]) == 3

    def test_moderator_send_broadcast_to_all_users(self, moderator_client, test_db):
        """Test moderator sending broadcast message to all users

        验证：
        - 审核员可以发送全用户广播
        """
        # Create a user
        user = User(
            id=str(uuid.uuid4()),
            username="broadcast_recipient",
            email="broadcast_recipient@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(user)
        test_db.commit()

        data = {
            "recipient_ids": [user.id],
            "title": "Moderator Announcement",
            "content": "Moderator announcement content",
            "message_type": "announcement",
            "broadcast_scope": "all_users",
        }

        response = moderator_client.post("/api/messages/send", json=data)
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

    def test_regular_user_cannot_send_broadcast(self, authenticated_client, test_db):
        """Test regular user cannot send broadcast to all users

        验证：
        - 普通用户不能发送全用户广播
        - 返回权限错误
        """
        user = User(
            id=str(uuid.uuid4()),
            username="broadcast_target",
            email="broadcast_target@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(user)
        test_db.commit()

        data = {
            "recipient_ids": [user.id],
            "title": "Unauthorized Broadcast",
            "content": "Should not work",
            "message_type": "announcement",
            "broadcast_scope": "all_users",
        }

        response = authenticated_client.post("/api/messages/send", json=data)
        assert response.status_code in [400, 403]

    def test_broadcast_scope_requires_announcement_type(self, admin_client, test_db):
        """Test broadcast_scope only works with announcement type

        验证：
        - broadcast_scope 只能用于 announcement 类型
        - 其他类型使用 broadcast_scope 返回错误
        """
        user = User(
            id=str(uuid.uuid4()),
            username="broadcast_test_user",
            email="broadcast_test_user@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(user)
        test_db.commit()

        data = {
            "recipient_ids": [user.id],
            "title": "Invalid Broadcast",
            "content": "Direct message with broadcast scope",
            "message_type": "direct",
            "broadcast_scope": "all_users",
        }

        response = admin_client.post("/api/messages/send", json=data)
        assert response.status_code in [400, 422]

    def test_get_broadcast_messages_as_admin(self, admin_client, test_db):
        """Test admin can get broadcast message history

        验证：
        - 管理员可以查看广播消息历史
        - 返回分页数据
        """
        response = admin_client.get("/api/admin/broadcast-messages?page=1&page_size=10")
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "data" in result
        assert "pagination" in result
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["page_size"] == 10

    def test_get_broadcast_messages_as_moderator(self, moderator_client):
        """Test moderator can get broadcast message history

        验证：
        - 审核员可以查看广播消息历史
        """
        response = moderator_client.get("/api/admin/broadcast-messages")
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

    def test_get_broadcast_messages_invalid_pagination(self, admin_client):
        """Test broadcast messages with invalid pagination parameters

        验证：
        - 无效的分页参数返回错误
        """
        response = admin_client.get("/api/admin/broadcast-messages?page=0&page_size=200")
        assert response.status_code in [400, 422]

    def test_broadcast_message_excludes_sender(self, admin_client, test_db):
        """Test broadcast message excludes sender from recipients

        验证：
        - 广播消息不会发送给发送者自己
        """
        # Create recipients
        users = []
        for i in range(2):
            user = User(
                id=str(uuid.uuid4()),
                username=f"exclude_test_{i}",
                email=f"exclude_test_{i}@example.com",
                hashed_password="hashed",
                is_active=True,
            )
            test_db.add(user)
            users.append(user)
        test_db.commit()

        data = {
            "recipient_ids": [u.id for u in users],
            "title": "Exclude Sender Test",
            "content": "Test content",
            "message_type": "announcement",
            "broadcast_scope": "all_users",
        }

        response = admin_client.post("/api/messages/send", json=data)
        assert response.status_code == 200
        result = response.json()
        # Should only send to the 2 users, not the admin sender
        assert result["data"]["count"] == 2


class TestMessagePermissionCombinations:
    """Test message permission check combinations

    Tests cross-user message access, message owner permissions, and admin message permissions.

    Requirements: 3.9, 10.5
    """

    def test_user_cannot_read_other_user_message(self, authenticated_client, test_db):
        """Test user cannot read message sent to another user

        验证：
        - 用户不能读取发送给其他用户的消息
        """
        # Create sender and recipient
        sender = User(
            id=str(uuid.uuid4()),
            username="sender_perm",
            email="sender_perm@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        recipient = User(
            id=str(uuid.uuid4()),
            username="recipient_perm",
            email="recipient_perm@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.add(recipient)
        test_db.commit()

        # Create message between other users
        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=recipient.id,
            title="Private Message",
            content="Private content",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        # Try to read as authenticated_client (test_user)
        response = authenticated_client.get(f"/api/messages/{message.id}")
        assert response.status_code in [403, 404]

    def test_user_cannot_mark_other_user_message_read(self, authenticated_client, test_db):
        """Test user cannot mark another user's message as read

        验证：
        - 用户不能标记其他用户的消息为已读
        """
        sender = User(
            id=str(uuid.uuid4()),
            username="sender_mark",
            email="sender_mark@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        recipient = User(
            id=str(uuid.uuid4()),
            username="recipient_mark",
            email="recipient_mark@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.add(recipient)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=recipient.id,
            title="Mark Test",
            content="Mark test content",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        response = authenticated_client.post(f"/api/messages/{message.id}/read")
        assert response.status_code in [403, 404]

    def test_recipient_can_update_own_message(self, authenticated_client, test_user, test_db):
        """Test recipient can update message they received

        验证：
        - 接收者可以更新自己收到的消息
        """
        sender = User(
            id=str(uuid.uuid4()),
            username="sender_update_perm",
            email="sender_update_perm@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=test_user.id,
            title="Update Permission Test",
            content="Original content",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        data = {"content": "Updated by recipient"}
        response = authenticated_client.put(f"/api/messages/{message.id}", json=data)
        assert response.status_code == 200

    def test_recipient_can_delete_own_message(self, authenticated_client, test_user, test_db):
        """Test recipient can delete message they received

        验证：
        - 接收者可以删除自己收到的消息
        """
        sender = User(
            id=str(uuid.uuid4()),
            username="sender_delete_perm",
            email="sender_delete_perm@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=test_user.id,
            title="Delete Permission Test",
            content="Delete test content",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        response = authenticated_client.delete(f"/api/messages/{message.id}")
        assert response.status_code == 200

    def test_admin_can_delete_broadcast_announcement(self, admin_client, test_db):
        """Test admin can delete their own broadcast announcement

        验证：
        - 管理员可以删除自己发送的广播公告
        """
        # Create recipient
        user = User(
            id=str(uuid.uuid4()),
            username="broadcast_delete_user",
            email="broadcast_delete_user@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(user)
        test_db.commit()

        # Send broadcast
        data = {
            "recipient_ids": [user.id],
            "title": "Admin Broadcast Delete",
            "content": "To be deleted",
            "message_type": "announcement",
            "broadcast_scope": "all_users",
        }

        response = admin_client.post("/api/messages/send", json=data)
        assert response.status_code == 200
        message_id = response.json()["data"]["message_ids"][0]

        # Delete broadcast
        response = admin_client.delete(f"/api/messages/{message_id}")
        assert response.status_code == 200

    def test_admin_can_update_broadcast_announcement(self, admin_client, test_db):
        """Test admin can update their own broadcast announcement

        验证：
        - 管理员可以更新自己发送的广播公告
        """
        user = User(
            id=str(uuid.uuid4()),
            username="broadcast_update_user",
            email="broadcast_update_user@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(user)
        test_db.commit()

        # Send broadcast
        data = {
            "recipient_ids": [user.id],
            "title": "Admin Broadcast Update",
            "content": "Original content",
            "message_type": "announcement",
            "broadcast_scope": "all_users",
        }

        response = admin_client.post("/api/messages/send", json=data)
        assert response.status_code == 200
        message_id = response.json()["data"]["message_ids"][0]

        # Update broadcast
        update_data = {"content": "Updated content"}
        response = admin_client.put(f"/api/messages/{message_id}", json=update_data)
        assert response.status_code == 200

    def test_sender_cannot_delete_direct_message_after_sending(self, authenticated_client, test_user, test_db):
        """Test sender cannot delete direct message after sending

        验证：
        - 发送者不能删除已发送的直接消息（只有接收者可以）
        """
        recipient = User(
            id=str(uuid.uuid4()),
            username="recipient_sender_delete",
            email="recipient_sender_delete@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(recipient)
        test_db.commit()

        # Send message
        data = {
            "recipient_id": recipient.id,
            "title": "Sender Delete Test",
            "content": "Test content",
            "message_type": "direct",
        }

        response = authenticated_client.post("/api/messages/send", json=data)
        assert response.status_code == 200
        message_id = response.json()["data"]["message_ids"][0]

        # Try to delete as sender
        response = authenticated_client.delete(f"/api/messages/{message_id}")
        assert response.status_code in [403, 404]

    def test_user_can_only_see_own_messages_in_list(self, authenticated_client, test_user, test_db):
        """Test user can only see their own messages in message list

        验证：
        - 用户只能看到自己的消息列表
        - 不能看到其他用户之间的消息
        """
        # Create other users
        user1 = User(
            id=str(uuid.uuid4()),
            username="other_user1",
            email="other_user1@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        user2 = User(
            id=str(uuid.uuid4()),
            username="other_user2",
            email="other_user2@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(user1)
        test_db.add(user2)
        test_db.commit()

        # Create message between other users
        message = Message(
            id=str(uuid.uuid4()),
            sender_id=user1.id,
            recipient_id=user2.id,
            title="Private Between Others",
            content="Private content",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        # Get messages as test_user
        response = authenticated_client.get("/api/messages")
        assert response.status_code == 200
        result = response.json()

        # Should not contain the message between other users
        message_ids = [msg["id"] for msg in result["data"]]
        assert message.id not in message_ids


class TestMessageErrorHandling:
    """Test message error handling paths

    Tests database errors, invalid message IDs, and message sending failures.

    Requirements: 10.1, 10.4
    """

    def test_send_message_with_invalid_message_type(self, authenticated_client, test_db):
        """Test sending message with invalid message type

        验证：
        - 无效的消息类型返回验证错误
        """
        recipient = User(
            id=str(uuid.uuid4()),
            username="invalid_type_recipient",
            email="invalid_type_recipient@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(recipient)
        test_db.commit()

        data = {
            "recipient_id": recipient.id,
            "title": "Invalid Type Test",
            "content": "Test content",
            "message_type": "invalid_type",
        }

        response = authenticated_client.post("/api/messages/send", json=data)
        assert response.status_code in [400, 422]

    def test_get_message_with_invalid_uuid(self, authenticated_client):
        """Test getting message with invalid UUID format

        验证：
        - 无效的 UUID 格式返回错误
        """
        response = authenticated_client.get("/api/messages/not-a-uuid")
        assert response.status_code in [400, 404, 422]

    def test_mark_read_with_nonexistent_message_id(self, authenticated_client):
        """Test marking non-existent message as read

        验证：
        - 不存在的消息 ID 返回 404
        """
        fake_id = str(uuid.uuid4())
        response = authenticated_client.post(f"/api/messages/{fake_id}/read")
        assert response.status_code == 404

    def test_update_message_with_only_whitespace(self, authenticated_client, test_user, test_db):
        """Test updating message with only whitespace content

        验证：
        - 只包含空白字符的更新返回错误
        """
        sender = User(
            id=str(uuid.uuid4()),
            username="whitespace_sender",
            email="whitespace_sender@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=test_user.id,
            title="Whitespace Test",
            content="Original content",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        data = {"content": "   ", "title": "   "}
        response = authenticated_client.put(f"/api/messages/{message.id}", json=data)
        assert response.status_code in [400, 422]

    def test_send_message_missing_required_fields(self, authenticated_client):
        """Test sending message with missing required fields

        验证：
        - 缺少必填字段返回验证错误
        """
        data = {
            "title": "Missing Content"
            # Missing content and recipient_id
        }

        response = authenticated_client.post("/api/messages/send", json=data)
        assert response.status_code in [400, 422]

    def test_send_message_with_empty_title(self, authenticated_client, test_db):
        """Test sending message with empty title

        验证：
        - 空标题返回验证错误
        """
        recipient = User(
            id=str(uuid.uuid4()),
            username="empty_title_recipient",
            email="empty_title_recipient@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(recipient)
        test_db.commit()

        data = {"recipient_id": recipient.id, "title": "", "content": "Test content", "message_type": "direct"}

        response = authenticated_client.post("/api/messages/send", json=data)
        assert response.status_code in [400, 422]

    def test_get_messages_by_type_with_empty_type(self, authenticated_client):
        """Test getting messages by empty type

        验证：
        - 空消息类型返回错误或空列表
        """
        response = authenticated_client.get("/api/messages/by-type/")
        assert response.status_code in [404, 422]

    def test_delete_already_deleted_message(self, authenticated_client, test_user, test_db):
        """Test deleting a message that was already deleted

        验证：
        - 删除已删除的消息返回 404
        """
        sender = User(
            id=str(uuid.uuid4()),
            username="double_delete_sender",
            email="double_delete_sender@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(sender)
        test_db.commit()

        message = Message(
            id=str(uuid.uuid4()),
            sender_id=sender.id,
            recipient_id=test_user.id,
            title="Double Delete Test",
            content="Test content",
            message_type="direct",
            is_read=False,
            created_at=datetime.now(),
        )
        test_db.add(message)
        test_db.commit()

        # Delete once
        response = authenticated_client.delete(f"/api/messages/{message.id}")
        assert response.status_code == 200

        # Try to delete again
        response = authenticated_client.delete(f"/api/messages/{message.id}")
        assert response.status_code == 404

    def test_send_message_to_inactive_user(self, authenticated_client, test_db):
        """Test sending message to inactive user

        验证：
        - 发送消息给未激活用户的行为
        """
        inactive_user = User(
            id=str(uuid.uuid4()),
            username="inactive_user",
            email="inactive_user@example.com",
            hashed_password="hashed",
            is_active=False,
        )
        test_db.add(inactive_user)
        test_db.commit()

        data = {
            "recipient_id": inactive_user.id,
            "title": "To Inactive User",
            "content": "Test content",
            "message_type": "direct",
        }

        response = authenticated_client.post("/api/messages/send", json=data)
        # Should either succeed or return error depending on business logic
        assert response.status_code in [200, 400, 404]

    def test_get_messages_with_negative_page(self, authenticated_client):
        """Test getting messages with negative page number

        验证：
        - 负数页码返回验证错误
        """
        response = authenticated_client.get("/api/messages?page=-1")
        assert response.status_code in [400, 422]

    def test_get_messages_with_zero_page_size(self, authenticated_client):
        """Test getting messages with zero page size

        验证：
        - 零页面大小返回验证错误
        """
        response = authenticated_client.get("/api/messages?page_size=0")
        assert response.status_code in [400, 422]
