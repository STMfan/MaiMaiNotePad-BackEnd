"""
评论路由错误路径测试
测试评论API的所有错误处理路径，包括不存在错误、权限验证失败、创建失败和删除失败

Requirements: 5.6 (comments.py error paths)
"""

import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from app.models.database import Comment, User, KnowledgeBase, PersonaCard
from tests.conftest import assert_error_response


class TestCommentNotFoundErrors:
    """测试评论不存在错误（96-98行）- Task 5.6.1"""
    
    def test_react_nonexistent_comment(self, client, test_user, test_db):
        """测试对不存在的评论进行反应
        
        验证：
        - 返回 404 状态码
        - 返回"评论不存在"错误消息
        - 覆盖 comments.py 第96-98行
        """
        # Login to get token
        test_db.commit()
        test_db.refresh(test_user)
        
        login_response = client.post(
            "/api/auth/token",
            data={"username": test_user.username, "password": "testpassword123"}
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        token = token_data.get("data", {}).get("access_token") or token_data.get("access_token")
        
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/comments/{fake_id}/react",
            json={"action": "like"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert_error_response(response, [404], ["评论不存在", "not found"])
    
    def test_react_deleted_comment(self, client, test_user, test_db, factory):
        """测试对已删除的评论进行反应
        
        验证：
        - 返回 404 状态码
        - 返回"评论不存在或已删除"错误消息
        """
        # Login to get token
        test_db.commit()
        test_db.refresh(test_user)
        
        login_response = client.post(
            "/api/auth/token",
            data={"username": test_user.username, "password": "testpassword123"}
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        token = token_data.get("data", {}).get("access_token") or token_data.get("access_token")
        
        kb = factory.create_knowledge_base()
        user = factory.create_user()
        
        comment = Comment(
            user_id=user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="Deleted comment",
            is_deleted=True
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)
        
        response = client.post(
            f"/api/comments/{comment.id}/react",
            json={"action": "like"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert_error_response(response, [404], ["不存在", "已删除", "deleted"])
    
    def test_delete_nonexistent_comment(self, client, test_user, test_db):
        """测试删除不存在的评论
        
        验证：
        - 返回 404 状态码
        - 返回"评论不存在"错误消息
        """
        # Login to get token
        test_db.commit()
        test_db.refresh(test_user)
        
        login_response = client.post(
            "/api/auth/token",
            data={"username": test_user.username, "password": "testpassword123"}
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        token = token_data.get("data", {}).get("access_token") or token_data.get("access_token")
        
        fake_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/comments/{fake_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert_error_response(response, [404], ["评论不存在", "not found"])
    
    def test_restore_nonexistent_comment(self, client, test_user, test_db):
        """测试恢复不存在的评论
        
        验证：
        - 返回 404 状态码
        - 返回"评论不存在"错误消息
        """
        # Login to get token
        test_db.commit()
        test_db.refresh(test_user)
        
        login_response = client.post(
            "/api/auth/token",
            data={"username": test_user.username, "password": "testpassword123"}
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        token = token_data.get("data", {}).get("access_token") or token_data.get("access_token")
        
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/comments/{fake_id}/restore",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert_error_response(response, [404], ["评论不存在", "not found"])


class TestCommentPermissionErrors:
    """测试权限验证失败（122, 127行）- Task 5.6.2"""
    
    def test_delete_others_comment_without_permission(self, authenticated_client, test_db, test_user, factory):
        """测试删除他人评论被拒绝
        
        验证：
        - 返回 403 状态码
        - 返回权限错误消息
        - 覆盖 comments.py 第122行
        """
        # Create a knowledge base owned by someone else
        kb_owner = factory.create_user()
        kb = factory.create_knowledge_base(uploader=kb_owner)
        
        # Create another user who wrote the comment
        other_user = factory.create_user()
        
        comment = Comment(
            user_id=other_user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="Other user's comment"
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)
        
        # test_user (authenticated) tries to delete other_user's comment
        # test_user is not the comment owner, not the content owner, and not an admin
        response = authenticated_client.delete(f"/api/comments/{comment.id}")
        
        assert_error_response(response, [403], ["权限", "permission"])
    
    def test_restore_others_comment_without_permission(self, authenticated_client, test_db, test_user, factory):
        """测试恢复他人评论被拒绝
        
        验证：
        - 返回 403 状态码
        - 返回权限错误消息
        - 覆盖 comments.py 第127行
        """
        # Create a knowledge base owned by someone else
        kb_owner = factory.create_user()
        kb = factory.create_knowledge_base(uploader=kb_owner)
        
        # Create another user who wrote the comment
        other_user = factory.create_user()
        
        comment = Comment(
            user_id=other_user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="Other user's comment",
            is_deleted=True
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)
        
        # test_user (authenticated) tries to restore other_user's comment
        # test_user is not the comment owner, not the content owner, and not an admin
        response = authenticated_client.post(f"/api/comments/{comment.id}/restore")
        
        assert_error_response(response, [403], ["权限", "permission"])
    
    def test_content_owner_can_delete_comment(self, authenticated_client, test_user, test_db, factory):
        """测试内容所有者可以删除评论
        
        验证：
        - 返回 200 状态码
        - 评论被删除
        """
        # Ensure test_user is committed and refreshed
        test_db.commit()
        test_db.refresh(test_user)
        
        # test_user is the knowledge base owner
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            content="Test content",
            uploader_id=test_user.id,
            is_pending=False,
            is_public=True
        )
        test_db.add(kb)
        test_db.commit()
        test_db.refresh(kb)
        
        other_user = factory.create_user()
        
        comment = Comment(
            user_id=other_user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="Comment from other user"
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)
        comment_id = comment.id
        
        response = authenticated_client.delete(f"/api/comments/{comment_id}")
        
        assert response.status_code == 200
        
        # Expire all objects and query again to get fresh data from database
        test_db.expire_all()
        
        # Query the comment again to check if it's deleted
        updated_comment = test_db.query(Comment).filter(Comment.id == comment_id).first()
        assert updated_comment is not None
        assert updated_comment.is_deleted is True
    
    def test_content_owner_can_restore_comment(self, authenticated_client, test_user, test_db, factory):
        """测试内容所有者可以恢复评论
        
        验证：
        - 返回 200 状态码
        - 评论被恢复
        """
        # Ensure test_user is committed and refreshed
        test_db.commit()
        test_db.refresh(test_user)
        
        # test_user is the knowledge base owner
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name="Test KB",
            description="Test description",
            content="Test content",
            uploader_id=test_user.id,
            is_pending=False,
            is_public=True
        )
        test_db.add(kb)
        test_db.commit()
        test_db.refresh(kb)
        
        other_user = factory.create_user()
        
        comment = Comment(
            user_id=other_user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="Comment from other user",
            is_deleted=True
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)
        comment_id = comment.id
        
        response = authenticated_client.post(f"/api/comments/{comment_id}/restore")
        
        assert response.status_code == 200
        
        # Expire all objects and query again to get fresh data from database
        test_db.expire_all()
        
        # Query the comment again to check if it's restored
        updated_comment = test_db.query(Comment).filter(Comment.id == comment_id).first()
        assert updated_comment is not None
        assert updated_comment.is_deleted is False


class TestCommentCreationErrors:
    """测试创建失败错误 - Task 5.6.3"""
    
    def test_create_comment_empty_content(self, authenticated_client, test_db, factory):
        """测试创建空内容评论
        
        验证：
        - 返回 400 或 422 状态码
        - 返回"评论内容不能为空"错误消息
        """
        kb = factory.create_knowledge_base()
        
        response = authenticated_client.post(
            "/api/comments",
            json={
                "content": "   ",
                "target_type": "knowledge",
                "target_id": kb.id
            }
        )
        
        assert_error_response(response, [400, 422], ["内容", "不能为空", "empty"])
    
    def test_create_comment_too_long(self, authenticated_client, test_db, factory):
        """测试创建超长评论
        
        验证：
        - 返回 400 或 422 状态码
        - 返回"评论内容不能超过500字"错误消息
        """
        kb = factory.create_knowledge_base()
        
        response = authenticated_client.post(
            "/api/comments",
            json={
                "content": "a" * 501,
                "target_type": "knowledge",
                "target_id": kb.id
            }
        )
        
        assert_error_response(response, [400, 422], ["500"])
    
    def test_create_comment_invalid_target_type(self, authenticated_client, test_db):
        """测试使用无效目标类型创建评论
        
        验证：
        - 返回 400 或 422 状态码
        - 返回"目标类型必须是 knowledge 或 persona"错误消息
        """
        response = authenticated_client.post(
            "/api/comments",
            json={
                "content": "Test comment",
                "target_type": "invalid",
                "target_id": str(uuid.uuid4())
            }
        )
        
        assert_error_response(response, [400, 422], ["目标类型", "knowledge", "persona"])
    
    def test_create_comment_nonexistent_target(self, authenticated_client, test_db):
        """测试对不存在的目标创建评论
        
        验证：
        - 返回 404 状态码
        - 返回"目标内容不存在"错误消息
        """
        response = authenticated_client.post(
            "/api/comments",
            json={
                "content": "Test comment",
                "target_type": "knowledge",
                "target_id": str(uuid.uuid4())
            }
        )
        
        assert_error_response(response, [404], ["目标", "不存在", "not found"])
    
    def test_create_comment_nonexistent_parent(self, authenticated_client, test_db, factory):
        """测试回复不存在的父评论
        
        验证：
        - 返回 400 或 422 状态码
        - 返回"父级评论不存在"错误消息
        """
        kb = factory.create_knowledge_base()
        
        response = authenticated_client.post(
            "/api/comments",
            json={
                "content": "Reply",
                "target_type": "knowledge",
                "target_id": kb.id,
                "parent_id": str(uuid.uuid4())
            }
        )
        
        assert_error_response(response, [400, 422], ["父级评论", "不存在", "parent"])
    
    def test_create_comment_when_muted_temporarily(self, authenticated_client, test_db, test_user, factory):
        """测试被临时禁言用户创建评论
        
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
            "/api/comments",
            json={
                "content": "Test comment",
                "target_type": "knowledge",
                "target_id": kb.id
            }
        )
        
        assert_error_response(response, [403], ["禁言", "muted"])
        
        # Cleanup
        test_user.is_muted = False
        test_user.muted_until = None
        test_db.commit()
    
    def test_create_comment_when_permanently_muted(self, authenticated_client, test_db, test_user, factory):
        """测试被永久禁言用户创建评论
        
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
            "/api/comments",
            json={
                "content": "Test comment",
                "target_type": "knowledge",
                "target_id": kb.id
            }
        )
        
        assert_error_response(response, [403], ["永久禁言", "permanent"])
        
        # Cleanup
        test_user.is_muted = False
        test_db.commit()
    
    def test_create_comment_missing_target_id(self, authenticated_client):
        """测试创建评论时缺少目标ID
        
        验证：
        - 返回 400 或 422 状态码
        - 返回验证错误消息
        """
        response = authenticated_client.post(
            "/api/comments",
            json={
                "content": "Test comment",
                "target_type": "knowledge"
            }
        )
        
        assert_error_response(response, [400, 422], ["target_id", "目标ID", "required", "目标不存在", "参数缺失"])
    
    def test_create_comment_database_error(self, authenticated_client, test_db, factory):
        """测试创建评论时数据库错误
        
        验证：
        - 返回 400 状态码 (APIError默认状态码)
        - 返回"发表评论失败"错误消息
        - 覆盖 comments.py 第233-235行的通用异常处理
        """
        kb = factory.create_knowledge_base()
        
        # Mock Session.add to raise an exception
        from sqlalchemy.orm import Session
        with patch.object(Session, 'add', side_effect=Exception("Database error")):
            response = authenticated_client.post(
                "/api/comments",
                json={
                    "content": "Test comment",
                    "target_type": "knowledge",
                    "target_id": kb.id
                }
            )
            
            assert_error_response(response, [400], ["发表评论失败", "failed"])


class TestCommentDeletionErrors:
    """测试删除失败错误 - Task 5.6.4"""
    
    def test_delete_comment_database_error(self, authenticated_client, test_user, test_db, factory):
        """测试删除评论数据库错误
        
        验证：
        - 返回 400 状态码 (APIError默认状态码)
        - 返回"删除评论失败"错误消息
        - 触发异常处理路径（lines 426-428）
        """
        kb = factory.create_knowledge_base()
        
        comment = Comment(
            user_id=test_user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="My comment"
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)
        
        # Mock Session.commit to raise exception
        from sqlalchemy.orm import Session
        with patch.object(Session, 'commit', side_effect=Exception("Database error")):
            response = authenticated_client.delete(f"/api/comments/{comment.id}")
            
            # Should return 400 error with failure message
            assert response.status_code == 400
            data = response.json()
            assert "删除评论失败" in str(data) or "error" in str(data).lower()
    
    def test_delete_comment_attribute_error(self, authenticated_client, test_user, test_db, factory):
        """测试删除评论时属性访问错误
        
        验证：
        - 返回 400 状态码 (APIError默认状态码)
        - 返回"删除评论失败"错误消息
        - 触发异常处理路径
        """
        kb = factory.create_knowledge_base()
        
        comment = Comment(
            user_id=test_user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="My comment"
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)
        
        # Mock Comment.is_deleted property to raise exception
        with patch.object(Comment, 'is_deleted', new_callable=lambda: property(
            fget=lambda self: None,
            fset=lambda self, value: (_ for _ in ()).throw(Exception("Attribute error"))
        )):
            response = authenticated_client.delete(f"/api/comments/{comment.id}")
            
            # Should return 400 error
            assert response.status_code == 400
            data = response.json()
            assert "删除评论失败" in str(data) or "error" in str(data).lower()


class TestCommentReactionErrors:
    """测试评论反应错误"""
    
    def test_react_invalid_action(self, authenticated_client, test_db, factory):
        """测试使用无效操作进行反应
        
        验证：
        - 返回 400 或 422 状态码
        - 返回"action 必须是 like、dislike 或 clear"错误消息
        """
        kb = factory.create_knowledge_base()
        user = factory.create_user()
        
        comment = Comment(
            user_id=user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="Test comment"
        )
        test_db.add(comment)
        test_db.commit()
        test_db.refresh(comment)
        
        response = authenticated_client.post(
            f"/api/comments/{comment.id}/react",
            json={"action": "invalid"}
        )
        
        assert_error_response(response, [400, 422], ["action", "操作", "like", "dislike", "clear"])


class TestCommentValidationErrors:
    """测试评论验证错误"""
    
    def test_get_comments_invalid_target_type(self, authenticated_client, test_db):
        """测试使用无效目标类型获取评论
        
        验证：
        - 返回 400 或 422 状态码
        - 返回"目标类型必须是 knowledge 或 persona"错误消息
        """
        response = authenticated_client.get(
            "/api/comments?target_type=invalid&target_id=123"
        )
        
        assert_error_response(response, [400, 422], ["目标类型", "knowledge", "persona"])
    
    def test_get_comments_missing_target_id(self, authenticated_client):
        """测试获取评论时缺少目标ID
        
        验证：
        - 返回 400 或 422 状态码
        - 返回验证错误消息
        """
        response = authenticated_client.get(
            "/api/comments?target_type=knowledge"
        )
        
        assert_error_response(response, [400, 422], ["target_id", "required"])
    
    def test_get_comments_missing_target_type(self, authenticated_client):
        """测试获取评论时缺少目标类型
        
        验证：
        - 返回 400 或 422 状态码
        - 返回验证错误消息
        """
        response = authenticated_client.get(
            f"/api/comments?target_id={uuid.uuid4()}"
        )
        
        assert_error_response(response, [400, 422], ["target_type", "required"])


class TestCommentCascadeDeletion:
    """测试评论级联删除"""
    
    def test_delete_parent_comment_cascades_to_children(self, authenticated_client, test_user, test_db, factory):
        """测试删除父评论级联删除子评论
        
        验证：
        - 返回 200 状态码
        - 父评论被删除
        - 子评论也被删除
        """
        kb = factory.create_knowledge_base()
        
        parent_comment = Comment(
            user_id=test_user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="Parent comment"
        )
        test_db.add(parent_comment)
        test_db.commit()
        test_db.refresh(parent_comment)
        
        child_comment = Comment(
            user_id=test_user.id,
            target_type="knowledge",
            target_id=kb.id,
            parent_id=parent_comment.id,
            content="Child comment"
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
    
    def test_restore_parent_comment_restores_children(self, authenticated_client, test_user, test_db, factory):
        """测试恢复父评论恢复子评论
        
        验证：
        - 返回 200 状态码
        - 父评论被恢复
        - 子评论也被恢复
        """
        kb = factory.create_knowledge_base()
        
        parent_comment = Comment(
            user_id=test_user.id,
            target_type="knowledge",
            target_id=kb.id,
            content="Parent comment",
            is_deleted=True
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
            is_deleted=True
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
