from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Body

from database_models import sqlite_db_manager as db_manager  # type: ignore[attr-defined]
from database_models import Comment, CommentReaction, KnowledgeBase, PersonaCard, User  # type: ignore[attr-defined]
from api_routes.response_util import Success
from error_handlers import APIError, ValidationError, AuthorizationError, NotFoundError
from user_management import get_current_user
from logging_config import app_logger, log_exception
from websocket_manager import message_ws_manager


comment_router = APIRouter()


@comment_router.get(
    "/comments",
)
async def get_comments(
        target_type: str = Query(..., description="目标类型: knowledge/persona"),
        target_id: str = Query(..., description="目标ID"),
        current_user: dict = Depends(get_current_user)
):
    """获取评论列表（包含一级与二级评论）"""
    if target_type not in ["knowledge", "persona"]:
        raise ValidationError("目标类型必须是 knowledge 或 persona")

    try:
        app_logger.info(
            f"Get comments: target_type={target_type}, target_id={target_id}, user_id={current_user.get('id')}")

        with db_manager.get_session() as session:
            query = session.query(Comment).filter(
                Comment.target_type == target_type,
                Comment.target_id == target_id,
                Comment.is_deleted == False
            ).order_by(Comment.created_at.asc())

            comments = query.all()

            user_ids = list({c.user_id for c in comments})
            users = {}
            if user_ids:
                user_list = session.query(User).filter(User.id.in_(user_ids)).all()
                for u in user_list:
                    users[u.id] = u

            current_user_id = str(current_user.get("id")) if current_user.get("id") else None
            reactions_map = {}
            if current_user_id and comments:
                comment_ids = [c.id for c in comments]
                reaction_rows = session.query(CommentReaction).filter(
                    CommentReaction.comment_id.in_(comment_ids),
                    CommentReaction.user_id == current_user_id,
                ).all()
                for r in reaction_rows:
                    reactions_map[r.comment_id] = r.reaction_type

            result: List[dict] = []
            for c in comments:
                user = users.get(c.user_id)
                result.append({
                    "id": c.id,
                    "userId": c.user_id,
                    "username": user.username if user else "",
                    "avatarUpdatedAt": user.avatar_updated_at.isoformat() if user and user.avatar_updated_at else None,
                    "parentId": c.parent_id,
                    "content": c.content,
                    "createdAt": c.created_at.isoformat() if c.created_at else None,
                    "likeCount": c.like_count or 0,
                    "dislikeCount": c.dislike_count or 0,
                    "myReaction": reactions_map.get(c.id)
                })

            return Success(
                message="获取评论成功",
                data=result
            )
    except Exception as e:
        log_exception(app_logger, "Get comments error", exception=e)
        raise APIError("获取评论失败")


