"""
评论路由集成测试
测试评论的CRUD操作、反应和权限

需求：3.4
"""

import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.database import Comment, CommentReaction, User
from tests.conftest import assert_error_response


class TestGetComments:
    """Test GET /api/comments endpoint"""

    def test_get_comments_for_knowledge_base_success(self, authenticated_client: TestClient, test_db: Session, factory):
        """Test successful retrieval of comments for knowledge base

        验证：
        - 返回 200 状态码
        - 返回评论列表
        - 评论按创建时间升序排列
        """
        # Create knowledge base and comments
        kb = factory.create_knowledge_base()
        user1 = factory.create_user()
        user2 = factory.create_user()

        comment1 = Comment(
            user_id=user1.id,
            target_type="knowledge",
            target_id=kb.id,
            content="First comment",
            created_at=datetime.now(),
        )
        comment2 = Comment(
            user_id=user2.id,
            target_type="knowledge",
            target_id=kb.id,
            content="Second comment",
            created_at=datetime.now() + timedelta(seconds=1),
        )
        test_db.add_all([comment1, comment2])
        test_db.commit()

        response = authenticated_client.get(f"/api/comments?target_type=knowledge&target_id={kb.id}")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2
        assert data["data"][0]["content"] == "First comment"
        assert data["data"][1]["content"] == "Second comment"

    def test_get_comments_for_persona_card_success(self, authenticated_client: TestClient, test_db: Session, factory):
        """Test successful retrieval of comments for persona card

        验证：
        - 返回 200 状态码
        - 返回评论列表
        """
        pc = factory.create_persona_card()
        user = factory.create_user()

        comment = Comment(user_id=user.id, target_type="persona", target_id=pc.id, content="Persona comment")
        test_db.add(comment)
        test_db.commit()

        response = authenticated_client.get(f"/api/comments?target_type=persona&target_id={pc.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["content"] == "Persona comment"

    def test_get_comments_excludes_deleted(self, authenticated_client: TestClient, test_db: Session, factory):
        """Test that deleted comments are not returned

        验证：
        - 已删除的评论不在结果中
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment1 = Comment(
            user_id=user.id, target_type="knowledge", target_id=kb.id, content="Active comment", is_deleted=False
        )
        comment2 = Comment(
            user_id=user.id, target_type="knowledge", target_id=kb.id, content="Deleted comment", is_deleted=True
        )
        test_db.add_all([comment1, comment2])
        test_db.commit()

        response = authenticated_client.get(f"/api/comments?target_type=knowledge&target_id={kb.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["content"] == "Active comment"

    def test_get_comments_includes_user_reaction(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test that comments include current user's reaction

        验证：
        - 评论包含当前用户的反应（like/dislike）
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(user_id=user.id, target_type="knowledge", target_id=kb.id, content="Test comment")
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        # Add reaction from test_user
        reaction = CommentReaction(user_id=test_user.id, comment_id=comment.id, reaction_type="like")
        test_db.add(reaction)
        test_db.commit()

        response = authenticated_client.get(f"/api/comments?target_type=knowledge&target_id={kb.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["myReaction"] == "like"

    def test_get_comments_invalid_target_type(self, authenticated_client: TestClient, test_db: Session):
        """Test get comments with invalid target type

        验证：
        - 返回 400 或 422 状态码
        - 返回错误消息
        """
        response = authenticated_client.get("/api/comments?target_type=invalid&target_id=123")

        assert_error_response(response, [400, 422], ["目标类型", "knowledge", "persona"])


class TestCreateComment:
    """Test POST /api/comments endpoint"""

    def test_create_comment_on_knowledge_base_success(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test successful comment creation on knowledge base

        验证：
        - 返回 200 状态码
        - 评论被创建
        - 返回评论数据
        """
        kb = factory.create_knowledge_base()

        response = authenticated_client.post(
            "/api/comments", json={"content": "Great knowledge base!", "target_type": "knowledge", "target_id": kb.id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["content"] == "Great knowledge base!"
        assert data["data"]["userId"] == test_user.id

        # Verify in database
        comment = test_db.query(Comment).filter(Comment.target_id == kb.id).first()
        assert comment is not None
        assert comment.content == "Great knowledge base!"

    def test_create_comment_on_persona_card_success(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test successful comment creation on persona card

        验证：
        - 返回 200 状态码
        - 评论被创建
        """
        pc = factory.create_persona_card()

        response = authenticated_client.post(
            "/api/comments", json={"content": "Nice persona card!", "target_type": "persona", "target_id": pc.id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["content"] == "Nice persona card!"

    def test_create_reply_to_comment_success(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test successful reply to existing comment

        验证：
        - 返回 200 状态码
        - 回复被创建
        - parent_id 正确设置
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        parent_comment = Comment(user_id=user.id, target_type="knowledge", target_id=kb.id, content="Parent comment")
        test_db.add(parent_comment)
        test_db.commit()
        test_db.refresh(parent_comment)

        response = authenticated_client.post(
            "/api/comments",
            json={
                "content": "Reply to comment",
                "target_type": "knowledge",
                "target_id": kb.id,
                "parent_id": parent_comment.id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["content"] == "Reply to comment"
        assert data["data"]["parentId"] == parent_comment.id

    def test_create_comment_empty_content_fails(self, authenticated_client: TestClient, test_db: Session, factory):
        """Test that empty comment content is rejected

        验证：
        - 返回 400 或 422 状态码
        - 返回错误消息
        """
        kb = factory.create_knowledge_base()

        response = authenticated_client.post(
            "/api/comments", json={"content": "   ", "target_type": "knowledge", "target_id": kb.id}
        )

        assert_error_response(response, [400, 422], ["内容", "不能为空"])

    def test_create_comment_too_long_fails(self, authenticated_client: TestClient, test_db: Session, factory):
        """Test that comment content exceeding 500 characters is rejected

        验证：
        - 返回 400 或 422 状态码
        - 返回错误消息
        """
        kb = factory.create_knowledge_base()

        response = authenticated_client.post(
            "/api/comments", json={"content": "a" * 501, "target_type": "knowledge", "target_id": kb.id}
        )

        assert_error_response(response, [400, 422], ["500"])

    def test_create_comment_invalid_target_type_fails(self, authenticated_client: TestClient, test_db: Session):
        """Test that invalid target type is rejected

        验证：
        - 返回 400 或 422 状态码
        - 返回错误消息
        """
        response = authenticated_client.post(
            "/api/comments", json={"content": "Test comment", "target_type": "invalid", "target_id": str(uuid.uuid4())}
        )

        assert_error_response(response, [400, 422], ["目标类型"])

    def test_create_comment_nonexistent_target_fails(self, authenticated_client: TestClient, test_db: Session):
        """Test that comment on nonexistent target fails

        验证：
        - 返回 404 状态码
        - 返回错误消息
        """
        response = authenticated_client.post(
            "/api/comments",
            json={"content": "Test comment", "target_type": "knowledge", "target_id": str(uuid.uuid4())},
        )

        assert_error_response(response, [404], ["不存在"])

    def test_create_comment_nonexistent_parent_fails(self, authenticated_client: TestClient, test_db: Session, factory):
        """Test that reply to nonexistent parent comment fails

        验证：
        - 返回 400 或 422 状态码
        - 返回错误消息
        """
        kb = factory.create_knowledge_base()

        response = authenticated_client.post(
            "/api/comments",
            json={"content": "Reply", "target_type": "knowledge", "target_id": kb.id, "parent_id": str(uuid.uuid4())},
        )

        assert_error_response(response, [400, 422], ["父级评论", "不存在"])

    def test_create_comment_when_muted_temporarily_fails(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test that muted user cannot create comment

        验证：
        - 返回 403 状态码
        - 返回禁言错误消息
        """
        # Mute the test user temporarily
        test_user.is_muted = True
        test_user.muted_until = datetime.now() + timedelta(days=1)
        test_user.mute_reason = "Test mute"
        test_db.commit()

        kb = factory.create_knowledge_base()

        response = authenticated_client.post(
            "/api/comments", json={"content": "Test comment", "target_type": "knowledge", "target_id": kb.id}
        )

        assert_error_response(response, [403], ["禁言"])

    def test_create_comment_when_permanently_muted_fails(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test that permanently muted user cannot create comment

        验证：
        - 返回 403 状态码
        - 返回永久禁言错误消息
        """
        # Permanently mute the test user
        test_user.is_muted = True
        test_user.muted_until = None
        test_user.mute_reason = "Permanent ban"
        test_db.commit()

        kb = factory.create_knowledge_base()

        response = authenticated_client.post(
            "/api/comments", json={"content": "Test comment", "target_type": "knowledge", "target_id": kb.id}
        )

        assert_error_response(response, [403], ["永久禁言"])


class TestReactComment:
    """Test POST /api/comments/{comment_id}/react endpoint"""

    def test_like_comment_success(self, authenticated_client: TestClient, test_db: Session, test_user: User, factory):
        """Test successful like on comment

        验证：
        - 返回 200 状态码
        - like_count 增加
        - myReaction 为 like
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(
            user_id=user.id, target_type="knowledge", target_id=kb.id, content="Test comment", like_count=0
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = authenticated_client.post(f"/api/comments/{comment.id}/react", json={"action": "like"})

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["likeCount"] == 1
        assert data["data"]["myReaction"] == "like"

    def test_dislike_comment_success(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test successful dislike on comment

        验证：
        - 返回 200 状态码
        - dislike_count 增加
        - myReaction 为 dislike
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(
            user_id=user.id, target_type="knowledge", target_id=kb.id, content="Test comment", dislike_count=0
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = authenticated_client.post(f"/api/comments/{comment.id}/react", json={"action": "dislike"})

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["dislikeCount"] == 1
        assert data["data"]["myReaction"] == "dislike"

    def test_toggle_like_removes_like(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test that liking again removes the like

        验证：
        - 返回 200 状态码
        - like_count 减少
        - myReaction 为 None
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(
            user_id=user.id, target_type="knowledge", target_id=kb.id, content="Test comment", like_count=1
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        # Add existing like
        reaction = CommentReaction(user_id=test_user.id, comment_id=comment.id, reaction_type="like")
        test_db.add(reaction)
        test_db.commit()

        # Toggle like
        response = authenticated_client.post(f"/api/comments/{comment.id}/react", json={"action": "like"})

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["likeCount"] == 0
        assert data["data"]["myReaction"] is None

    def test_change_like_to_dislike(self, authenticated_client: TestClient, test_db: Session, test_user: User, factory):
        """Test changing from like to dislike

        验证：
        - 返回 200 状态码
        - like_count 减少
        - dislike_count 增加
        - myReaction 为 dislike
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(
            user_id=user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="Test comment",
            like_count=1,
            dislike_count=0,
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        # Add existing like
        reaction = CommentReaction(user_id=test_user.id, comment_id=comment.id, reaction_type="like")
        test_db.add(reaction)
        test_db.commit()

        # Change to dislike
        response = authenticated_client.post(f"/api/comments/{comment.id}/react", json={"action": "dislike"})

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["likeCount"] == 0
        assert data["data"]["dislikeCount"] == 1
        assert data["data"]["myReaction"] == "dislike"

    def test_clear_reaction_success(self, authenticated_client: TestClient, test_db: Session, test_user: User, factory):
        """Test clearing reaction

        验证：
        - 返回 200 状态码
        - 反应被移除
        - myReaction 为 None
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(
            user_id=user.id, target_type="knowledge", target_id=kb.id, content="Test comment", like_count=1
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        # Add existing like
        reaction = CommentReaction(user_id=test_user.id, comment_id=comment.id, reaction_type="like")
        test_db.add(reaction)
        test_db.commit()

        # Clear reaction
        response = authenticated_client.post(f"/api/comments/{comment.id}/react", json={"action": "clear"})

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["likeCount"] == 0
        assert data["data"]["myReaction"] is None

    def test_react_invalid_action_fails(self, authenticated_client: TestClient, test_db: Session, factory):
        """Test that invalid action is rejected

        验证：
        - 返回 400 或 422 状态码
        - 返回错误消息
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(user_id=user.id, target_type="knowledge", target_id=kb.id, content="Test comment")
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = authenticated_client.post(f"/api/comments/{comment.id}/react", json={"action": "invalid"})

        assert_error_response(response, [400, 422], ["action", "操作"])

    def test_react_nonexistent_comment_fails(self, authenticated_client: TestClient, test_db: Session):
        """Test that reacting to nonexistent comment fails

        验证：
        - 返回 404 状态码
        - 返回错误消息
        """
        response = authenticated_client.post(f"/api/comments/{uuid.uuid4()}/react", json={"action": "like"})

        assert_error_response(response, [404], ["不存在"])

    def test_react_deleted_comment_fails(self, authenticated_client: TestClient, test_db: Session, factory):
        """Test that reacting to deleted comment fails

        验证：
        - 返回 404 状态码
        - 返回错误消息
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(
            user_id=user.id, target_type="knowledge", target_id=kb.id, content="Test comment", is_deleted=True
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = authenticated_client.post(f"/api/comments/{comment.id}/react", json={"action": "like"})

        assert_error_response(response, [404], ["不存在", "已删除"])


class TestDeleteComment:
    """Test DELETE /api/comments/{comment_id} endpoint"""

    def test_delete_own_comment_success(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test that user can delete their own comment

        验证：
        - 返回 200 状态码
        - 评论被软删除
        """
        kb = factory.create_knowledge_base()

        comment = Comment(user_id=test_user.id, target_type="knowledge", target_id=kb.id, content="My comment")
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = authenticated_client.delete(f"/api/comments/{comment.id}")

        assert response.status_code == 200

        # Verify soft delete
        test_db.refresh(comment)
        assert comment.is_deleted is True

    def test_delete_comment_cascades_to_children(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test that deleting parent comment also deletes child comments

        验证：
        - 返回 200 状态码
        - 父评论被删除
        - 子评论也被删除
        """
        kb = factory.create_knowledge_base()

        parent_comment = Comment(
            user_id=test_user.id, target_type="knowledge", target_id=kb.id, content="Parent comment"
        )
        test_db.add(parent_comment)
        test_db.commit()
        test_db.refresh(parent_comment)

        child_comment = Comment(
            user_id=test_user.id,
            target_type="knowledge",
            target_id=kb.id,
            parent_id=parent_comment.id,
            content="Child comment",
        )
        test_db.add(child_comment)
        test_db.commit()
        test_db.refresh(child_comment)

        response = authenticated_client.delete(f"/api/comments/{parent_comment.id}")

        assert response.status_code == 200

        # Verify both are deleted
        test_db.refresh(parent_comment)
        test_db.refresh(child_comment)
        assert parent_comment.is_deleted is True
        assert child_comment.is_deleted is True

    def test_content_owner_can_delete_comment(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test that content owner can delete comments on their content

        验证：
        - 返回 200 状态码
        - 评论被删除
        """
        # test_user is the knowledge base owner
        kb = factory.create_knowledge_base(uploader=test_user)
        other_user = factory.create_user()

        comment = Comment(
            user_id=other_user.id, target_type="knowledge", target_id=kb.id, content="Comment from other user"
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = authenticated_client.delete(f"/api/comments/{comment.id}")

        assert response.status_code == 200
        test_db.refresh(comment)
        assert comment.is_deleted is True

    def test_admin_can_delete_any_comment(self, admin_client: TestClient, test_db: Session, factory):
        """Test that admin can delete any comment

        验证：
        - 返回 200 状态码
        - 评论被删除
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(user_id=user.id, target_type="knowledge", target_id=kb.id, content="User comment")
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = admin_client.delete(f"/api/comments/{comment.id}")

        assert response.status_code == 200
        test_db.refresh(comment)
        assert comment.is_deleted is True

    def test_moderator_can_delete_any_comment(self, moderator_client: TestClient, test_db: Session, factory):
        """Test that moderator can delete any comment

        验证：
        - 返回 200 状态码
        - 评论被删除
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(user_id=user.id, target_type="knowledge", target_id=kb.id, content="User comment")
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = moderator_client.delete(f"/api/comments/{comment.id}")

        assert response.status_code == 200
        test_db.refresh(comment)
        assert comment.is_deleted is True

    def test_delete_others_comment_without_permission_fails(
        self, authenticated_client: TestClient, test_db: Session, factory
    ):
        """Test that user cannot delete others' comments without permission

        验证：
        - 返回 403 状态码
        - 返回权限错误消息
        """
        kb = factory.create_knowledge_base()
        other_user = factory.create_user()

        comment = Comment(
            user_id=other_user.id, target_type="knowledge", target_id=kb.id, content="Other user's comment"
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = authenticated_client.delete(f"/api/comments/{comment.id}")

        assert_error_response(response, [403], ["权限"])

    def test_delete_nonexistent_comment_fails(self, authenticated_client: TestClient, test_db: Session):
        """Test that deleting nonexistent comment fails

        验证：
        - 返回 404 状态码
        - 返回错误消息
        """
        response = authenticated_client.delete(f"/api/comments/{uuid.uuid4()}")

        assert_error_response(response, [404], ["不存在"])


class TestRestoreComment:
    """Test POST /api/comments/{comment_id}/restore endpoint"""

    def test_restore_own_comment_success(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test that user can restore their own deleted comment

        验证：
        - 返回 200 状态码
        - 评论被恢复
        """
        kb = factory.create_knowledge_base()

        comment = Comment(
            user_id=test_user.id, target_type="knowledge", target_id=kb.id, content="My comment", is_deleted=True
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = authenticated_client.post(f"/api/comments/{comment.id}/restore")

        assert response.status_code == 200

        # Verify restored
        test_db.refresh(comment)
        assert comment.is_deleted is False

    def test_restore_comment_restores_children(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test that restoring parent comment also restores child comments

        验证：
        - 返回 200 状态码
        - 父评论被恢复
        - 子评论也被恢复
        """
        kb = factory.create_knowledge_base()

        parent_comment = Comment(
            user_id=test_user.id, target_type="knowledge", target_id=kb.id, content="Parent comment", is_deleted=True
        )
        test_db.add(parent_comment)
        test_db.commit()
        test_db.refresh(parent_comment)

        child_comment = Comment(
            user_id=test_user.id,
            target_type="knowledge",
            target_id=kb.id,
            parent_id=parent_comment.id,
            content="Child comment",
            is_deleted=True,
        )
        test_db.add(child_comment)
        test_db.commit()
        test_db.refresh(child_comment)

        response = authenticated_client.post(f"/api/comments/{parent_comment.id}/restore")

        assert response.status_code == 200

        # Verify both are restored
        test_db.refresh(parent_comment)
        test_db.refresh(child_comment)
        assert parent_comment.is_deleted is False
        assert child_comment.is_deleted is False

    def test_content_owner_can_restore_comment(
        self, authenticated_client: TestClient, test_db: Session, test_user: User, factory
    ):
        """Test that content owner can restore comments on their content

        验证：
        - 返回 200 状态码
        - 评论被恢复
        """
        kb = factory.create_knowledge_base(uploader=test_user)
        other_user = factory.create_user()

        comment = Comment(
            user_id=other_user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="Comment from other user",
            is_deleted=True,
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = authenticated_client.post(f"/api/comments/{comment.id}/restore")

        assert response.status_code == 200
        test_db.refresh(comment)
        assert comment.is_deleted is False

    def test_admin_can_restore_any_comment(self, admin_client: TestClient, test_db: Session, factory):
        """Test that admin can restore any comment

        验证：
        - 返回 200 状态码
        - 评论被恢复
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(
            user_id=user.id, target_type="knowledge", target_id=kb.id, content="User comment", is_deleted=True
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = admin_client.post(f"/api/comments/{comment.id}/restore")

        assert response.status_code == 200
        test_db.refresh(comment)
        assert comment.is_deleted is False

    def test_moderator_can_restore_any_comment(self, moderator_client: TestClient, test_db: Session, factory):
        """Test that moderator can restore any comment

        验证：
        - 返回 200 状态码
        - 评论被恢复
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(
            user_id=user.id, target_type="knowledge", target_id=kb.id, content="User comment", is_deleted=True
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = moderator_client.post(f"/api/comments/{comment.id}/restore")

        assert response.status_code == 200
        test_db.refresh(comment)
        assert comment.is_deleted is False

    def test_restore_others_comment_without_permission_fails(
        self, authenticated_client: TestClient, test_db: Session, factory
    ):
        """Test that user cannot restore others' comments without permission

        验证：
        - 返回 403 状态码
        - 返回权限错误消息
        """
        kb = factory.create_knowledge_base()
        other_user = factory.create_user()

        comment = Comment(
            user_id=other_user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="Other user's comment",
            is_deleted=True,
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = authenticated_client.post(f"/api/comments/{comment.id}/restore")

        assert_error_response(response, [403], ["权限"])

    def test_restore_nonexistent_comment_fails(self, authenticated_client: TestClient, test_db: Session):
        """Test that restoring nonexistent comment fails

        验证：
        - 返回 404 状态码
        - 返回错误消息
        """
        response = authenticated_client.post(f"/api/comments/{uuid.uuid4()}/restore")

        assert_error_response(response, [404], ["不存在"])


class TestCommentAuthentication:
    """Test authentication requirements for comment endpoints"""

    def test_get_comments_requires_authentication(self, client: TestClient, test_db: Session, factory):
        """Test that getting comments requires authentication

        验证：
        - 返回 401 状态码
        """
        kb = factory.create_knowledge_base()

        response = client.get(f"/api/comments?target_type=knowledge&target_id={kb.id}")

        assert response.status_code == 401

    def test_create_comment_requires_authentication(self, client: TestClient, test_db: Session, factory):
        """Test that creating comment requires authentication

        验证：
        - 返回 401 状态码
        """
        kb = factory.create_knowledge_base()

        response = client.post(
            "/api/comments", json={"content": "Test comment", "target_type": "knowledge", "target_id": kb.id}
        )

        assert response.status_code == 401

    def test_react_comment_requires_authentication(self, client: TestClient, test_db: Session, factory):
        """Test that reacting to comment requires authentication

        验证：
        - 返回 401 状态码
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(user_id=user.id, target_type="knowledge", target_id=kb.id, content="Test comment")
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = client.post(f"/api/comments/{comment.id}/react", json={"action": "like"})

        assert response.status_code == 401

    def test_delete_comment_requires_authentication(self, client: TestClient, test_db: Session, factory):
        """Test that deleting comment requires authentication

        验证：
        - 返回 401 状态码
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(user_id=user.id, target_type="knowledge", target_id=kb.id, content="Test comment")
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = client.delete(f"/api/comments/{comment.id}")

        assert response.status_code == 401

    def test_restore_comment_requires_authentication(self, client: TestClient, test_db: Session, factory):
        """Test that restoring comment requires authentication

        验证：
        - 返回 401 状态码
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()

        comment = Comment(
            user_id=user.id, target_type="knowledge", target_id=kb.id, content="Test comment", is_deleted=True
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)

        response = client.post(f"/api/comments/{comment.id}/restore")

        assert response.status_code == 401
