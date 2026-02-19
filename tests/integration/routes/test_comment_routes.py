"""
Integration tests for comment routes
Tests comment listing, creation, and reactions on knowledge bases and persona cards

Requirements: 1.2 - Comment routes coverage
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.database import Comment, CommentReaction
from tests.test_data_factory import TestDataFactory


class TestGetComments:
    """Test GET /api/comments endpoint"""
    
    def test_get_comments_for_knowledge_base(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test getting comments for a knowledge base"""
        # Create knowledge base and comments
        kb = factory.create_knowledge_base()
        user1 = factory.create_user(username="commenter1")
        user2 = factory.create_user(username="commenter2")
        
        comment1 = factory.create_comment(user=user1, target_id=kb.id, target_type="knowledge", content="Great knowledge base!")
        comment2 = factory.create_comment(user=user2, target_id=kb.id, target_type="knowledge", content="Very helpful!")
        
        # Get comments
        response = authenticated_client.get(f"/api/comments/comments?target_type=knowledge&target_id={kb.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        comments = data["data"]
        
        # Verify comments are returned
        assert len(comments) >= 2
        comment_contents = [c["content"] for c in comments]
        assert "Great knowledge base!" in comment_contents
        assert "Very helpful!" in comment_contents
        
        # Verify comment structure
        comment = comments[0]
        assert "id" in comment
        assert "userId" in comment
        assert "username" in comment
        assert "content" in comment
        assert "createdAt" in comment
        assert "likeCount" in comment
        assert "dislikeCount" in comment
        assert "myReaction" in comment
    
    def test_get_comments_for_persona_card(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test getting comments for a persona card"""
        # Create persona card and comments
        persona = factory.create_persona_card()
        user1 = factory.create_user(username="persona_commenter1")
        
        comment1 = factory.create_comment(user=user1, target_id=persona.id, target_type="persona", content="Nice persona!")
        
        # Get comments
        response = authenticated_client.get(f"/api/comments/comments?target_type=persona&target_id={persona.id}")
        
        assert response.status_code == 200
        data = response.json()
        comments = data["data"]
        
        # Verify comment is returned
        assert len(comments) >= 1
        assert comments[0]["content"] == "Nice persona!"
    
    def test_get_comments_ordered_by_created_at(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test comments are ordered by creation date (oldest first)"""
        kb = factory.create_knowledge_base()
        user = factory.create_user()
        
        # Create comments in sequence
        comment1 = factory.create_comment(user=user, target_id=kb.id, target_type="knowledge", content="First comment")
        comment2 = factory.create_comment(user=user, target_id=kb.id, target_type="knowledge", content="Second comment")
        
        response = authenticated_client.get(f"/api/comments/comments?target_type=knowledge&target_id={kb.id}")
        
        assert response.status_code == 200
        comments = response.json()["data"]
        
        # Find our test comments
        test_comments = [c for c in comments if c["content"] in ["First comment", "Second comment"]]
        if len(test_comments) == 2:
            # Older comment should appear first
            assert test_comments[0]["content"] == "First comment"
            assert test_comments[1]["content"] == "Second comment"
    
    def test_get_comments_excludes_deleted(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test deleted comments are not returned"""
        kb = factory.create_knowledge_base()
        user = factory.create_user()
        
        # Create normal and deleted comments
        comment1 = factory.create_comment(user=user, target_id=kb.id, target_type="knowledge", content="Visible comment")
        comment2 = factory.create_comment(user=user, target_id=kb.id, target_type="knowledge", content="Deleted comment", is_deleted=True)
        
        response = authenticated_client.get(f"/api/comments/comments?target_type=knowledge&target_id={kb.id}")
        
        assert response.status_code == 200
        comments = response.json()["data"]
        
        # Verify deleted comment is not returned
        comment_contents = [c["content"] for c in comments]
        assert "Visible comment" in comment_contents
        assert "Deleted comment" not in comment_contents
    
    def test_get_comments_includes_nested_comments(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test nested comments (replies) are included"""
        kb = factory.create_knowledge_base()
        user1 = factory.create_user()
        user2 = factory.create_user()
        
        # Create parent comment and reply
        parent = factory.create_comment(user=user1, target_id=kb.id, target_type="knowledge", content="Parent comment")
        reply = factory.create_comment(user=user2, target_id=kb.id, target_type="knowledge", content="Reply comment", parent_id=parent.id)
        
        response = authenticated_client.get(f"/api/comments/comments?target_type=knowledge&target_id={kb.id}")
        
        assert response.status_code == 200
        comments = response.json()["data"]
        
        # Verify both parent and reply are returned
        comment_contents = [c["content"] for c in comments]
        assert "Parent comment" in comment_contents
        assert "Reply comment" in comment_contents
        
        # Verify reply has parentId set
        reply_comment = next(c for c in comments if c["content"] == "Reply comment")
        assert reply_comment["parentId"] == parent.id
    
    def test_get_comments_includes_user_reaction(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test comments include current user's reaction"""
        kb = factory.create_knowledge_base()
        
        # Create comment and reaction from test user
        comment = factory.create_comment(target_id=kb.id, target_type="knowledge", content="Test comment")
        reaction = factory.create_comment_reaction(user=test_user, comment=comment, reaction_type="like")
        
        response = authenticated_client.get(f"/api/comments/comments?target_type=knowledge&target_id={kb.id}")
        
        assert response.status_code == 200
        comments = response.json()["data"]
        
        # Find our comment
        test_comment = next((c for c in comments if c["id"] == comment.id), None)
        assert test_comment is not None
        assert test_comment["myReaction"] == "like"
    
    def test_get_comments_invalid_target_type(self, authenticated_client, test_db: Session):
        """Test getting comments with invalid target type fails"""
        response = authenticated_client.get("/api/comments/comments?target_type=invalid&target_id=123")
        
        assert response.status_code == 422
        data = response.json()
        # The error message is wrapped by error handler
        assert "评论目标类型不合法" in data["error"]["message"] or "目标类型必须是 knowledge 或 persona" in data["error"]["message"]
    
    def test_get_comments_empty_list(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test getting comments for target with no comments returns empty list"""
        kb = factory.create_knowledge_base()
        
        response = authenticated_client.get(f"/api/comments/comments?target_type=knowledge&target_id={kb.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []


class TestCreateComment:
    """Test POST /api/comments endpoint"""
    
    def test_create_comment_on_knowledge_base(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test creating a comment on a knowledge base"""
        kb = factory.create_knowledge_base()
        
        comment_data = {
            "content": "This is a test comment",
            "target_type": "knowledge",
            "target_id": kb.id
        }
        
        response = authenticated_client.post("/api/comments/comments", json=comment_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "发表评论成功"
        assert data["data"]["content"] == "This is a test comment"
        assert data["data"]["userId"] is not None
        assert data["data"]["username"] is not None
        assert data["data"]["likeCount"] == 0
        assert data["data"]["dislikeCount"] == 0
        assert data["data"]["myReaction"] is None
        
        # Verify comment was created in database
        comment = test_db.query(Comment).filter(Comment.id == data["data"]["id"]).first()
        assert comment is not None
        assert comment.content == "This is a test comment"
        assert comment.target_type == "knowledge"
        assert comment.target_id == kb.id
    
    def test_create_comment_on_persona_card(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test creating a comment on a persona card"""
        persona = factory.create_persona_card()
        
        comment_data = {
            "content": "Great persona card!",
            "target_type": "persona",
            "target_id": persona.id
        }
        
        response = authenticated_client.post("/api/comments/comments", json=comment_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["content"] == "Great persona card!"
        
        # Verify in database
        comment = test_db.query(Comment).filter(Comment.id == data["data"]["id"]).first()
        assert comment.target_type == "persona"
        assert comment.target_id == persona.id
    
    def test_create_nested_comment_reply(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test creating a reply to an existing comment"""
        kb = factory.create_knowledge_base()
        user = factory.create_user()
        
        # Create parent comment
        parent = factory.create_comment(user=user, target_id=kb.id, target_type="knowledge", content="Parent comment")
        
        # Create reply
        reply_data = {
            "content": "This is a reply",
            "target_type": "knowledge",
            "target_id": kb.id,
            "parent_id": parent.id
        }
        
        response = authenticated_client.post("/api/comments/comments", json=reply_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["content"] == "This is a reply"
        assert data["data"]["parentId"] == parent.id
        
        # Verify in database
        reply = test_db.query(Comment).filter(Comment.id == data["data"]["id"]).first()
        assert reply.parent_id == parent.id
    
    def test_create_comment_empty_content_fails(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test creating comment with empty content fails"""
        kb = factory.create_knowledge_base()
        
        comment_data = {
            "content": "",
            "target_type": "knowledge",
            "target_id": kb.id
        }
        
        response = authenticated_client.post("/api/comments/comments", json=comment_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "评论内容不能为空" in data["error"]["message"]
    
    def test_create_comment_whitespace_only_fails(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test creating comment with only whitespace fails"""
        kb = factory.create_knowledge_base()
        
        comment_data = {
            "content": "   ",
            "target_type": "knowledge",
            "target_id": kb.id
        }
        
        response = authenticated_client.post("/api/comments/comments", json=comment_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "评论内容不能为空" in data["error"]["message"]
    
    def test_create_comment_too_long_fails(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test creating comment exceeding 500 characters fails"""
        kb = factory.create_knowledge_base()
        
        comment_data = {
            "content": "a" * 501,  # 501 characters
            "target_type": "knowledge",
            "target_id": kb.id
        }
        
        response = authenticated_client.post("/api/comments/comments", json=comment_data)
        
        assert response.status_code == 422
        data = response.json()
        # Error message may be wrapped by error handler
        assert "500" in data["error"]["message"] or "评论内容不能超过500字" in data["error"]["message"]
    
    def test_create_comment_invalid_target_type_fails(self, authenticated_client, test_db: Session):
        """Test creating comment with invalid target type fails"""
        comment_data = {
            "content": "Test comment",
            "target_type": "invalid",
            "target_id": "123"
        }
        
        response = authenticated_client.post("/api/comments/comments", json=comment_data)
        
        assert response.status_code == 422
        data = response.json()
        # Error message may be wrapped by error handler
        assert "目标类型" in data["error"]["message"] or "评论目标类型不合法" in data["error"]["message"]
    
    def test_create_comment_nonexistent_target_fails(self, authenticated_client, test_db: Session):
        """Test creating comment on nonexistent target fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        comment_data = {
            "content": "Test comment",
            "target_type": "knowledge",
            "target_id": fake_id
        }
        
        response = authenticated_client.post("/api/comments/comments", json=comment_data)
        
        assert response.status_code == 404
        data = response.json()
        assert "目标内容不存在" in data["error"]["message"]
    
    def test_create_comment_nonexistent_parent_fails(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test creating reply to nonexistent parent comment fails"""
        kb = factory.create_knowledge_base()
        fake_parent_id = "00000000-0000-0000-0000-000000000000"
        
        comment_data = {
            "content": "Test reply",
            "target_type": "knowledge",
            "target_id": kb.id,
            "parent_id": fake_parent_id
        }
        
        response = authenticated_client.post("/api/comments/comments", json=comment_data)
        
        assert response.status_code == 422
        data = response.json()
        # Error message may be wrapped by error handler
        assert "父级评论" in data["error"]["message"] or "上级评论" in data["error"]["message"]
    
    def test_create_comment_muted_user_temporary_fails(self, test_db: Session, factory: TestDataFactory):
        """Test muted user cannot create comments (temporary mute)"""
        from datetime import datetime, timedelta
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create muted user
        muted_until = datetime.now() + timedelta(days=1)
        muted_user = factory.create_user(
            username="muteduser",
            password="password123",
            is_muted=True,
            muted_until=muted_until,
            mute_reason="Test mute"
        )
        
        # Login as muted user
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "muteduser", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to create comment
        kb = factory.create_knowledge_base()
        comment_data = {
            "content": "Test comment",
            "target_type": "knowledge",
            "target_id": kb.id
        }
        
        response = client.post("/api/comments/comments", json=comment_data)
        
        assert response.status_code == 403
        data = response.json()
        assert "禁言状态" in data["error"]["message"]
        assert "Test mute" in data["error"]["message"]
    
    def test_create_comment_muted_user_permanent_fails(self, test_db: Session, factory: TestDataFactory):
        """Test permanently muted user cannot create comments"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create permanently muted user
        muted_user = factory.create_user(
            username="permamuted",
            password="password123",
            is_muted=True,
            muted_until=None,  # Permanent mute
            mute_reason="Severe violations"
        )
        
        # Login as muted user
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "permamuted", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to create comment
        kb = factory.create_knowledge_base()
        comment_data = {
            "content": "Test comment",
            "target_type": "knowledge",
            "target_id": kb.id
        }
        
        response = client.post("/api/comments/comments", json=comment_data)
        
        assert response.status_code == 403
        data = response.json()
        assert "永久禁言" in data["error"]["message"]
        assert "Severe violations" in data["error"]["message"]
    
    def test_create_comment_unauthenticated_fails(self, test_db: Session, factory: TestDataFactory):
        """Test unauthenticated user cannot create comments"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        kb = factory.create_knowledge_base()
        
        comment_data = {
            "content": "Test comment",
            "target_type": "knowledge",
            "target_id": kb.id
        }
        
        response = client.post("/api/comments/comments", json=comment_data)
        
        assert response.status_code == 401


class TestDeleteComment:
    """Test DELETE /api/comments/{id} endpoint"""
    
    def test_delete_own_comment(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test user can delete their own comment"""
        kb = factory.create_knowledge_base()
        comment = factory.create_comment(user=test_user, target_id=kb.id, target_type="knowledge", content="My comment")
        
        response = authenticated_client.delete(f"/api/comments/comments/{comment.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "删除评论成功"
        assert data["data"]["id"] == comment.id
        
        # Verify comment is soft deleted
        test_db.refresh(comment)
        assert comment.is_deleted is True
    
    def test_delete_comment_cascades_to_replies(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test deleting parent comment also deletes child comments"""
        kb = factory.create_knowledge_base()
        parent = factory.create_comment(user=test_user, target_id=kb.id, target_type="knowledge", content="Parent")
        child1 = factory.create_comment(user=test_user, target_id=kb.id, target_type="knowledge", content="Child 1", parent_id=parent.id)
        child2 = factory.create_comment(user=test_user, target_id=kb.id, target_type="knowledge", content="Child 2", parent_id=parent.id)
        
        response = authenticated_client.delete(f"/api/comments/comments/{parent.id}")
        
        assert response.status_code == 200
        
        # Verify all comments are soft deleted
        test_db.refresh(parent)
        test_db.refresh(child1)
        test_db.refresh(child2)
        assert parent.is_deleted is True
        assert child1.is_deleted is True
        assert child2.is_deleted is True

    
    def test_delete_child_comment_only(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test deleting child comment doesn't delete parent"""
        kb = factory.create_knowledge_base()
        parent = factory.create_comment(user=test_user, target_id=kb.id, target_type="knowledge", content="Parent")
        child = factory.create_comment(user=test_user, target_id=kb.id, target_type="knowledge", content="Child", parent_id=parent.id)
        
        response = authenticated_client.delete(f"/api/comments/comments/{child.id}")
        
        assert response.status_code == 200
        
        # Verify only child is deleted
        test_db.refresh(parent)
        test_db.refresh(child)
        assert parent.is_deleted is False
        assert child.is_deleted is True
    
    def test_delete_comment_nonexistent_fails(self, authenticated_client, test_db: Session):
        """Test deleting nonexistent comment fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = authenticated_client.delete(f"/api/comments/comments/{fake_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "评论不存在" in data["error"]["message"]
    
    def test_delete_other_user_comment_fails(self, test_db: Session, factory: TestDataFactory):
        """Test user cannot delete another user's comment"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create comment by user1
        user1 = factory.create_user(username="user1", password="password123")
        kb = factory.create_knowledge_base()
        comment = factory.create_comment(user=user1, target_id=kb.id, target_type="knowledge", content="User1 comment")
        
        # Login as user2
        user2 = factory.create_user(username="user2", password="password123")
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "user2", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to delete user1's comment
        response = client.delete(f"/api/comments/comments/{comment.id}")
        
        assert response.status_code == 403
        data = response.json()
        assert "没有权限删除此评论" in data["error"]["message"]



class TestRestoreComment:
    """Test POST /api/comments/{id}/restore endpoint"""
    
    def test_restore_own_deleted_comment(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test user can restore their own deleted comment"""
        kb = factory.create_knowledge_base()
        comment = factory.create_comment(user=test_user, target_id=kb.id, target_type="knowledge", content="My comment", is_deleted=True)
        
        response = authenticated_client.post(f"/api/comments/comments/{comment.id}/restore")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "撤销删除评论成功"
        assert data["data"]["id"] == comment.id
        
        # Verify comment is restored
        test_db.refresh(comment)
        assert comment.is_deleted is False
    
    def test_restore_comment_restores_replies(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test restoring parent comment also restores child comments"""
        kb = factory.create_knowledge_base()
        parent = factory.create_comment(user=test_user, target_id=kb.id, target_type="knowledge", content="Parent", is_deleted=True)
        child1 = factory.create_comment(user=test_user, target_id=kb.id, target_type="knowledge", content="Child 1", parent_id=parent.id, is_deleted=True)
        child2 = factory.create_comment(user=test_user, target_id=kb.id, target_type="knowledge", content="Child 2", parent_id=parent.id, is_deleted=True)
        
        response = authenticated_client.post(f"/api/comments/comments/{parent.id}/restore")
        
        assert response.status_code == 200
        
        # Verify all comments are restored
        test_db.refresh(parent)
        test_db.refresh(child1)
        test_db.refresh(child2)
        assert parent.is_deleted is False
        assert child1.is_deleted is False
        assert child2.is_deleted is False
    
    def test_restore_comment_nonexistent_fails(self, authenticated_client, test_db: Session):
        """Test restoring nonexistent comment fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = authenticated_client.post(f"/api/comments/comments/{fake_id}/restore")
        
        assert response.status_code == 404
        data = response.json()
        assert "评论不存在" in data["error"]["message"]

    
    def test_restore_other_user_comment_fails(self, test_db: Session, factory: TestDataFactory):
        """Test user cannot restore another user's comment"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create deleted comment by user1
        user1 = factory.create_user(username="user1", password="password123")
        kb = factory.create_knowledge_base()
        comment = factory.create_comment(user=user1, target_id=kb.id, target_type="knowledge", content="User1 comment", is_deleted=True)
        
        # Login as user2
        user2 = factory.create_user(username="user2", password="password123")
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "user2", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to restore user1's comment
        response = client.post(f"/api/comments/comments/{comment.id}/restore")
        
        assert response.status_code == 403
        data = response.json()
        assert "没有权限撤销此评论删除" in data["error"]["message"]


class TestCommentReactions:
    """Test POST /api/comments/{id}/react endpoint"""
    
    def test_add_like_to_comment(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test adding a like reaction to a comment"""
        kb = factory.create_knowledge_base()
        other_user = factory.create_user(username="other")
        comment = factory.create_comment(user=other_user, target_id=kb.id, target_type="knowledge", content="Test comment")
        
        response = authenticated_client.post(
            f"/api/comments/comments/{comment.id}/react",
            json={"action": "like"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "操作成功"
        assert data["data"]["likeCount"] == 1
        assert data["data"]["dislikeCount"] == 0
        assert data["data"]["myReaction"] == "like"
        
        # Verify in database
        test_db.refresh(comment)
        assert comment.like_count == 1
        assert comment.dislike_count == 0
        
        reaction = test_db.query(CommentReaction).filter(
            CommentReaction.comment_id == comment.id,
            CommentReaction.user_id == test_user.id
        ).first()
        assert reaction is not None
        assert reaction.reaction_type == "like"

    
    def test_add_dislike_to_comment(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test adding a dislike reaction to a comment"""
        kb = factory.create_knowledge_base()
        other_user = factory.create_user(username="other")
        comment = factory.create_comment(user=other_user, target_id=kb.id, target_type="knowledge", content="Test comment")
        
        response = authenticated_client.post(
            f"/api/comments/comments/{comment.id}/react",
            json={"action": "dislike"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["likeCount"] == 0
        assert data["data"]["dislikeCount"] == 1
        assert data["data"]["myReaction"] == "dislike"
        
        # Verify in database
        test_db.refresh(comment)
        assert comment.like_count == 0
        assert comment.dislike_count == 1
        
        reaction = test_db.query(CommentReaction).filter(
            CommentReaction.comment_id == comment.id,
            CommentReaction.user_id == test_user.id
        ).first()
        assert reaction is not None
        assert reaction.reaction_type == "dislike"
    
    def test_toggle_like_removes_like(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test clicking like again removes the like"""
        kb = factory.create_knowledge_base()
        other_user = factory.create_user(username="other")
        comment = factory.create_comment(user=other_user, target_id=kb.id, target_type="knowledge", content="Test comment")
        
        # Add like
        factory.create_comment_reaction(user=test_user, comment=comment, reaction_type="like")
        comment.like_count = 1
        test_db.commit()
        
        # Toggle like (remove)
        response = authenticated_client.post(
            f"/api/comments/comments/{comment.id}/react",
            json={"action": "like"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["likeCount"] == 0
        assert data["data"]["myReaction"] is None
        
        # Verify reaction is removed from database
        reaction = test_db.query(CommentReaction).filter(
            CommentReaction.comment_id == comment.id,
            CommentReaction.user_id == test_user.id
        ).first()
        assert reaction is None

    
    def test_change_like_to_dislike(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test changing from like to dislike"""
        kb = factory.create_knowledge_base()
        other_user = factory.create_user(username="other")
        comment = factory.create_comment(user=other_user, target_id=kb.id, target_type="knowledge", content="Test comment")
        
        # Add like
        factory.create_comment_reaction(user=test_user, comment=comment, reaction_type="like")
        comment.like_count = 1
        test_db.commit()
        
        # Change to dislike
        response = authenticated_client.post(
            f"/api/comments/comments/{comment.id}/react",
            json={"action": "dislike"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["likeCount"] == 0
        assert data["data"]["dislikeCount"] == 1
        assert data["data"]["myReaction"] == "dislike"
        
        # Verify in database
        test_db.refresh(comment)
        assert comment.like_count == 0
        assert comment.dislike_count == 1
        
        reaction = test_db.query(CommentReaction).filter(
            CommentReaction.comment_id == comment.id,
            CommentReaction.user_id == test_user.id
        ).first()
        assert reaction is not None
        assert reaction.reaction_type == "dislike"
    
    def test_change_dislike_to_like(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test changing from dislike to like"""
        kb = factory.create_knowledge_base()
        other_user = factory.create_user(username="other")
        comment = factory.create_comment(user=other_user, target_id=kb.id, target_type="knowledge", content="Test comment")
        
        # Add dislike
        factory.create_comment_reaction(user=test_user, comment=comment, reaction_type="dislike")
        comment.dislike_count = 1
        test_db.commit()
        
        # Change to like
        response = authenticated_client.post(
            f"/api/comments/comments/{comment.id}/react",
            json={"action": "like"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["likeCount"] == 1
        assert data["data"]["dislikeCount"] == 0
        assert data["data"]["myReaction"] == "like"

    
    def test_clear_reaction(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test clearing a reaction using clear action"""
        kb = factory.create_knowledge_base()
        other_user = factory.create_user(username="other")
        comment = factory.create_comment(user=other_user, target_id=kb.id, target_type="knowledge", content="Test comment")
        
        # Add like
        factory.create_comment_reaction(user=test_user, comment=comment, reaction_type="like")
        comment.like_count = 1
        test_db.commit()
        
        # Clear reaction
        response = authenticated_client.post(
            f"/api/comments/comments/{comment.id}/react",
            json={"action": "clear"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["likeCount"] == 0
        assert data["data"]["myReaction"] is None
        
        # Verify reaction is removed
        reaction = test_db.query(CommentReaction).filter(
            CommentReaction.comment_id == comment.id,
            CommentReaction.user_id == test_user.id
        ).first()
        assert reaction is None
    
    def test_react_to_nonexistent_comment_fails(self, authenticated_client, test_db: Session):
        """Test reacting to nonexistent comment fails"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = authenticated_client.post(
            f"/api/comments/comments/{fake_id}/react",
            json={"action": "like"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "评论不存在" in data["error"]["message"]
    
    def test_react_to_deleted_comment_fails(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test reacting to deleted comment fails"""
        kb = factory.create_knowledge_base()
        user = factory.create_user()
        comment = factory.create_comment(user=user, target_id=kb.id, target_type="knowledge", content="Deleted", is_deleted=True)
        
        response = authenticated_client.post(
            f"/api/comments/comments/{comment.id}/react",
            json={"action": "like"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "评论不存在或已删除" in data["error"]["message"]

    
    def test_react_invalid_action_fails(self, authenticated_client, test_db: Session, factory: TestDataFactory):
        """Test reacting with invalid action fails"""
        kb = factory.create_knowledge_base()
        user = factory.create_user()
        comment = factory.create_comment(user=user, target_id=kb.id, target_type="knowledge", content="Test")
        
        response = authenticated_client.post(
            f"/api/comments/comments/{comment.id}/react",
            json={"action": "invalid"}
        )
        
        assert response.status_code == 422
        data = response.json()
        # Error message may be wrapped by error handler
        assert "action 必须是 like、dislike 或 clear" in data["error"]["message"] or "不支持的评论操作类型" in data["error"]["message"]


class TestCommentPermissions:
    """Test comment permission enforcement"""
    
    def test_content_owner_can_delete_any_comment(self, test_db: Session, factory: TestDataFactory):
        """Test knowledge base owner can delete any comment on their content"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create knowledge base owner
        owner = factory.create_user(username="owner", password="password123")
        kb = factory.create_knowledge_base(uploader=owner)
        
        # Create comment by another user
        commenter = factory.create_user(username="commenter")
        comment = factory.create_comment(user=commenter, target_id=kb.id, target_type="knowledge", content="Comment")
        
        # Login as owner
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "owner", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Owner should be able to delete comment
        response = client.delete(f"/api/comments/comments/{comment.id}")
        
        assert response.status_code == 200
        test_db.refresh(comment)
        assert comment.is_deleted is True

    
    def test_moderator_can_delete_any_comment(self, test_db: Session, factory: TestDataFactory):
        """Test moderator can delete any comment"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create moderator
        moderator = factory.create_user(username="moderator", password="password123", is_moderator=True)
        
        # Create comment by another user
        commenter = factory.create_user(username="commenter")
        kb = factory.create_knowledge_base()
        comment = factory.create_comment(user=commenter, target_id=kb.id, target_type="knowledge", content="Comment")
        
        # Login as moderator
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "moderator", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Moderator should be able to delete comment
        response = client.delete(f"/api/comments/comments/{comment.id}")
        
        assert response.status_code == 200
        test_db.refresh(comment)
        assert comment.is_deleted is True
    
    def test_admin_can_delete_any_comment(self, test_db: Session, factory: TestDataFactory):
        """Test admin can delete any comment"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create admin
        admin = factory.create_user(username="admin", password="password123", is_admin=True)
        
        # Create comment by another user
        commenter = factory.create_user(username="commenter")
        kb = factory.create_knowledge_base()
        comment = factory.create_comment(user=commenter, target_id=kb.id, target_type="knowledge", content="Comment")
        
        # Login as admin
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "admin", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Admin should be able to delete comment
        response = client.delete(f"/api/comments/comments/{comment.id}")
        
        assert response.status_code == 200
        test_db.refresh(comment)
        assert comment.is_deleted is True

    
    def test_content_owner_can_restore_any_comment(self, test_db: Session, factory: TestDataFactory):
        """Test content owner can restore any comment on their content"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create persona card owner
        owner = factory.create_user(username="owner", password="password123")
        persona = factory.create_persona_card(uploader=owner)
        
        # Create deleted comment by another user
        commenter = factory.create_user(username="commenter")
        comment = factory.create_comment(user=commenter, target_id=persona.id, target_type="persona", content="Comment", is_deleted=True)
        
        # Login as owner
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "owner", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Owner should be able to restore comment
        response = client.post(f"/api/comments/comments/{comment.id}/restore")
        
        assert response.status_code == 200
        test_db.refresh(comment)
        assert comment.is_deleted is False
    
    def test_moderator_can_restore_any_comment(self, test_db: Session, factory: TestDataFactory):
        """Test moderator can restore any comment"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create moderator
        moderator = factory.create_user(username="moderator", password="password123", is_moderator=True)
        
        # Create deleted comment by another user
        commenter = factory.create_user(username="commenter")
        kb = factory.create_knowledge_base()
        comment = factory.create_comment(user=commenter, target_id=kb.id, target_type="knowledge", content="Comment", is_deleted=True)
        
        # Login as moderator
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "moderator", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Moderator should be able to restore comment
        response = client.post(f"/api/comments/comments/{comment.id}/restore")
        
        assert response.status_code == 200
        test_db.refresh(comment)
        assert comment.is_deleted is False

    
    def test_nested_comment_creation_by_any_user(self, test_db: Session, factory: TestDataFactory):
        """Test any authenticated user can create nested comments (replies)"""
        from app.main import app
        from fastapi.testclient import TestClient
        
        # Create parent comment by user1
        user1 = factory.create_user(username="user1")
        kb = factory.create_knowledge_base()
        parent = factory.create_comment(user=user1, target_id=kb.id, target_type="knowledge", content="Parent comment")
        
        # Login as user2
        user2 = factory.create_user(username="user2", password="password123")
        client = TestClient(app)
        login_response = client.post(
            "/api/auth/token",
            data={"username": "user2", "password": "password123"}
        )
        token = login_response.json()["data"]["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # User2 should be able to reply to user1's comment
        reply_data = {
            "content": "Reply to parent",
            "target_type": "knowledge",
            "target_id": kb.id,
            "parent_id": parent.id
        }
        
        response = client.post("/api/comments/comments", json=reply_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["content"] == "Reply to parent"
        assert data["data"]["parentId"] == parent.id
        
        # Verify in database
        reply = test_db.query(Comment).filter(Comment.id == data["data"]["id"]).first()
        assert reply is not None
        assert reply.parent_id == parent.id
        assert reply.user_id == user2.id
    
    def test_deeply_nested_comments_allowed(self, authenticated_client, test_db: Session, factory: TestDataFactory, test_user):
        """Test creating replies to replies (deeply nested comments)"""
        kb = factory.create_knowledge_base()
        
        # Create parent comment
        parent = factory.create_comment(user=test_user, target_id=kb.id, target_type="knowledge", content="Level 1")
        
        # Create first level reply
        reply1_data = {
            "content": "Level 2 reply",
            "target_type": "knowledge",
            "target_id": kb.id,
            "parent_id": parent.id
        }
        response1 = authenticated_client.post("/api/comments/comments", json=reply1_data)
        assert response1.status_code == 200
        reply1_id = response1.json()["data"]["id"]
        
        # Create second level reply (reply to reply)
        reply2_data = {
            "content": "Level 3 reply",
            "target_type": "knowledge",
            "target_id": kb.id,
            "parent_id": reply1_id
        }
        response2 = authenticated_client.post("/api/comments/comments", json=reply2_data)
        assert response2.status_code == 200
        
        # Verify both replies exist
        reply1 = test_db.query(Comment).filter(Comment.id == reply1_id).first()
        reply2 = test_db.query(Comment).filter(Comment.id == response2.json()["data"]["id"]).first()
        
        assert reply1.parent_id == parent.id
        assert reply2.parent_id == reply1.id