@comment_router.post(
    "/comments",
)
async def create_comment(
        data: dict = Body(...),
        current_user: dict = Depends(get_current_user)
):
    """创建评论或回复（受禁言限制）"""
    content = (data.get("content") or "").strip()
    target_type = data.get("target_type")
    target_id = data.get("target_id")
    parent_id = data.get("parent_id")

    if not content:
        raise ValidationError("评论内容不能为空")
    if len(content) > 500:
        raise ValidationError("评论内容不能超过500字")
    if target_type not in ["knowledge", "persona"]:
        raise ValidationError("目标类型必须是 knowledge 或 persona")
    if not target_id:
        raise ValidationError("目标ID不能为空")

    try:
        sender_id = current_user.get("id")
        if not sender_id:
            raise AuthorizationError("用户未登录")

        with db_manager.get_session() as session:
            user = session.query(User).filter(User.id == sender_id).first()
            if not user:
                raise NotFoundError("用户不存在")

            now = datetime.now()
            if user.is_muted:
                if user.muted_until and user.muted_until > now:
                    raise AuthorizationError("当前用户已被禁言，无法发表评论")
                if user.muted_until is None:
                    raise AuthorizationError("当前用户已被永久禁言，无法发表评论")

            if target_type == "knowledge":
                target = session.query(KnowledgeBase).filter(KnowledgeBase.id == target_id).first()
            else:
                target = session.query(PersonaCard).filter(PersonaCard.id == target_id).first()

            if not target:
                raise NotFoundError("目标内容不存在")

            parent = None
            if parent_id:
                parent = session.query(Comment).filter(
                    Comment.id == parent_id,
                    Comment.target_type == target_type,
                    Comment.target_id == target_id
                ).first()
                if not parent:
                    raise ValidationError("父级评论不存在")

            comment = Comment(
                user_id=user.id,
                target_type=target_type,
                target_id=target_id,
                parent_id=parent.id if parent else None,
                content=content,
            )
            session.add(comment)
            session.commit()
            session.refresh(comment)

            recipients = set()

            if parent and parent.user_id and parent.user_id != user.id:
                recipients.add(str(parent.user_id))

            owner_id = None
            if target_type == "knowledge":
                owner_id = getattr(target, "uploader_id", None)
            else:
                owner_id = getattr(target, "uploader_id", None)
            if owner_id and owner_id != user.id:
                recipients.add(str(owner_id))

            snippet = content[:80]
            if parent:
                title = "你收到了新的评论回复"
                body = f"{user.username} 回复了你的评论：{snippet}"
            else:
                title = "你收到了新的评论"
                body = f"{user.username} 评论了你的内容：{snippet}"

            for rid in recipients:
                try:
                    db_manager.create_message(
                        sender_id=str(user.id),
                        recipient_id=str(rid),
                        title=title,
                        content=body,
                        message_type="comment",
                        summary=snippet,
                    )
                except Exception:
                    continue

            if recipients:
                await message_ws_manager.broadcast_user_update(recipients)

            return Success(
                message="发表评论成功",
                data={
                    "id": comment.id,
                    "userId": user.id,
                    "username": user.username,
                    "avatarUpdatedAt": user.avatar_updated_at.isoformat() if user.avatar_updated_at else None,
                    "parentId": comment.parent_id,
                    "content": comment.content,
                    "createdAt": comment.created_at.isoformat() if comment.created_at else None,
                    "likeCount": comment.like_count or 0,
                    "dislikeCount": comment.dislike_count or 0,
                    "myReaction": None,
                }
            )
    except (ValidationError, AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        log_exception(app_logger, "Create comment error", exception=e)
        raise APIError("发表评论失败")


@comment_router.post(
    "/comments/{comment_id}/react",
)
async def react_comment(
        comment_id: str,
        data: dict = Body(...),
        current_user: dict = Depends(get_current_user)
):
    """对评论进行点赞或踩，支持撤销"""
    action = (data.get("action") or "").strip().lower()
    if action not in ["like", "dislike", "clear"]:
        raise ValidationError("action 必须是 like、dislike 或 clear")

    user_id = current_user.get("id")
    if not user_id:
        raise AuthorizationError("用户未登录")

    try:
        with db_manager.get_session() as session:
            comment = session.query(Comment).filter(
                Comment.id == comment_id,
                Comment.is_deleted == False
            ).first()
            if not comment:
                raise NotFoundError("评论不存在或已删除")

            reaction = session.query(CommentReaction).filter(
                CommentReaction.comment_id == comment_id,
                CommentReaction.user_id == user_id
            ).first()

            before_type: Optional[str] = reaction.reaction_type if reaction else None
            after_type: Optional[str] = None

            if action == "clear":
                if reaction:
                    if reaction.reaction_type == "like":
                        comment.like_count = max((comment.like_count or 0) - 1, 0)
                    elif reaction.reaction_type == "dislike":
                        comment.dislike_count = max((comment.dislike_count or 0) - 1, 0)
                    session.delete(reaction)
            elif action == "like":
                if reaction and reaction.reaction_type == "like":
                    comment.like_count = max((comment.like_count or 0) - 1, 0)
                    session.delete(reaction)
                else:
                    if reaction and reaction.reaction_type == "dislike":
                        comment.dislike_count = max((comment.dislike_count or 0) - 1, 0)
                        reaction.reaction_type = "like"
                    else:
                        reaction = CommentReaction(
                            user_id=user_id,
                            comment_id=comment_id,
                            reaction_type="like"
                        )
                        session.add(reaction)
                    comment.like_count = (comment.like_count or 0) + 1
                    after_type = "like"
            elif action == "dislike":
                if reaction and reaction.reaction_type == "dislike":
                    comment.dislike_count = max((comment.dislike_count or 0) - 1, 0)
                    session.delete(reaction)
                else:
                    if reaction and reaction.reaction_type == "like":
                        comment.like_count = max((comment.like_count or 0) - 1, 0)
                        reaction.reaction_type = "dislike"
                    else:
                        reaction = CommentReaction(
                            user_id=user_id,
                            comment_id=comment_id,
                            reaction_type="dislike"
                        )
                        session.add(reaction)
                    comment.dislike_count = (comment.dislike_count or 0) + 1
                    after_type = "dislike"

            session.commit()
            session.refresh(comment)

            my_reaction: Optional[str]
            if action == "clear":
                my_reaction = None
            else:
                my_reaction = after_type
                if action in ["like", "dislike"] and after_type is None:
                    my_reaction = None

            should_notify = (
                after_type in ["like", "dislike"]
                and after_type != before_type
                and str(user_id) != str(comment.user_id)
            )

            recipient_id = str(comment.user_id)
            snippet = (comment.content or "")[:80]
            sender_name = current_user.get("username", "")

            if should_notify and recipient_id:
                title = "你的评论收到新的点赞" if after_type == "like" else "你的评论收到新的踩"
                body = f"{sender_name} 对你的评论进行了{'点赞' if after_type == 'like' else '踩'}：{snippet}"
                try:
                    db_manager.create_message(
                        sender_id=str(user_id),
                        recipient_id=recipient_id,
                        title=title,
                        content=body,
                        message_type="reaction",
                        summary=snippet,
                    )
                    await message_ws_manager.broadcast_user_update({recipient_id})
                except Exception:
                    pass

            return Success(
                message="操作成功",
                data={
                    "id": comment.id,
                    "likeCount": comment.like_count or 0,
                    "dislikeCount": comment.dislike_count or 0,
                    "myReaction": my_reaction,
                }
            )
    except (ValidationError, AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        log_exception(app_logger, "React comment error", exception=e)
        raise APIError("操作失败")


@comment_router.delete(
    "/comments/{comment_id}",
)
async def delete_comment(
        comment_id: str,
        current_user: dict = Depends(get_current_user)
):
    """删除评论（软删除，支持级联删除二级评论）"""
    try:
        with db_manager.get_session() as session:
            comment = session.query(Comment).filter(Comment.id == comment_id).first()
            if not comment:
                raise NotFoundError("评论不存在")

            user_id = current_user.get("id")
            user_role = current_user.get("role", "user")
            is_admin = current_user.get("is_admin", False)

            can_delete = False
            if comment.user_id == user_id:
                can_delete = True

            if not can_delete:
                if comment.target_type == "knowledge":
                    target = session.query(KnowledgeBase).filter(
                        KnowledgeBase.id == comment.target_id
                    ).first()
                else:
                    target = session.query(PersonaCard).filter(
                        PersonaCard.id == comment.target_id
                    ).first()
                if target and str(getattr(target, "uploader_id", "")) == str(user_id):
                    can_delete = True

            if not can_delete and (is_admin or user_role in ["admin", "moderator"]):
                can_delete = True

            if not can_delete:
                raise AuthorizationError("没有权限删除此评论")

            comment.is_deleted = True

            if comment.parent_id is None:
                children = session.query(Comment).filter(
                    Comment.parent_id == comment.id
                ).all()
                for child in children:
                    child.is_deleted = True

            session.commit()

            return Success(
                message="删除评论成功",
                data={"id": comment.id}
            )
    except (AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete comment error", exception=e)
        raise APIError("删除评论失败")


@comment_router.post(
    "/comments/{comment_id}/restore",
)
async def restore_comment(
        comment_id: str,
        current_user: dict = Depends(get_current_user)
):
    """撤销删除评论（恢复软删除的评论以及其子评论）"""
    try:
        with db_manager.get_session() as session:
            comment = session.query(Comment).filter(Comment.id == comment_id).first()
            if not comment:
                raise NotFoundError("评论不存在")

            user_id = current_user.get("id")
            user_role = current_user.get("role", "user")
            is_admin = current_user.get("is_admin", False)

            can_restore = False
            if comment.user_id == user_id:
                can_restore = True

            if not can_restore:
                if comment.target_type == "knowledge":
                    target = session.query(KnowledgeBase).filter(
                        KnowledgeBase.id == comment.target_id
                    ).first()
                else:
                    target = session.query(PersonaCard).filter(
                        PersonaCard.id == comment.target_id
                    ).first()
                if target and str(getattr(target, "uploader_id", "")) == str(user_id):
                    can_restore = True

            if not can_restore and (is_admin or user_role in ["admin", "moderator"]):
                can_restore = True

            if not can_restore:
                raise AuthorizationError("没有权限撤销此评论删除")

            comment.is_deleted = False

            if comment.parent_id is None:
                children = session.query(Comment).filter(
                    Comment.parent_id == comment.id
                ).all()
                for child in children:
                    child.is_deleted = False

            session.commit()

            return Success(
                message="撤销删除评论成功",
                data={"id": comment.id}
            )
    except (AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        log_exception(app_logger, "Restore comment error", exception=e)
        raise APIError("撤销删除评论失败")
