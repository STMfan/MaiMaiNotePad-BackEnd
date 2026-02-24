"""
审核路由集成测试
测试知识库和人设卡的审核操作和权限

需求: 3.5
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.database import Message, UploadRecord
from tests.conftest import assert_error_response


class TestGetPendingKnowledgeBases:
    """测试 GET /api/review/knowledge/pending 端点"""

    def test_get_pending_knowledge_bases_as_admin_success(self, admin_client: TestClient, test_db: Session, factory):
        """Test admin can retrieve pending knowledge bases

        验证：
        - 返回 200 状态码
        - 返回待审核知识库列表
        - 分页信息正确
        """
        # Create pending knowledge bases
        user = factory.create_user()
        _ = factory.create_knowledge_base(uploader=user, name="Pending KB 1", is_pending=True, is_public=False)
        _ = factory.create_knowledge_base(uploader=user, name="Pending KB 2", is_pending=True, is_public=False)
        # Create non-pending KB (should not be returned)
        _ = factory.create_knowledge_base(uploader=user, name="Public KB", is_pending=False, is_public=True)

        response = admin_client.get("/api/review/knowledge/pending")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["total"] == 2

    def test_get_pending_knowledge_bases_as_moderator_success(
        self, moderator_client: TestClient, test_db: Session, factory
    ):
        """Test moderator can retrieve pending knowledge bases

        验证：
        - 返回 200 状态码
        - 审核员有权限访问
        """
        user = factory.create_user()
        _ = factory.create_knowledge_base(uploader=user, is_pending=True, is_public=False)

        response = moderator_client.get("/api/review/knowledge/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1

    def test_get_pending_knowledge_bases_as_regular_user_forbidden(
        self, authenticated_client: TestClient, test_db: Session
    ):
        """Test regular user cannot access pending knowledge bases

        验证：
        - 返回 403 状态码
        - 错误消息包含权限相关信息
        """
        response = authenticated_client.get("/api/review/knowledge/pending")

        assert_error_response(response, 403, "权限")

    def test_get_pending_knowledge_bases_unauthenticated_fails(self, client: TestClient):
        """Test unauthenticated user cannot access pending knowledge bases

        验证：
        - 返回 401 状态码
        """
        response = client.get("/api/review/knowledge/pending")

        assert response.status_code == 401

    def test_get_pending_knowledge_bases_with_pagination(self, admin_client: TestClient, test_db: Session, factory):
        """Test pagination for pending knowledge bases

        验证：
        - 分页参数正确应用
        - 返回正确数量的结果
        """
        user = factory.create_user()
        # Create 15 pending knowledge bases
        for i in range(15):
            factory.create_knowledge_base(uploader=user, name=f"Pending KB {i}", is_pending=True, is_public=False)

        # Get first page
        response = admin_client.get("/api/review/knowledge/pending?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 10
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 10
        assert data["pagination"]["total"] == 15

        # Get second page
        response = admin_client.get("/api/review/knowledge/pending?page=2&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["pagination"]["page"] == 2

    def test_get_pending_knowledge_bases_with_name_filter(self, admin_client: TestClient, test_db: Session, factory):
        """Test filtering pending knowledge bases by name

        验证：
        - 名称搜索正确过滤结果
        """
        user = factory.create_user()
        _ = factory.create_knowledge_base(uploader=user, name="Python Tutorial", is_pending=True, is_public=False)
        _ = factory.create_knowledge_base(uploader=user, name="JavaScript Guide", is_pending=True, is_public=False)

        response = admin_client.get("/api/review/knowledge/pending?name=Python")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Python Tutorial"

    def test_get_pending_knowledge_bases_with_uploader_filter(
        self, admin_client: TestClient, test_db: Session, factory
    ):
        """Test filtering pending knowledge bases by uploader

        验证：
        - 上传者ID过滤正确工作
        """
        user1 = factory.create_user()
        user2 = factory.create_user()
        _ = factory.create_knowledge_base(uploader=user1, is_pending=True, is_public=False)
        _ = factory.create_knowledge_base(uploader=user2, is_pending=True, is_public=False)

        response = admin_client.get(f"/api/review/knowledge/pending?uploader_id={user1.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["uploader_id"] == user1.id

    def test_get_pending_knowledge_bases_with_sorting(self, admin_client: TestClient, test_db: Session, factory):
        """Test sorting pending knowledge bases

        验证：
        - 排序参数正确应用
        - 支持升序和降序
        """
        user = factory.create_user()
        _ = factory.create_knowledge_base(uploader=user, name="KB A", is_pending=True, is_public=False)
        test_db.flush()
        _ = factory.create_knowledge_base(uploader=user, name="KB B", is_pending=True, is_public=False)

        # Test descending order (default)
        response = admin_client.get("/api/review/knowledge/pending?sort_by=created_at&sort_order=desc")

        assert response.status_code == 200
        data = response.json()
        assert data["data"][0]["name"] == "KB B"

        # Test ascending order
        response = admin_client.get("/api/review/knowledge/pending?sort_by=created_at&sort_order=asc")

        assert response.status_code == 200
        data = response.json()
        assert data["data"][0]["name"] == "KB A"


class TestGetPendingPersonaCards:
    """测试 GET /api/review/persona/pending 端点"""

    def test_get_pending_persona_cards_as_admin_success(self, admin_client: TestClient, test_db: Session, factory):
        """Test admin can retrieve pending persona cards

        验证：
        - 返回 200 状态码
        - 返回待审核人设卡列表
        """
        user = factory.create_user()
        _ = factory.create_persona_card(uploader=user, name="Pending PC 1", is_pending=True, is_public=False)
        _ = factory.create_persona_card(uploader=user, name="Pending PC 2", is_pending=True, is_public=False)

        response = admin_client.get("/api/review/persona/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

    def test_get_pending_persona_cards_as_moderator_success(
        self, moderator_client: TestClient, test_db: Session, factory
    ):
        """Test moderator can retrieve pending persona cards

        验证：
        - 返回 200 状态码
        - 审核员有权限访问
        """
        user = factory.create_user()
        _ = factory.create_persona_card(uploader=user, is_pending=True, is_public=False)

        response = moderator_client.get("/api/review/persona/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1

    def test_get_pending_persona_cards_as_regular_user_forbidden(
        self, authenticated_client: TestClient, test_db: Session
    ):
        """Test regular user cannot access pending persona cards

        验证：
        - 返回 403 状态码
        """
        response = authenticated_client.get("/api/review/persona/pending")

        assert_error_response(response, 403, "权限")

    def test_get_pending_persona_cards_with_pagination(self, admin_client: TestClient, test_db: Session, factory):
        """Test pagination for pending persona cards

        验证：
        - 分页参数正确应用
        """
        user = factory.create_user()
        for i in range(15):
            factory.create_persona_card(uploader=user, name=f"Pending PC {i}", is_pending=True, is_public=False)

        response = admin_client.get("/api/review/persona/pending?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 10
        assert data["pagination"]["total"] == 15

    def test_get_pending_persona_cards_with_name_filter(self, admin_client: TestClient, test_db: Session, factory):
        """Test filtering pending persona cards by name

        验证：
        - 名称搜索正确过滤结果
        """
        user = factory.create_user()
        _ = factory.create_persona_card(uploader=user, name="Alice Character", is_pending=True, is_public=False)
        _ = factory.create_persona_card(uploader=user, name="Bob Character", is_pending=True, is_public=False)

        response = admin_client.get("/api/review/persona/pending?name=Alice")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Alice Character"


class TestApproveKnowledgeBase:
    """测试 POST /api/review/knowledge/{kb_id}/approve 端点"""

    @patch("app.utils.websocket.message_ws_manager.broadcast_user_update")
    def test_approve_knowledge_base_as_admin_success(
        self, mock_broadcast, admin_client: TestClient, test_db: Session, factory
    ):
        """Test admin can approve knowledge base

        验证：
        - 返回 200 状态码
        - 知识库状态更新为公开
        - is_pending 设置为 False
        - 发送通知消息
        """
        mock_broadcast.return_value = AsyncMock()

        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user, is_pending=True, is_public=False)

        # Create upload record
        upload_record = UploadRecord(
            id=str(uuid.uuid4()),
            uploader_id=user.id,
            target_id=kb.id,
            target_type="knowledge",
            name=kb.name,
            status="pending",
            created_at=datetime.now(),
        )
        test_db.add(upload_record)
        test_db.commit()

        response = admin_client.post(f"/api/review/knowledge/{kb.id}/approve")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify knowledge base status
        test_db.refresh(kb)
        assert kb.is_public is True
        assert kb.is_pending is False
        assert kb.rejection_reason is None

        # Verify upload record status
        test_db.refresh(upload_record)
        assert upload_record.status == "approved"

        # Verify notification message was created
        message = test_db.query(Message).filter(Message.recipient_id == user.id).first()
        assert message is not None
        assert "审核通过" in message.title

    @patch("app.utils.websocket.message_ws_manager.broadcast_user_update")
    def test_approve_knowledge_base_as_moderator_success(
        self, mock_broadcast, moderator_client: TestClient, test_db: Session, factory
    ):
        """Test moderator can approve knowledge base

        验证：
        - 审核员有权限审核
        """
        mock_broadcast.return_value = AsyncMock()

        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user, is_pending=True, is_public=False)

        response = moderator_client.post(f"/api/review/knowledge/{kb.id}/approve")

        assert response.status_code == 200
        test_db.refresh(kb)
        assert kb.is_public is True

    def test_approve_knowledge_base_as_regular_user_forbidden(
        self, authenticated_client: TestClient, test_db: Session, factory
    ):
        """Test regular user cannot approve knowledge base

        验证：
        - 返回 403 状态码
        """
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user, is_pending=True, is_public=False)

        response = authenticated_client.post(f"/api/review/knowledge/{kb.id}/approve")

        assert_error_response(response, 403, "权限")

    def test_approve_nonexistent_knowledge_base_fails(self, admin_client: TestClient, test_db: Session):
        """Test approving non-existent knowledge base fails

        验证：
        - 返回 404 状态码
        """
        fake_id = str(uuid.uuid4())
        response = admin_client.post(f"/api/review/knowledge/{fake_id}/approve")

        assert_error_response(response, 404, "不存在")


class TestRejectKnowledgeBase:
    """测试 POST /api/review/knowledge/{kb_id}/reject 端点"""

    @patch("app.utils.websocket.message_ws_manager.broadcast_user_update")
    def test_reject_knowledge_base_as_admin_success(
        self, mock_broadcast, admin_client: TestClient, test_db: Session, factory
    ):
        """Test admin can reject knowledge base

        验证：
        - 返回 200 状态码
        - 知识库状态更新
        - 拒绝原因被保存
        - 发送通知消息
        """
        mock_broadcast.return_value = AsyncMock()

        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user, is_pending=True, is_public=False)

        # Create upload record
        upload_record = UploadRecord(
            id=str(uuid.uuid4()),
            uploader_id=user.id,
            target_id=kb.id,
            target_type="knowledge",
            name=kb.name,
            status="pending",
            created_at=datetime.now(),
        )
        test_db.add(upload_record)
        test_db.commit()

        rejection_reason = "内容不符合规范"
        response = admin_client.post(f"/api/review/knowledge/{kb.id}/reject", json={"reason": rejection_reason})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify knowledge base status
        test_db.refresh(kb)
        assert kb.is_public is False
        assert kb.is_pending is False
        assert kb.rejection_reason == rejection_reason

        # Verify upload record status
        test_db.refresh(upload_record)
        assert upload_record.status == "rejected"

        # Verify notification message was created
        message = test_db.query(Message).filter(Message.recipient_id == user.id).first()
        assert message is not None
        assert "审核未通过" in message.title
        assert rejection_reason in message.content

    @patch("app.utils.websocket.message_ws_manager.broadcast_user_update")
    def test_reject_knowledge_base_as_moderator_success(
        self, mock_broadcast, moderator_client: TestClient, test_db: Session, factory
    ):
        """Test moderator can reject knowledge base

        验证：
        - 审核员有权限拒绝
        """
        mock_broadcast.return_value = AsyncMock()

        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user, is_pending=True, is_public=False)

        response = moderator_client.post(f"/api/review/knowledge/{kb.id}/reject", json={"reason": "测试拒绝"})

        assert response.status_code == 200
        test_db.refresh(kb)
        assert kb.is_pending is False
        assert kb.rejection_reason == "测试拒绝"

    def test_reject_knowledge_base_as_regular_user_forbidden(
        self, authenticated_client: TestClient, test_db: Session, factory
    ):
        """Test regular user cannot reject knowledge base

        验证：
        - 返回 403 状态码
        """
        user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=user, is_pending=True, is_public=False)

        response = authenticated_client.post(f"/api/review/knowledge/{kb.id}/reject", json={"reason": "测试"})

        assert_error_response(response, 403, "权限")

    def test_reject_nonexistent_knowledge_base_fails(self, admin_client: TestClient, test_db: Session):
        """Test rejecting non-existent knowledge base fails

        验证：
        - 返回 404 状态码
        """
        fake_id = str(uuid.uuid4())
        response = admin_client.post(f"/api/review/knowledge/{fake_id}/reject", json={"reason": "测试"})

        assert_error_response(response, 404, "不存在")


class TestApprovePersonaCard:
    """测试 POST /api/review/persona/{pc_id}/approve 端点"""

    @patch("app.utils.websocket.message_ws_manager.broadcast_user_update")
    def test_approve_persona_card_as_admin_success(
        self, mock_broadcast, admin_client: TestClient, test_db: Session, factory
    ):
        """Test admin can approve persona card

        验证：
        - 返回 200 状态码
        - 人设卡状态更新为公开
        - 发送通知消息
        """
        mock_broadcast.return_value = AsyncMock()

        user = factory.create_user()
        pc = factory.create_persona_card(uploader=user, is_pending=True, is_public=False)

        # Create upload record
        upload_record = UploadRecord(
            id=str(uuid.uuid4()),
            uploader_id=user.id,
            target_id=pc.id,
            target_type="persona",
            name=pc.name,
            status="pending",
            created_at=datetime.now(),
        )
        test_db.add(upload_record)
        test_db.commit()

        response = admin_client.post(f"/api/review/persona/{pc.id}/approve")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify persona card status
        test_db.refresh(pc)
        assert pc.is_public is True
        assert pc.is_pending is False
        assert pc.rejection_reason is None

        # Verify upload record status
        test_db.refresh(upload_record)
        assert upload_record.status == "approved"

        # Verify notification message was created
        message = test_db.query(Message).filter(Message.recipient_id == user.id).first()
        assert message is not None
        assert "审核通过" in message.title

    @patch("app.utils.websocket.message_ws_manager.broadcast_user_update")
    def test_approve_persona_card_as_moderator_success(
        self, mock_broadcast, moderator_client: TestClient, test_db: Session, factory
    ):
        """Test moderator can approve persona card

        验证：
        - 审核员有权限审核
        """
        mock_broadcast.return_value = AsyncMock()

        user = factory.create_user()
        pc = factory.create_persona_card(uploader=user, is_pending=True, is_public=False)

        response = moderator_client.post(f"/api/review/persona/{pc.id}/approve")

        assert response.status_code == 200
        test_db.refresh(pc)
        assert pc.is_public is True

    def test_approve_persona_card_as_regular_user_forbidden(
        self, authenticated_client: TestClient, test_db: Session, factory
    ):
        """Test regular user cannot approve persona card

        验证：
        - 返回 403 状态码
        """
        user = factory.create_user()
        pc = factory.create_persona_card(uploader=user, is_pending=True, is_public=False)

        response = authenticated_client.post(f"/api/review/persona/{pc.id}/approve")

        assert_error_response(response, 403, "权限")

    def test_approve_nonexistent_persona_card_fails(self, admin_client: TestClient, test_db: Session):
        """Test approving non-existent persona card fails

        验证：
        - 返回 404 状态码
        """
        fake_id = str(uuid.uuid4())
        response = admin_client.post(f"/api/review/persona/{fake_id}/approve")

        assert_error_response(response, 404, "不存在")


class TestRejectPersonaCard:
    """测试 POST /api/review/persona/{pc_id}/reject 端点"""

    @patch("app.utils.websocket.message_ws_manager.broadcast_user_update")
    def test_reject_persona_card_as_admin_success(
        self, mock_broadcast, admin_client: TestClient, test_db: Session, factory
    ):
        """Test admin can reject persona card

        验证：
        - 返回 200 状态码
        - 人设卡状态更新
        - 拒绝原因被保存
        - 发送通知消息
        """
        mock_broadcast.return_value = AsyncMock()

        user = factory.create_user()
        pc = factory.create_persona_card(uploader=user, is_pending=True, is_public=False)

        # Create upload record
        upload_record = UploadRecord(
            id=str(uuid.uuid4()),
            uploader_id=user.id,
            target_id=pc.id,
            target_type="persona",
            name=pc.name,
            status="pending",
            created_at=datetime.now(),
        )
        test_db.add(upload_record)
        test_db.commit()

        rejection_reason = "人设描述不完整"
        response = admin_client.post(f"/api/review/persona/{pc.id}/reject", json={"reason": rejection_reason})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify persona card status
        test_db.refresh(pc)
        assert pc.is_public is False
        assert pc.is_pending is False
        assert pc.rejection_reason == rejection_reason

        # Verify upload record status
        test_db.refresh(upload_record)
        assert upload_record.status == "rejected"

        # Verify notification message was created
        message = test_db.query(Message).filter(Message.recipient_id == user.id).first()
        assert message is not None
        assert "审核未通过" in message.title
        assert rejection_reason in message.content

    @patch("app.utils.websocket.message_ws_manager.broadcast_user_update")
    def test_reject_persona_card_as_moderator_success(
        self, mock_broadcast, moderator_client: TestClient, test_db: Session, factory
    ):
        """Test moderator can reject persona card

        验证：
        - 审核员有权限拒绝
        """
        mock_broadcast.return_value = AsyncMock()

        user = factory.create_user()
        pc = factory.create_persona_card(uploader=user, is_pending=True, is_public=False)

        response = moderator_client.post(f"/api/review/persona/{pc.id}/reject", json={"reason": "测试拒绝"})

        assert response.status_code == 200
        test_db.refresh(pc)
        assert pc.is_pending is False
        assert pc.rejection_reason == "测试拒绝"

    def test_reject_persona_card_as_regular_user_forbidden(
        self, authenticated_client: TestClient, test_db: Session, factory
    ):
        """Test regular user cannot reject persona card

        验证：
        - 返回 403 状态码
        """
        user = factory.create_user()
        pc = factory.create_persona_card(uploader=user, is_pending=True, is_public=False)

        response = authenticated_client.post(f"/api/review/persona/{pc.id}/reject", json={"reason": "测试"})

        assert_error_response(response, 403, "权限")

    def test_reject_nonexistent_persona_card_fails(self, admin_client: TestClient, test_db: Session):
        """Test rejecting non-existent persona card fails

        验证：
        - 返回 404 状态码
        """
        fake_id = str(uuid.uuid4())
        response = admin_client.post(f"/api/review/persona/{fake_id}/reject", json={"reason": "测试"})

        assert_error_response(response, 404, "不存在")
