"""
Integration tests for review routes

Tests cover:
- GET /api/review/review/knowledge/pending (list pending knowledge bases)
- GET /api/review/review/persona/pending (list pending persona cards)
- POST /api/review/review/knowledge/{id}/approve (approve knowledge base)
- POST /api/review/review/knowledge/{id}/reject (reject knowledge base)
- POST /api/review/review/persona/{id}/approve (approve persona card)
- POST /api/review/review/persona/{id}/reject (reject persona card)

Note: The routes have a double /review/ prefix due to how the router is registered.
This is a known issue in the existing codebase.

Requirements: 1.5, 7.3, 7.4
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, AsyncMock

from app.models.database import KnowledgeBase, PersonaCard, UploadRecord, Message


class TestGetPendingKnowledgeBases:
    """Test GET /api/review/review/knowledge/pending endpoint"""

    def test_get_pending_knowledge_bases_as_moderator(self, moderator_client, test_db, test_user):
        """Test moderator can list pending knowledge bases"""
        # Create pending knowledge bases
        kb1 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Pending KB 1",
            description="Test description 1",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path1",
            created_at=datetime.now()
        )
        kb2 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Pending KB 2",
            description="Test description 2",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path2",
            created_at=datetime.now()
        )
        test_db.add_all([kb1, kb2])
        test_db.commit()

        # Get pending knowledge bases
        response = moderator_client.get("/api/review/review/knowledge/pending")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "获取待审核知识库成功"
        assert len(data["data"]) == 2
        assert data["pagination"]["total"] == 2
        assert data["pagination"]["page"] == 1

    def test_get_pending_knowledge_bases_as_admin(self, admin_client, test_db, test_user):
        """Test admin can list pending knowledge bases"""
        # Create pending knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Pending KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()

        # Get pending knowledge bases
        response = admin_client.get("/api/review/review/knowledge/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1

    def test_get_pending_knowledge_bases_with_pagination(self, moderator_client, test_db, test_user):
        """Test pagination for pending knowledge bases"""
        # Create multiple pending knowledge bases
        for i in range(15):
            kb = KnowledgeBase(
                id=str(uuid.uuid4()),
                name=f"Pending KB {i}",
                description=f"Test description {i}",
                uploader_id=test_user.id,
                is_pending=True,
                is_public=False,
                base_path=f"/test/path{i}",
                created_at=datetime.now()
            )
            test_db.add(kb)
        test_db.commit()

        # Get first page
        response = moderator_client.get("/api/review/review/knowledge/pending?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 10
        assert data["pagination"]["total"] == 15
        assert data["pagination"]["page"] == 1

        # Get second page
        response = moderator_client.get("/api/review/review/knowledge/pending?page=2&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["pagination"]["page"] == 2

    def test_get_pending_knowledge_bases_with_search(self, moderator_client, test_db, test_user):
        """Test search filter for pending knowledge bases"""
        # Create knowledge bases with different names
        kb1 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Python Tutorial",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path1",
            created_at=datetime.now()
        )
        kb2 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="JavaScript Guide",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path2",
            created_at=datetime.now()
        )
        test_db.add_all([kb1, kb2])
        test_db.commit()

        # Search for Python
        response = moderator_client.get("/api/review/review/knowledge/pending?name=Python")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Python Tutorial"

    def test_get_pending_knowledge_bases_with_uploader_filter(self, moderator_client, test_db, test_user, admin_user):
        """Test uploader filter for pending knowledge bases"""
        # Create knowledge bases from different uploaders
        kb1 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB from test user",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path1",
            created_at=datetime.now()
        )
        kb2 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB from admin",
            description="Test description",
            uploader_id=admin_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path2",
            created_at=datetime.now()
        )
        test_db.add_all([kb1, kb2])
        test_db.commit()

        # Filter by test_user
        response = moderator_client.get(f"/api/review/review/knowledge/pending?uploader_id={test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["uploader_id"] == test_user.id

    def test_get_pending_knowledge_bases_with_sorting(self, moderator_client, test_db, test_user):
        """Test sorting for pending knowledge bases"""
        # Create knowledge bases with different star counts
        kb1 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB 1",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path1",
            star_count=5,
            created_at=datetime.now()
        )
        kb2 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB 2",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path2",
            star_count=10,
            created_at=datetime.now()
        )
        test_db.add_all([kb1, kb2])
        test_db.commit()

        # Sort by star_count descending
        response = moderator_client.get("/api/review/review/knowledge/pending?sort_by=star_count&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        assert data["data"][0]["star_count"] == 10
        assert data["data"][1]["star_count"] == 5

        # Sort by star_count ascending
        response = moderator_client.get("/api/review/review/knowledge/pending?sort_by=star_count&sort_order=asc")
        assert response.status_code == 200
        data = response.json()
        assert data["data"][0]["star_count"] == 5
        assert data["data"][1]["star_count"] == 10

    def test_get_pending_knowledge_bases_permission_denied(self, authenticated_client, test_db):
        """Test regular user cannot list pending knowledge bases"""
        response = authenticated_client.get("/api/review/review/knowledge/pending")
        assert response.status_code == 403
        data = response.json()
        assert "没有审核权限" in data["detail"]


class TestGetPendingPersonaCards:
    """Test GET /api/review/review/persona/pending endpoint"""

    def test_get_pending_persona_cards_as_moderator(self, moderator_client, test_db, test_user):
        """Test moderator can list pending persona cards"""
        # Create pending persona cards
        pc1 = PersonaCard(
            id=str(uuid.uuid4()),
            name="Pending PC 1",
            description="Test description 1",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path1",
            created_at=datetime.now()
        )
        pc2 = PersonaCard(
            id=str(uuid.uuid4()),
            name="Pending PC 2",
            description="Test description 2",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path2",
            created_at=datetime.now()
        )
        test_db.add_all([pc1, pc2])
        test_db.commit()

        # Get pending persona cards
        response = moderator_client.get("/api/review/review/persona/pending")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "获取待审核人设卡成功"
        assert len(data["data"]) == 2
        assert data["pagination"]["total"] == 2

    def test_get_pending_persona_cards_as_admin(self, admin_client, test_db, test_user):
        """Test admin can list pending persona cards"""
        # Create pending persona card
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Pending PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(pc)
        test_db.commit()

        # Get pending persona cards
        response = admin_client.get("/api/review/review/persona/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1

    def test_get_pending_persona_cards_with_pagination(self, moderator_client, test_db, test_user):
        """Test pagination for pending persona cards"""
        # Create multiple pending persona cards
        for i in range(15):
            pc = PersonaCard(
                id=str(uuid.uuid4()),
                name=f"Pending PC {i}",
                description=f"Test description {i}",
                uploader_id=test_user.id,
                is_pending=True,
                is_public=False,
                base_path=f"/test/path{i}",
                created_at=datetime.now()
            )
            test_db.add(pc)
        test_db.commit()

        # Get first page
        response = moderator_client.get("/api/review/review/persona/pending?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 10
        assert data["pagination"]["total"] == 15

        # Get second page
        response = moderator_client.get("/api/review/review/persona/pending?page=2&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5

    def test_get_pending_persona_cards_with_search(self, moderator_client, test_db, test_user):
        """Test search filter for pending persona cards"""
        # Create persona cards with different names
        pc1 = PersonaCard(
            id=str(uuid.uuid4()),
            name="Friendly Assistant",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path1",
            created_at=datetime.now()
        )
        pc2 = PersonaCard(
            id=str(uuid.uuid4()),
            name="Professional Expert",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path2",
            created_at=datetime.now()
        )
        test_db.add_all([pc1, pc2])
        test_db.commit()

        # Search for Friendly
        response = moderator_client.get("/api/review/review/persona/pending?name=Friendly")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Friendly Assistant"

    def test_get_pending_persona_cards_permission_denied(self, authenticated_client, test_db):
        """Test regular user cannot list pending persona cards"""
        response = authenticated_client.get("/api/review/review/persona/pending")
        assert response.status_code == 403
        data = response.json()
        assert "没有审核权限" in data["detail"]



class TestApproveKnowledgeBase:
    """Test POST /api/review/review/knowledge/{id}/approve endpoint"""

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_approve_knowledge_base_as_moderator(self, mock_broadcast, moderator_client, test_db, test_user):
        """Test moderator can approve knowledge base"""
        # Create pending knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()

        # Create upload record
        upload_record = UploadRecord(
            id=str(uuid.uuid4()),
            uploader_id=test_user.id,
            target_id=kb.id,
            target_type="knowledge",
            name=kb.name,
            status="pending"
        )
        test_db.add(upload_record)
        test_db.commit()

        # Approve knowledge base
        response = moderator_client.post(f"/api/review/review/knowledge/{kb.id}/approve")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "审核通过，已发送通知"

        # Verify knowledge base status updated
        test_db.refresh(kb)
        assert kb.is_public is True
        assert kb.is_pending is False
        assert kb.rejection_reason is None

        # Verify upload record status updated
        test_db.refresh(upload_record)
        assert upload_record.status == "approved"

        # Verify notification message created
        message = test_db.query(Message).filter(Message.recipient_id == test_user.id).first()
        assert message is not None
        assert "审核通过" in message.title
        assert kb.name in message.content

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_approve_knowledge_base_as_admin(self, mock_broadcast, admin_client, test_db, test_user):
        """Test admin can approve knowledge base"""
        # Create pending knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()

        # Approve knowledge base
        response = admin_client.post(f"/api/review/review/knowledge/{kb.id}/approve")

        assert response.status_code == 200
        test_db.refresh(kb)
        assert kb.is_public is True
        assert kb.is_pending is False

    def test_approve_knowledge_base_not_found(self, moderator_client, test_db):
        """Test approving non-existent knowledge base returns 404"""
        fake_id = str(uuid.uuid4())
        response = moderator_client.post(f"/api/review/review/knowledge/{fake_id}/approve")

        assert response.status_code == 404
        data = response.json()
        assert "知识库不存在" in data["detail"]

    def test_approve_knowledge_base_permission_denied(self, authenticated_client, test_db, test_user):
        """Test regular user cannot approve knowledge base"""
        # Create pending knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()

        # Try to approve
        response = authenticated_client.post(f"/api/review/review/knowledge/{kb.id}/approve")

        assert response.status_code == 403
        data = response.json()
        assert "没有审核权限" in data["detail"]


class TestRejectKnowledgeBase:
    """Test POST /api/review/review/knowledge/{id}/reject endpoint"""

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_reject_knowledge_base_as_moderator(self, mock_broadcast, moderator_client, test_db, test_user):
        """Test moderator can reject knowledge base"""
        # Create pending knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()

        # Create upload record
        upload_record = UploadRecord(
            id=str(uuid.uuid4()),
            uploader_id=test_user.id,
            target_id=kb.id,
            target_type="knowledge",
            name=kb.name,
            status="pending"
        )
        test_db.add(upload_record)
        test_db.commit()

        # Reject knowledge base
        rejection_reason = "Content does not meet quality standards"
        response = moderator_client.post(
            f"/api/review/review/knowledge/{kb.id}/reject",
            json={"reason": rejection_reason}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "审核拒绝，已发送通知"

        # Verify knowledge base status updated
        test_db.refresh(kb)
        assert kb.is_public is False
        assert kb.is_pending is False
        assert kb.rejection_reason == rejection_reason

        # Verify upload record status updated
        test_db.refresh(upload_record)
        assert upload_record.status == "rejected"

        # Verify notification message created
        message = test_db.query(Message).filter(Message.recipient_id == test_user.id).first()
        assert message is not None
        assert "审核未通过" in message.title
        assert rejection_reason in message.content

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_reject_knowledge_base_as_admin(self, mock_broadcast, admin_client, test_db, test_user):
        """Test admin can reject knowledge base"""
        # Create pending knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()

        # Reject knowledge base
        rejection_reason = "Inappropriate content"
        response = admin_client.post(
            f"/api/review/review/knowledge/{kb.id}/reject",
            json={"reason": rejection_reason}
        )

        assert response.status_code == 200
        test_db.refresh(kb)
        assert kb.is_public is False
        assert kb.is_pending is False
        assert kb.rejection_reason == rejection_reason

    def test_reject_knowledge_base_not_found(self, moderator_client, test_db):
        """Test rejecting non-existent knowledge base returns 404"""
        fake_id = str(uuid.uuid4())
        response = moderator_client.post(
            f"/api/review/review/knowledge/{fake_id}/reject",
            json={"reason": "Test reason"}
        )

        assert response.status_code == 404
        data = response.json()
        assert "知识库不存在" in data["detail"]

    def test_reject_knowledge_base_permission_denied(self, authenticated_client, test_db, test_user):
        """Test regular user cannot reject knowledge base"""
        # Create pending knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()

        # Try to reject
        response = authenticated_client.post(
            f"/api/review/review/knowledge/{kb.id}/reject",
            json={"reason": "Test reason"}
        )

        assert response.status_code == 403
        data = response.json()
        assert "没有审核权限" in data["detail"]


class TestApprovePersonaCard:
    """Test POST /api/review/review/persona/{id}/approve endpoint"""

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_approve_persona_card_as_moderator(self, mock_broadcast, moderator_client, test_db, test_user):
        """Test moderator can approve persona card"""
        # Create pending persona card
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(pc)
        test_db.commit()

        # Create upload record
        upload_record = UploadRecord(
            id=str(uuid.uuid4()),
            uploader_id=test_user.id,
            target_id=pc.id,
            target_type="persona",
            name=pc.name,
            status="pending"
        )
        test_db.add(upload_record)
        test_db.commit()

        # Approve persona card
        response = moderator_client.post(f"/api/review/review/persona/{pc.id}/approve")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "审核通过，已发送通知"

        # Verify persona card status updated
        test_db.refresh(pc)
        assert pc.is_public is True
        assert pc.is_pending is False
        assert pc.rejection_reason is None

        # Verify upload record status updated
        test_db.refresh(upload_record)
        assert upload_record.status == "approved"

        # Verify notification message created
        message = test_db.query(Message).filter(Message.recipient_id == test_user.id).first()
        assert message is not None
        assert "审核通过" in message.title
        assert pc.name in message.content

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_approve_persona_card_as_admin(self, mock_broadcast, admin_client, test_db, test_user):
        """Test admin can approve persona card"""
        # Create pending persona card
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(pc)
        test_db.commit()

        # Approve persona card
        response = admin_client.post(f"/api/review/review/persona/{pc.id}/approve")

        assert response.status_code == 200
        test_db.refresh(pc)
        assert pc.is_public is True
        assert pc.is_pending is False

    def test_approve_persona_card_not_found(self, moderator_client, test_db):
        """Test approving non-existent persona card returns 404"""
        fake_id = str(uuid.uuid4())
        response = moderator_client.post(f"/api/review/review/persona/{fake_id}/approve")

        assert response.status_code == 404
        data = response.json()
        assert "人设卡不存在" in data["detail"]

    def test_approve_persona_card_permission_denied(self, authenticated_client, test_db, test_user):
        """Test regular user cannot approve persona card"""
        # Create pending persona card
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(pc)
        test_db.commit()

        # Try to approve
        response = authenticated_client.post(f"/api/review/review/persona/{pc.id}/approve")

        assert response.status_code == 403
        data = response.json()
        assert "没有审核权限" in data["detail"]


class TestRejectPersonaCard:
    """Test POST /api/review/review/persona/{id}/reject endpoint"""

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_reject_persona_card_as_moderator(self, mock_broadcast, moderator_client, test_db, test_user):
        """Test moderator can reject persona card"""
        # Create pending persona card
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(pc)
        test_db.commit()

        # Create upload record
        upload_record = UploadRecord(
            id=str(uuid.uuid4()),
            uploader_id=test_user.id,
            target_id=pc.id,
            target_type="persona",
            name=pc.name,
            status="pending"
        )
        test_db.add(upload_record)
        test_db.commit()

        # Reject persona card
        rejection_reason = "Character description is inappropriate"
        response = moderator_client.post(
            f"/api/review/review/persona/{pc.id}/reject",
            json={"reason": rejection_reason}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "审核拒绝，已发送通知"

        # Verify persona card status updated
        test_db.refresh(pc)
        assert pc.is_public is False
        assert pc.is_pending is False
        assert pc.rejection_reason == rejection_reason

        # Verify upload record status updated
        test_db.refresh(upload_record)
        assert upload_record.status == "rejected"

        # Verify notification message created
        message = test_db.query(Message).filter(Message.recipient_id == test_user.id).first()
        assert message is not None
        assert "审核未通过" in message.title
        assert rejection_reason in message.content

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_reject_persona_card_as_admin(self, mock_broadcast, admin_client, test_db, test_user):
        """Test admin can reject persona card"""
        # Create pending persona card
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(pc)
        test_db.commit()

        # Reject persona card
        rejection_reason = "Violates community guidelines"
        response = admin_client.post(
            f"/api/review/review/persona/{pc.id}/reject",
            json={"reason": rejection_reason}
        )

        assert response.status_code == 200
        test_db.refresh(pc)
        assert pc.is_public is False
        assert pc.is_pending is False
        assert pc.rejection_reason == rejection_reason

    def test_reject_persona_card_not_found(self, moderator_client, test_db):
        """Test rejecting non-existent persona card returns 404"""
        fake_id = str(uuid.uuid4())
        response = moderator_client.post(
            f"/api/review/review/persona/{fake_id}/reject",
            json={"reason": "Test reason"}
        )

        assert response.status_code == 404
        data = response.json()
        assert "人设卡不存在" in data["detail"]

    def test_reject_persona_card_permission_denied(self, authenticated_client, test_db, test_user):
        """Test regular user cannot reject persona card"""
        # Create pending persona card
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(pc)
        test_db.commit()

        # Try to reject
        response = authenticated_client.post(
            f"/api/review/review/persona/{pc.id}/reject",
            json={"reason": "Test reason"}
        )

        assert response.status_code == 403
        data = response.json()
        assert "没有审核权限" in data["detail"]



class TestReviewPermissions:
    """Test review endpoint permission requirements"""

    def test_super_admin_can_access_review_endpoints(self, super_admin_client, test_db, test_user):
        """Test super admin has access to all review endpoints"""
        # Create pending knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()

        # Test list pending knowledge bases
        response = super_admin_client.get("/api/review/review/knowledge/pending")
        assert response.status_code == 200

        # Test approve knowledge base
        response = super_admin_client.post(f"/api/review/review/knowledge/{kb.id}/approve")
        assert response.status_code == 200

    def test_moderator_can_access_all_review_endpoints(self, moderator_client, test_db, test_user):
        """Test moderator has access to all review endpoints"""
        # Create pending items
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add_all([kb, pc])
        test_db.commit()

        # Test all endpoints
        assert moderator_client.get("/api/review/review/knowledge/pending").status_code == 200
        assert moderator_client.get("/api/review/review/persona/pending").status_code == 200
        assert moderator_client.post(f"/api/review/review/knowledge/{kb.id}/approve").status_code == 200
        
        # Create another for reject test
        kb2 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB 2",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path2",
            created_at=datetime.now()
        )
        test_db.add(kb2)
        test_db.commit()
        
        assert moderator_client.post(
            f"/api/review/review/knowledge/{kb2.id}/reject",
            json={"reason": "Test"}
        ).status_code == 200
        assert moderator_client.post(f"/api/review/review/persona/{pc.id}/approve").status_code == 200

    def test_admin_can_access_all_review_endpoints(self, admin_client, test_db, test_user):
        """Test admin has access to all review endpoints"""
        # Create pending items
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add_all([kb, pc])
        test_db.commit()

        # Test all endpoints
        assert admin_client.get("/api/review/review/knowledge/pending").status_code == 200
        assert admin_client.get("/api/review/review/persona/pending").status_code == 200
        assert admin_client.post(f"/api/review/review/knowledge/{kb.id}/approve").status_code == 200
        assert admin_client.post(f"/api/review/review/persona/{pc.id}/approve").status_code == 200

    def test_regular_user_cannot_access_review_endpoints(self, authenticated_client, test_db, test_user):
        """Test regular user is denied access to all review endpoints"""
        # Create pending items
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add_all([kb, pc])
        test_db.commit()

        # Test all endpoints return 403
        assert authenticated_client.get("/api/review/review/knowledge/pending").status_code == 403
        assert authenticated_client.get("/api/review/review/persona/pending").status_code == 403
        assert authenticated_client.post(f"/api/review/review/knowledge/{kb.id}/approve").status_code == 403
        assert authenticated_client.post(
            f"/api/review/review/knowledge/{kb.id}/reject",
            json={"reason": "Test"}
        ).status_code == 403
        assert authenticated_client.post(f"/api/review/review/persona/{pc.id}/approve").status_code == 403
        assert authenticated_client.post(
            f"/api/review/review/persona/{pc.id}/reject",
            json={"reason": "Test"}
        ).status_code == 403


class TestReviewHistoryTracking:
    """Test review history tracking via UploadRecord"""

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_upload_record_updated_on_approval(self, mock_broadcast, moderator_client, test_db, test_user):
        """Test upload record status is updated when content is approved"""
        # Create pending knowledge base with upload record
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()

        upload_record = UploadRecord(
            id=str(uuid.uuid4()),
            uploader_id=test_user.id,
            target_id=kb.id,
            target_type="knowledge",
            name=kb.name,
            status="pending",
            created_at=datetime.now()
        )
        test_db.add(upload_record)
        test_db.commit()

        # Approve knowledge base
        response = moderator_client.post(f"/api/review/review/knowledge/{kb.id}/approve")
        assert response.status_code == 200

        # Verify upload record status updated
        test_db.refresh(upload_record)
        assert upload_record.status == "approved"

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_upload_record_updated_on_rejection(self, mock_broadcast, moderator_client, test_db, test_user):
        """Test upload record status is updated when content is rejected"""
        # Create pending persona card with upload record
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(pc)
        test_db.commit()

        upload_record = UploadRecord(
            id=str(uuid.uuid4()),
            uploader_id=test_user.id,
            target_id=pc.id,
            target_type="persona",
            name=pc.name,
            status="pending",
            created_at=datetime.now()
        )
        test_db.add(upload_record)
        test_db.commit()

        # Reject persona card
        response = moderator_client.post(
            f"/api/review/review/persona/{pc.id}/reject",
            json={"reason": "Test rejection"}
        )
        assert response.status_code == 200

        # Verify upload record status updated
        test_db.refresh(upload_record)
        assert upload_record.status == "rejected"

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_review_history_persists_across_multiple_reviews(self, mock_broadcast, moderator_client, test_db, test_user):
        """Test that review history is maintained for multiple review actions"""
        # Create multiple pending items
        kb1 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB 1",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path1",
            created_at=datetime.now()
        )
        kb2 = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="KB 2",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path2",
            created_at=datetime.now()
        )
        test_db.add_all([kb1, kb2])
        test_db.commit()

        # Create upload records
        record1 = UploadRecord(
            id=str(uuid.uuid4()),
            uploader_id=test_user.id,
            target_id=kb1.id,
            target_type="knowledge",
            name=kb1.name,
            status="pending"
        )
        record2 = UploadRecord(
            id=str(uuid.uuid4()),
            uploader_id=test_user.id,
            target_id=kb2.id,
            target_type="knowledge",
            name=kb2.name,
            status="pending"
        )
        test_db.add_all([record1, record2])
        test_db.commit()

        # Approve first, reject second
        moderator_client.post(f"/api/review/review/knowledge/{kb1.id}/approve")
        moderator_client.post(
            f"/api/review/review/knowledge/{kb2.id}/reject",
            json={"reason": "Test"}
        )

        # Verify both records have correct status
        test_db.refresh(record1)
        test_db.refresh(record2)
        assert record1.status == "approved"
        assert record2.status == "rejected"


class TestReviewNotifications:
    """Test notification system for review decisions"""

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_notification_sent_on_knowledge_base_approval(self, mock_broadcast, moderator_client, test_db, test_user, moderator_user):
        """Test notification is sent when knowledge base is approved"""
        # Create pending knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()

        # Approve knowledge base
        response = moderator_client.post(f"/api/review/review/knowledge/{kb.id}/approve")
        assert response.status_code == 200

        # Verify notification message created
        message = test_db.query(Message).filter(
            Message.recipient_id == test_user.id,
            Message.sender_id == moderator_user.id
        ).first()
        assert message is not None
        assert "审核通过" in message.title
        assert kb.name in message.content

        # Verify WebSocket broadcast was called
        mock_broadcast.assert_called_once()

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_notification_sent_on_knowledge_base_rejection(self, mock_broadcast, moderator_client, test_db, test_user, moderator_user):
        """Test notification is sent when knowledge base is rejected"""
        # Create pending knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()

        # Reject knowledge base
        rejection_reason = "Content quality issues"
        response = moderator_client.post(
            f"/api/review/review/knowledge/{kb.id}/reject",
            json={"reason": rejection_reason}
        )
        assert response.status_code == 200

        # Verify notification message created
        message = test_db.query(Message).filter(
            Message.recipient_id == test_user.id,
            Message.sender_id == moderator_user.id
        ).first()
        assert message is not None
        assert "审核未通过" in message.title
        assert kb.name in message.content
        assert rejection_reason in message.content

        # Verify WebSocket broadcast was called
        mock_broadcast.assert_called_once()

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_notification_sent_on_persona_card_approval(self, mock_broadcast, moderator_client, test_db, test_user, moderator_user):
        """Test notification is sent when persona card is approved"""
        # Create pending persona card
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(pc)
        test_db.commit()

        # Approve persona card
        response = moderator_client.post(f"/api/review/review/persona/{pc.id}/approve")
        assert response.status_code == 200

        # Verify notification message created
        message = test_db.query(Message).filter(
            Message.recipient_id == test_user.id,
            Message.sender_id == moderator_user.id
        ).first()
        assert message is not None
        assert "审核通过" in message.title
        assert pc.name in message.content

        # Verify WebSocket broadcast was called
        mock_broadcast.assert_called_once()

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_notification_sent_on_persona_card_rejection(self, mock_broadcast, moderator_client, test_db, test_user, moderator_user):
        """Test notification is sent when persona card is rejected"""
        # Create pending persona card
        pc = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test PC",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(pc)
        test_db.commit()

        # Reject persona card
        rejection_reason = "Inappropriate character description"
        response = moderator_client.post(
            f"/api/review/review/persona/{pc.id}/reject",
            json={"reason": rejection_reason}
        )
        assert response.status_code == 200

        # Verify notification message created
        message = test_db.query(Message).filter(
            Message.recipient_id == test_user.id,
            Message.sender_id == moderator_user.id
        ).first()
        assert message is not None
        assert "审核未通过" in message.title
        assert pc.name in message.content
        assert rejection_reason in message.content

        # Verify WebSocket broadcast was called
        mock_broadcast.assert_called_once()

    @patch('app.utils.websocket.message_ws_manager.broadcast_user_update', new_callable=AsyncMock)
    def test_notification_includes_rejection_reason(self, mock_broadcast, moderator_client, test_db, test_user):
        """Test rejection notification includes the reason provided by moderator"""
        # Create pending knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            uploader_id=test_user.id,
            is_pending=True,
            is_public=False,
            base_path="/test/path",
            created_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()

        # Reject with specific reason
        rejection_reason = "The content contains copyrighted material without proper attribution"
        response = moderator_client.post(
            f"/api/review/review/knowledge/{kb.id}/reject",
            json={"reason": rejection_reason}
        )
        assert response.status_code == 200

        # Verify rejection reason is in notification
        message = test_db.query(Message).filter(Message.recipient_id == test_user.id).first()
        assert message is not None
        assert rejection_reason in message.content
        assert "拒绝原因" in message.content
