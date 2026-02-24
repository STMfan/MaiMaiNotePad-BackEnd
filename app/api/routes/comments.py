"""
评论路由模块

处理评论相关的API端点，包括：
- 获取评论列表
- 创建评论
- 点赞/取消点赞评论
- 删除评论
- 恢复评论
"""

from datetime import datetime
from typing import Optional, List, Any, Union

from fastapi import APIRouter, Depends, Query, Body

from app.models.database import Comment, CommentReaction, KnowledgeBase, PersonaCard, User
from app.api.response_util import Success
from app.core.error_handlers import APIError, ValidationError, AuthorizationError, NotFoundError
from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.logging import app_logger, log_exception
from app.utils.websocket import message_ws_manager
from sqlalchemy.orm import Session
from app.core.cache.invalidation import invalidate_comment_cache


router = APIRouter()


# 评论相关路由（获取、创建、点赞、删除等）


@router.get(
    "/comments",
)
async def get_comments(
    target_type: str = Query(..., description="目标类型: knowledge/persona"),
    target_id: str = Query(..., description="目标ID"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取评论列表（包含一级与二级评论）"""
    if target_type not in ["knowledge", "persona"]:
        raise ValidationError("目标类型必须是 knowledge 或 persona")

    try:
        app_logger.info(
            f"Get comments: target_type={target_type}, target_id={target_id}, user_id={current_user.get('id')}"
        )

        query = (
            db.query(Comment)
            .filter(Comment.target_type == target_type, Comment.target_id == target_id, Comment.is_deleted.is_(False))
            .order_by(Comment.created_at.asc())
        )

        comments = query.all()

        user_ids = list({c.user_id for c in comments})
        users = {}
        if user_ids:
            user_list = db.query(User).filter(User.id.in_(user_ids)).all()
            for u in user_list:
                users[u.id] = u

        current_user_id = str(current_user.get("id")) if current_user.get("id") else None
        reactions_map = {}
        if current_user_id and comments:
            comment_ids = [c.id for c in comments]
            reaction_rows = (
                db.query(CommentReaction)
                .filter(
                    CommentReaction.comment_id.in_(comment_ids),
                    CommentReaction.user_id == current_user_id,
                )
                .all()
            )
            for r in reaction_rows:
                reactions_map[r.comment_id] = r.reaction_type

        result: List[dict] = []
        for c in comments:
            user = users.get(c.user_id)
            result.append(
                {
                    "id": c.id,
                    "userId": c.user_id,
                    "username": user.username if user else "",
                    "avatarUpdatedAt": user.avatar_updated_at.isoformat() if user and user.avatar_updated_at else None,
                    "parentId": c.parent_id,
                    "content": c.content,
                    "createdAt": c.created_at.isoformat() if c.created_at else None,
                    "likeCount": c.like_count or 0,
                    "dislikeCount": c.dislike_count or 0,
                    "myReaction": reactions_map.get(c.id),
                }
            )

        return Success(message="获取评论成功", data=result)
    except Exception as e:
        log_exception(app_logger, "Get comments error", exception=e)
        raise APIError("获取评论失败")


def _validate_comment_input(content: str, target_type: str, target_id: Any) -> str:
    """验证评论输入参数

    Args:
        content: 评论内容
        target_type: 目标类型
        target_id: 目标ID

    Returns:
        清理后的评论内容

    Raises:
        ValidationError: 参数验证失败
    """
    content = (content or "").strip()

    if not content:
        raise ValidationError("评论内容不能为空")
    if len(content) > 500:
        raise ValidationError("评论内容不能超过500字")
    if target_type not in ["knowledge", "persona"]:
        raise ValidationError("目标类型必须是 knowledge 或 persona")
    if not target_id:
        raise ValidationError("目标ID不能为空")

    return content


def _check_user_mute_status(user: User) -> None:
    """检查用户禁言状态

    Args:
        user: 用户对象

    Raises:
        AuthorizationError: 用户处于禁言状态
    """
    if not user.is_muted:
        return

    now = datetime.now()
    reason = getattr(user, "mute_reason", "") or "违反社区行为规范"

    if user.muted_until and user.muted_until > now:
        raise AuthorizationError(
            f"你当前处于禁言状态，暂时无法发表评论。\n\n禁言原因：{reason}\n\n如有疑问，可以联系管理员。\n\n—— 麦麦"
        )

    if user.muted_until is None:
        raise AuthorizationError(
            f"你当前处于永久禁言状态，无法发表评论。\n\n禁言原因：{reason}\n\n如有疑问，可以联系管理员。\n\n—— 麦麦"
        )


def _get_comment_target(db: Session, target_type: str, target_id: Any) -> Union[KnowledgeBase, PersonaCard]:
    """获取评论目标对象

    Args:
        db: 数据库会话
        target_type: 目标类型
        target_id: 目标ID

    Returns:
        目标对象（KnowledgeBase 或 PersonaCard）

    Raises:
        NotFoundError: 目标不存在
    """
    target: Optional[Union[KnowledgeBase, PersonaCard]]
    if target_type == "knowledge":
        target = db.query(KnowledgeBase).filter(KnowledgeBase.id == target_id).first()
    else:
        target = db.query(PersonaCard).filter(PersonaCard.id == target_id).first()

    if not target:
        raise NotFoundError("目标内容不存在")

    return target


def _get_parent_comment(db: Session, parent_id: Any, target_type: str, target_id: Any) -> Optional[Comment]:
    """获取父级评论

    Args:
        db: 数据库会话
        parent_id: 父级评论ID
        target_type: 目标类型
        target_id: 目标ID

    Returns:
        父级评论对象，如果不存在则返回 None

    Raises:
        ValidationError: 父级评论不存在
    """
    if not parent_id:
        return None

    parent = (
        db.query(Comment)
        .filter(Comment.id == parent_id, Comment.target_type == target_type, Comment.target_id == target_id)
        .first()
    )

    if not parent:
        raise ValidationError("父级评论不存在")

    return parent


def _collect_notification_recipients(user: User, parent: Optional[Comment], target: Any, target_type: str) -> set:
    """收集需要通知的用户ID

    Args:
        user: 当前用户
        parent: 父级评论
        target: 目标对象
        target_type: 目标类型

    Returns:
        需要通知的用户ID集合
    """
    recipients = set()

    # 通知父级评论作者
    if parent and parent.user_id and parent.user_id != user.id:
        recipients.add(str(parent.user_id))

    # 通知目标内容所有者
    owner_id = getattr(target, "uploader_id", None)
    if owner_id and owner_id != user.id:
        recipients.add(str(owner_id))

    return recipients


def _send_comment_notifications(
    db: Session, user: User, content: str, parent: Optional[Comment], recipients: set
) -> None:
    """发送评论通知消息

    Args:
        db: 数据库会话
        user: 当前用户
        content: 评论内容
        parent: 父级评论
        recipients: 接收者ID集合
    """
    from app.models.database import Message

    snippet = content[:80]

    if parent:
        title = "你收到了新的评论回复"
        body = f"{user.username} 回复了你的评论：{snippet}"
    else:
        title = "你收到了新的评论"
        body = f"{user.username} 评论了你的内容：{snippet}"

    for rid in recipients:
        try:
            message = Message(
                sender_id=str(user.id),
                recipient_id=str(rid),
                title=title,
                content=body,
                message_type="comment",
                summary=snippet,
            )
            db.add(message)
        except Exception:
            continue


def _build_comment_response(comment: Comment, user: User) -> dict:
    """构建评论响应数据

    Args:
        comment: 评论对象
        user: 用户对象

    Returns:
        评论响应数据字典
    """
    return {
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


@router.post(
    "/comments",
)
async def create_comment(
    data: dict = Body(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """创建评论或回复（受禁言限制）"""
    try:
        # 验证输入
        content = _validate_comment_input(data.get("content"), data.get("target_type"), data.get("target_id"))
        target_type = data.get("target_type")
        target_id = data.get("target_id")
        parent_id = data.get("parent_id")

        # 获取并验证用户
        sender_id = current_user.get("id")
        if not sender_id:
            raise AuthorizationError("用户未登录")

        user = db.query(User).filter(User.id == sender_id).first()
        if not user:
            raise NotFoundError("用户不存在")

        # 检查禁言状态
        _check_user_mute_status(user)

        # 获取目标对象
        target = _get_comment_target(db, target_type, target_id)

        # 获取父级评论（如果有）
        parent = _get_parent_comment(db, parent_id, target_type, target_id)

        # 创建评论
        comment = Comment(
            user_id=user.id,
            target_type=target_type,
            target_id=target_id,
            parent_id=parent.id if parent else None,
            content=content,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)

        # 收集通知接收者
        recipients = _collect_notification_recipients(user, parent, target, target_type)

        # 发送通知
        _send_comment_notifications(db, user, content, parent, recipients)
        db.commit()

        # 失效评论缓存
        invalidate_comment_cache()

        # 广播WebSocket更新
        if recipients:
            await message_ws_manager.broadcast_user_update(recipients)

        # 返回响应
        return Success(message="发表评论成功", data=_build_comment_response(comment, user))

    except (ValidationError, AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        log_exception(app_logger, "Create comment error", exception=e)
        raise APIError("发表评论失败")


@router.post(
    "/comments/{comment_id}/react",
)
async def react_comment(
    comment_id: str,
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """对评论进行点赞或踩，支持撤销"""
    action = (data.get("action") or "").strip().lower()
    if action not in ["like", "dislike", "clear"]:
        raise ValidationError("action 必须是 like、dislike 或 clear")

    user_id = current_user.get("id")
    if not user_id:
        raise AuthorizationError("用户未登录")

    try:
        comment = db.query(Comment).filter(Comment.id == comment_id, Comment.is_deleted.is_(False)).first()
        if not comment:
            raise NotFoundError("评论不存在或已删除")

        reaction = (
            db.query(CommentReaction)
            .filter(CommentReaction.comment_id == comment_id, CommentReaction.user_id == user_id)
            .first()
        )

        before_type: Optional[str] = reaction.reaction_type if reaction else None
        after_type: Optional[str] = _process_reaction_action(db, comment, reaction, action, user_id, comment_id)

        db.commit()
        db.refresh(comment)

        my_reaction = _determine_my_reaction(action, after_type)

        # 发送通知
        if _should_send_notification(after_type, before_type, user_id, comment.user_id):
            await _send_reaction_notification(db, user_id, comment, after_type, current_user.get("username", ""))

        return Success(
            message="操作成功",
            data={
                "id": comment.id,
                "likeCount": comment.like_count or 0,
                "dislikeCount": comment.dislike_count or 0,
                "myReaction": my_reaction,
            },
        )
    except (ValidationError, AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        log_exception(app_logger, "React comment error", exception=e)
        raise APIError("操作失败")


def _process_reaction_action(
    db: Session, comment: Comment, reaction: Optional[CommentReaction], action: str, user_id: Any, comment_id: str
) -> Optional[str]:
    """处理反应操作并返回操作后的反应类型

    Args:
        db: 数据库会话
        comment: 评论对象
        reaction: 现有反应对象
        action: 操作类型（like/dislike/clear）
        user_id: 用户ID
        comment_id: 评论ID

    Returns:
        操作后的反应类型，如果清除则返回 None
    """
    if action == "clear":
        return _handle_clear_reaction(db, comment, reaction)
    elif action == "like":
        return _handle_like_reaction(db, comment, reaction, user_id, comment_id)
    elif action == "dislike":
        return _handle_dislike_reaction(db, comment, reaction, user_id, comment_id)
    return None


def _handle_clear_reaction(db: Session, comment: Comment, reaction: Optional[CommentReaction]) -> Optional[str]:
    """处理清除反应操作

    Args:
        db: 数据库会话
        comment: 评论对象
        reaction: 现有反应对象

    Returns:
        None（表示清除反应）
    """
    if not reaction:
        return None

    if reaction.reaction_type == "like":
        comment.like_count = max((comment.like_count or 0) - 1, 0)
    elif reaction.reaction_type == "dislike":
        comment.dislike_count = max((comment.dislike_count or 0) - 1, 0)

    db.delete(reaction)
    return None


def _handle_like_reaction(
    db: Session, comment: Comment, reaction: Optional[CommentReaction], user_id: Any, comment_id: str
) -> Optional[str]:
    """处理点赞操作

    Args:
        db: 数据库会话
        comment: 评论对象
        reaction: 现有反应对象
        user_id: 用户ID
        comment_id: 评论ID

    Returns:
        操作后的反应类型
    """
    # 如果已经点赞，则取消点赞
    if reaction and reaction.reaction_type == "like":
        comment.like_count = max((comment.like_count or 0) - 1, 0)
        db.delete(reaction)
        return None

    # 如果之前是踩，则改为点赞
    if reaction and reaction.reaction_type == "dislike":
        comment.dislike_count = max((comment.dislike_count or 0) - 1, 0)
        reaction.reaction_type = "like"
    else:
        # 新增点赞
        reaction = CommentReaction(user_id=user_id, comment_id=comment_id, reaction_type="like")
        db.add(reaction)

    comment.like_count = (comment.like_count or 0) + 1
    return "like"


def _handle_dislike_reaction(
    db: Session, comment: Comment, reaction: Optional[CommentReaction], user_id: Any, comment_id: str
) -> Optional[str]:
    """处理踩操作

    Args:
        db: 数据库会话
        comment: 评论对象
        reaction: 现有反应对象
        user_id: 用户ID
        comment_id: 评论ID

    Returns:
        操作后的反应类型
    """
    # 如果已经踩，则取消踩
    if reaction and reaction.reaction_type == "dislike":
        comment.dislike_count = max((comment.dislike_count or 0) - 1, 0)
        db.delete(reaction)
        return None

    # 如果之前是点赞，则改为踩
    if reaction and reaction.reaction_type == "like":
        comment.like_count = max((comment.like_count or 0) - 1, 0)
        reaction.reaction_type = "dislike"
    else:
        # 新增踩
        reaction = CommentReaction(user_id=user_id, comment_id=comment_id, reaction_type="dislike")
        db.add(reaction)

    comment.dislike_count = (comment.dislike_count or 0) + 1
    return "dislike"


def _determine_my_reaction(action: str, after_type: Optional[str]) -> Optional[str]:
    """确定用户当前的反应状态

    Args:
        action: 操作类型
        after_type: 操作后的反应类型

    Returns:
        用户当前的反应状态
    """
    if action == "clear":
        return None

    if action in ["like", "dislike"] and after_type is None:
        return None

    return after_type


def _should_send_notification(
    after_type: Optional[str], before_type: Optional[str], user_id: Any, comment_user_id: Any
) -> bool:
    """判断是否需要发送通知

    Args:
        after_type: 操作后的反应类型
        before_type: 操作前的反应类型
        user_id: 当前用户ID
        comment_user_id: 评论作者ID

    Returns:
        是否需要发送通知
    """
    return after_type in ["like", "dislike"] and after_type != before_type and str(user_id) != str(comment_user_id)


async def _send_reaction_notification(
    db: Session, user_id: Any, comment: Comment, reaction_type: str, sender_name: str
) -> None:
    """发送反应通知

    Args:
        db: 数据库会话
        user_id: 当前用户ID
        comment: 评论对象
        reaction_type: 反应类型
        sender_name: 发送者用户名
    """
    recipient_id = str(comment.user_id)
    snippet = (comment.content or "")[:80]

    title = "你的评论收到新的点赞" if reaction_type == "like" else "你的评论收到新的踩"
    body = f"{sender_name} 对你的评论进行了{'点赞' if reaction_type == 'like' else '踩'}：{snippet}"

    try:
        from app.models.database import Message

        message = Message(
            sender_id=str(user_id),
            recipient_id=recipient_id,
            title=title,
            content=body,
            message_type="reaction",
            summary=snippet,
        )
        db.add(message)
        db.commit()
        await message_ws_manager.broadcast_user_update({recipient_id})
    except Exception:
        pass


def _check_comment_owner_permission(comment: Comment, user_id: str) -> bool:
    """检查是否是评论作者

    Args:
        comment: 评论对象
        user_id: 用户ID

    Returns:
        是否有权限
    """
    return comment.user_id == user_id


def _check_target_owner_permission(comment: Comment, user_id: str, db: Session) -> bool:
    """检查是否是目标对象的所有者

    Args:
        comment: 评论对象
        user_id: 用户ID
        db: 数据库会话

    Returns:
        是否有权限
    """
    target_obj: Optional[Any] = None
    if comment.target_type == "knowledge":
        target_obj = db.query(KnowledgeBase).filter(KnowledgeBase.id == comment.target_id).first()
    else:
        target_obj = db.query(PersonaCard).filter(PersonaCard.id == comment.target_id).first()

    if target_obj and str(getattr(target_obj, "uploader_id", "")) == str(user_id):
        return True
    return False


def _check_admin_permission(current_user: dict) -> bool:
    """检查是否是管理员或审核员

    Args:
        current_user: 当前用户信息

    Returns:
        是否有权限
    """
    is_admin = current_user.get("is_admin", False)
    user_role = current_user.get("role", "user")
    return is_admin or user_role in ["admin", "moderator"]


def _validate_delete_comment_permission(comment: Comment, current_user: dict, db: Session) -> None:
    """验证删除评论权限

    Args:
        comment: 评论对象
        current_user: 当前用户信息
        db: 数据库会话

    Raises:
        AuthorizationError: 没有权限删除此评论
    """
    user_id = current_user.get("id")

    # 检查是否是评论作者
    if _check_comment_owner_permission(comment, user_id):
        return

    # 检查是否是目标对象的所有者
    if _check_target_owner_permission(comment, user_id, db):
        return

    # 检查是否是管理员或审核员
    if _check_admin_permission(current_user):
        return

    raise AuthorizationError("没有权限删除此评论")


def _soft_delete_comment_and_children(comment: Comment, db: Session) -> None:
    """软删除评论及其子评论

    Args:
        comment: 评论对象
        db: 数据库会话
    """
    comment.is_deleted = True

    # 如果是一级评论，级联删除所有子评论
    if comment.parent_id is None:
        children = db.query(Comment).filter(Comment.parent_id == comment.id).all()
        for child in children:
            child.is_deleted = True

    db.commit()


@router.delete(
    "/comments/{comment_id}",
)
async def delete_comment(
    comment_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """删除评论（软删除，支持级联删除二级评论）"""
    try:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise NotFoundError("评论不存在")

        _validate_delete_comment_permission(comment, current_user, db)
        _soft_delete_comment_and_children(comment, db)

        # 失效评论缓存
        invalidate_comment_cache()

        return Success(message="删除评论成功", data={"id": comment.id})
    except (AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete comment error", exception=e)
        raise APIError("删除评论失败")


def _validate_restore_comment_permission(comment: Comment, current_user: dict, db: Session) -> None:
    """验证恢复评论权限

    Args:
        comment: 评论对象
        current_user: 当前用户信息
        db: 数据库会话

    Raises:
        AuthorizationError: 没有权限撤销此评论删除
    """
    user_id = current_user.get("id")

    # 检查是否是评论作者
    if _check_comment_owner_permission(comment, user_id):
        return

    # 检查是否是目标对象的所有者
    if _check_target_owner_permission(comment, user_id, db):
        return

    # 检查是否是管理员或审核员
    if _check_admin_permission(current_user):
        return

    raise AuthorizationError("没有权限撤销此评论删除")


def _restore_comment_and_children(comment: Comment, db: Session) -> None:
    """恢复评论及其子评论

    Args:
        comment: 评论对象
        db: 数据库会话
    """
    comment.is_deleted = False

    # 如果是一级评论，恢复所有子评论
    if comment.parent_id is None:
        children = db.query(Comment).filter(Comment.parent_id == comment.id).all()
        for child in children:
            child.is_deleted = False

    db.commit()


@router.post(
    "/comments/{comment_id}/restore",
)
async def restore_comment(
    comment_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """撤销删除评论（恢复软删除的评论以及其子评论）"""
    try:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise NotFoundError("评论不存在")

        _validate_restore_comment_permission(comment, current_user, db)
        _restore_comment_and_children(comment, db)

        return Success(message="撤销删除评论成功", data={"id": comment.id})
    except (AuthorizationError, NotFoundError):
        raise
    except Exception as e:
        log_exception(app_logger, "Restore comment error", exception=e)
        raise APIError("撤销删除评论失败")
