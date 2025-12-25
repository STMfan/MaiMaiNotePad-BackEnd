from fastapi import APIRouter, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime

from api_routes.response_util import Success
from models import (
    MessageCreate, MessageUpdate, MessageResponse
)
from database_models import sqlite_db_manager
from user_management import get_current_user

# 导入错误处理和日志记录模块
from logging_config import app_logger, log_exception, log_database_operation
from error_handlers import (
    APIError, ValidationError,
    AuthorizationError, NotFoundError, DatabaseError
)

# 创建路由器
messages_router = APIRouter()

# 使用SQLite数据库管理器
db_manager = sqlite_db_manager


# 消息相关路由
@messages_router.post("/messages/send")
async def send_message(
        message: MessageCreate,
        current_user: dict = Depends(get_current_user)
):
    """发送消息"""
    sender_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Send message: sender={sender_id}, type={message.message_type}, "
            f"recipient={message.recipient_id}, broadcast_scope={message.broadcast_scope}"
        )

        title = (message.title or "").strip()
        content = (message.content or "").strip()

        if not title:
            raise ValidationError("消息标题不能为空")

        if not content:
            raise ValidationError("消息内容不能为空")

        # 权限检查：只有announcement类型可以使用broadcast_scope
        if message.broadcast_scope and message.message_type != "announcement":
            raise ValidationError("只有公告类型消息可以使用广播功能")

        # 权限检查：发送全用户广播需要管理员或审核员权限
        if message.broadcast_scope == "all_users":
            user_role = current_user.get("role", "user")
            is_admin_or_moderator = user_role in ["admin", "moderator"]
            if not is_admin_or_moderator:
                raise AuthorizationError("只有管理员和审核员可以发送全用户广播")

        recipient_ids = set()
        if message.recipient_id:
            recipient_ids.add(message.recipient_id)
        if message.recipient_ids:
            recipient_ids.update(message.recipient_ids)

        if message.message_type == "direct":
            if not recipient_ids:
                raise ValidationError("接收者ID不能为空")
        elif message.broadcast_scope == "all_users":
            all_users = db_manager.get_all_users()
            recipient_ids.update(user.id for user in all_users if user.id)

        # 移除发送者自身除非显式指定
        if sender_id in recipient_ids and message.message_type == "announcement" and message.broadcast_scope == "all_users":
            recipient_ids.discard(sender_id)

        if not recipient_ids:
            raise ValidationError("没有有效的接收者")

        # 检查接收者是否存在
        recipient_objects = db_manager.get_users_by_ids(list(recipient_ids))
        found_ids = {user.id for user in recipient_objects}
        missing = recipient_ids - found_ids
        if missing:
            raise NotFoundError(f"接收者不存在: {', '.join(missing)}")

        # 对接收者对象按用户ID去重，确保每个用户只创建一条消息
        # 使用字典按用户ID去重，保留第一个出现的用户对象
        unique_recipients = {}
        for user in recipient_objects:
            if user.id and user.id not in unique_recipients:
                unique_recipients[user.id] = user

        # 如果未提供summary，可以从content自动生成（取前150字符）
        summary = message.summary
        if not summary and content:
            import re
            text = re.sub(r'<[^>]+>', '', content)  # 移除HTML标签（如果有）
            text = ' '.join(text.split())  # 移除多余空白
            if len(text) > 150:
                truncated = text[:150]
                last_punctuation = max(
                    truncated.rfind('。'),
                    truncated.rfind('！'),
                    truncated.rfind('？'),
                    truncated.rfind('.'),
                    truncated.rfind('!'),
                    truncated.rfind('?')
                )
                if last_punctuation > 75:
                    summary = truncated[:last_punctuation + 1]
                else:
                    summary = truncated + '...'
            else:
                summary = text

        message_payloads = [
            {
                "sender_id": sender_id,
                "recipient_id": user.id,
                "title": title,
                "content": content,
                "summary": summary,
                "message_type": message.message_type,
                "broadcast_scope": message.broadcast_scope if message.message_type == "announcement" else None
            }
            for user in unique_recipients.values()
        ]

        try:
            created_messages = db_manager.bulk_create_messages(
                message_payloads)
            if not created_messages:
                raise DatabaseError("消息创建失败")
        except Exception as e:
            # 将数据库异常转换为DatabaseError
            raise DatabaseError(f"消息创建失败: {str(e)}")

        # 记录数据库操作成功
        for msg in created_messages:
            log_database_operation(
                app_logger,
                "create",
                "message",
                record_id=msg.id,
                user_id=sender_id,
                success=True
            )

        return Success(
            message="消息发送成功",
            data={
                "message_ids": [msg.id for msg in created_messages],
                "status": "sent",
                "count": len(created_messages)
            }
        )

    except (ValidationError, NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Send message error", exception=e)
        log_database_operation(
            app_logger,
            "create",
            "message",
            user_id=sender_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("发送消息失败")


@messages_router.get("/messages/{message_id}")
async def get_message_detail(
        message_id: str,
        current_user: dict = Depends(get_current_user)
):
    """获取消息详情"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Get message detail: message_id={message_id}, user_id={user_id}")

        # 检查消息是否存在
        message = db_manager.get_message_by_id(message_id)
        if not message:
            raise NotFoundError("消息不存在")

        # 验证权限：只有接收者可以查看消息详情
        recipient_id = str(
            message.recipient_id) if message.recipient_id else ""
        user_id_str = str(user_id) if user_id else ""

        if recipient_id != user_id_str:
            raise AuthorizationError("没有权限查看此消息")

        return Success(
            message="消息详情获取成功",
            data={
                "id": message.id,
                "sender_id": message.sender_id,
                "recipient_id": message.recipient_id,
                "title": message.title,
                "content": message.content,
                "summary": message.summary,
                "message_type": message.message_type or "direct",
                "broadcast_scope": message.broadcast_scope,
                "is_read": message.is_read or False,
                "created_at": message.created_at if message.created_at else datetime.now()
            }
        )

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get message detail error", exception=e)
        raise APIError("获取消息详情失败")


@messages_router.get("/messages")
async def get_messages(
        current_user: dict = Depends(get_current_user),
        other_user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
):
    """获取消息列表"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Get messages: user_id={user_id}, other_user_id={other_user_id}, page={page}, page_size={page_size}")

        # 验证参数
        if page <= 0 or page_size <= 0 or page_size > 100:
            raise ValidationError("page和page_size必须大于0，page_size最多100条")

        if offset < 0:
            raise ValidationError("offset不能为负数")

        # 获取消息列表
        if other_user_id:
            # 获取与特定用户的对话
            messages = db_manager.get_conversation_messages(
                user_id=user_id,
                other_user_id=other_user_id,
                page=page,
                page_size=page_size
            )
        else:
            # 获取所有消息
            messages = db_manager.get_user_messages(
                user_id=user_id,
                page=page,
                page_size=page_size
            )

        return Success(
            message="消息列表获取成功",
            data=[MessageResponse(**msg.to_dict()) for msg in messages]
        )

    except (ValidationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get messages error", exception=e)
        raise APIError("获取消息列表失败")


@messages_router.post("/messages/{message_id}/read")
async def mark_message_read(
        message_id: str,
        current_user: dict = Depends(get_current_user)
):
    """标记消息为已读"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Mark message as read: message_id={message_id}, user_id={user_id}")

        # 验证用户ID
        if not user_id:
            raise AuthorizationError("用户ID无效")

        # 检查消息是否存在
        message = db_manager.get_message_by_id(message_id)
        if not message:
            raise NotFoundError("消息不存在")

        # 验证权限：只有接收者可以标记消息为已读
        # 确保类型一致（都转换为字符串进行比较）
        recipient_id = str(
            message.recipient_id) if message.recipient_id else ""
        user_id_str = str(user_id) if user_id else ""

        if recipient_id != user_id_str:
            app_logger.warning(
                f"Unauthorized mark read attempt: user={user_id_str} (type={type(user_id)}) "
                f"trying to mark message={message_id} sent to {recipient_id} (type={type(message.recipient_id)})"
            )
            raise AuthorizationError("没有权限标记此消息为已读")

        # 标记为已读
        success = db_manager.mark_message_read(message_id, user_id)

        if not success:
            raise DatabaseError("标记消息已读失败")

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "update",
            "message",
            record_id=message_id,
            user_id=user_id,
            success=True
        )

        return Success(
            message="消息已标记为已读"
        )

    except (ValidationError, NotFoundError, AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Mark message read error", exception=e)
        log_database_operation(
            app_logger,
            "update",
            "message",
            record_id=message_id,
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("标记消息已读失败")


@messages_router.delete("/messages/{message_id}")
async def delete_message(
        message_id: str,
        current_user: dict = Depends(get_current_user)
):
    """删除消息（接收者可以删除，管理员可以删除公告）"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Delete message: message_id={message_id}, user_id={user_id}")

        # 验证用户ID
        if not user_id:
            raise AuthorizationError("用户ID无效")

        # 检查消息是否存在
        message = db_manager.get_message_by_id(message_id)
        if not message:
            raise NotFoundError("消息不存在")

        # 验证权限
        recipient_id = str(
            message.recipient_id) if message.recipient_id else ""
        sender_id = str(message.sender_id) if message.sender_id else ""
        user_id_str = str(user_id) if user_id else ""

        is_admin = current_user.get("is_admin", False)
        is_moderator = current_user.get("is_moderator", False)
        is_admin_or_moderator = is_admin or is_moderator

        # 权限检查：
        # 1. 接收者可以删除任何消息
        # 2. 管理员/审核员可以删除公告类型的消息（作为发送者）
        can_delete = False
        if recipient_id == user_id_str:
            can_delete = True
        elif (is_admin_or_moderator and
              message.message_type == "announcement" and
              message.broadcast_scope == "all_users" and
              sender_id == user_id_str):
            can_delete = True

        if not can_delete:
            app_logger.warning(
                f"Unauthorized delete attempt: user={user_id_str} (admin={is_admin}, moderator={is_moderator}) "
                f"trying to delete message={message_id} (type={message.message_type}, "
                f"recipient={recipient_id}, sender={sender_id})"
            )
            raise AuthorizationError("没有权限删除此消息")

        # 删除消息
        # 只有当管理员是发送者且不是接收者时，才使用批量删除
        # 如果管理员是接收者（即使他也是发送者），只删除单条消息
        if (recipient_id != user_id_str and  # 不是作为接收者删除
                is_admin_or_moderator and
                message.message_type == "announcement" and
                message.broadcast_scope == "all_users" and
                sender_id == user_id_str):
            # 管理员作为发送者删除公告，批量删除所有相关消息
            deleted_count = db_manager.delete_broadcast_messages(
                message_id, user_id)
            if deleted_count == 0:
                raise DatabaseError("删除公告失败")
        else:
            # 普通消息或接收者删除消息，使用单条删除方法
            success = db_manager.delete_message(message_id, user_id)
            if not success:
                raise DatabaseError("删除消息失败")
            deleted_count = 1

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "delete",
            "message",
            record_id=message_id,
            user_id=user_id,
            success=True
        )

        return Success(
            message="消息已删除",
            data={"deleted_count": deleted_count}
        )

    except (NotFoundError, AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete message error", exception=e)
        log_database_operation(
            app_logger,
            "delete",
            "message",
            record_id=message_id,
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("删除消息失败")


@messages_router.put("/messages/{message_id}")
async def update_message(
        message_id: str,
        update_data: MessageUpdate,
        current_user: dict = Depends(get_current_user)
):
    """修改消息（接收者可以修改，管理员可以修改公告）"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Update message: message_id={message_id}, user_id={user_id}")

        # 验证用户ID
        if not user_id:
            raise AuthorizationError("用户ID无效")

        # 验证更新数据
        title = update_data.title.strip(
        ) if update_data.title and update_data.title.strip() else None
        content = update_data.content.strip(
        ) if update_data.content and update_data.content.strip() else None
        summary = update_data.summary.strip(
        ) if update_data.summary and update_data.summary.strip() else None

        if not title and not content and summary is None:
            raise ValidationError("至少需要提供标题、内容或简介之一")

        # 检查消息是否存在
        message = db_manager.get_message_by_id(message_id)
        if not message:
            raise NotFoundError("消息不存在")

        # 验证权限
        recipient_id = str(
            message.recipient_id) if message.recipient_id else ""
        sender_id = str(message.sender_id) if message.sender_id else ""
        user_id_str = str(user_id) if user_id else ""

        is_admin = current_user.get("is_admin", False)
        is_moderator = current_user.get("is_moderator", False)
        is_admin_or_moderator = is_admin or is_moderator

        # 权限检查：
        # 1. 接收者可以修改任何消息
        # 2. 管理员/审核员可以修改公告类型的消息（作为发送者）
        can_update = False
        if recipient_id == user_id_str:
            can_update = True
        elif (is_admin_or_moderator and
              message.message_type == "announcement" and
              message.broadcast_scope == "all_users" and
              sender_id == user_id_str):
            can_update = True

        if not can_update:
            app_logger.warning(
                f"Unauthorized update attempt: user={user_id_str} (admin={is_admin}, moderator={is_moderator}) "
                f"trying to update message={message_id} (type={message.message_type}, "
                f"recipient={recipient_id}, sender={sender_id})"
            )
            raise AuthorizationError("没有权限修改此消息")

        # 更新消息
        # 如果是公告，使用批量更新方法
        if message.message_type == "announcement" and message.broadcast_scope == "all_users" and sender_id == user_id_str:
            updated_count = db_manager.update_broadcast_messages(
                message_id,
                user_id,
                title=title,
                content=content,
                summary=summary
            )
            if updated_count == 0:
                raise DatabaseError("更新公告失败")
        else:
            # 普通消息，直接更新单条
            if title:
                message.title = title
            if content:
                message.content = content
            if summary is not None:  # 允许设置为空字符串
                message.summary = summary

            # 保存更新
            success = db_manager.save_message(message)
            if not success:
                raise DatabaseError("更新消息失败")
            updated_count = 1

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "update",
            "message",
            record_id=message_id,
            user_id=user_id,
            success=True
        )

        return Success(
            message="消息已更新",
            data={"updated_count": updated_count}
        )

    except (ValidationError, NotFoundError, AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Update message error", exception=e)
        log_database_operation(
            app_logger,
            "update",
            "message",
            record_id=message_id,
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("更新消息失败")


@messages_router.get("/admin/broadcast-messages")
async def get_broadcast_messages(
        current_user: dict = Depends(get_current_user),
        page: int = 1,
        page_size: int = 20
):
    """获取广播消息历史（仅限admin和moderator）"""
    # 验证权限：admin或moderator
    user_role = current_user.get("role", "user")
    is_admin_or_moderator = user_role in ["admin", "moderator"]
    if not is_admin_or_moderator:
        raise AuthorizationError("需要管理员或审核员权限")

    try:
        app_logger.info(
            f"Get broadcast messages: user_id={current_user.get('id')}, page={page}, page_size={page_size}")

        # 验证参数
        if page_size <= 0 or page_size > 100:
            raise ValidationError("page_size必须在1-100之间")

        if page < 1:
            raise ValidationError("page必须大于等于1")

        # 获取广播消息
        messages = db_manager.get_broadcast_messages(
            page=page, page_size=page_size)

        # 获取发送者信息
        sender_ids = list(set([msg.sender_id for msg in messages]))
        senders = {}
        if sender_ids:
            users = db_manager.get_users_by_ids(sender_ids)
            for user in users:
                senders[user.id] = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }

        # 构建返回数据，包含统计信息
        result = []
        for msg in messages:
            stats = db_manager.get_broadcast_message_stats(
                message_id=msg.id
            )

            result.append({
                "id": msg.id,
                "sender_id": msg.sender_id,
                "sender": senders.get(msg.sender_id, {"id": msg.sender_id, "username": "未知用户", "email": ""}),
                "title": msg.title,
                "content": msg.content,
                "message_type": msg.message_type,
                "broadcast_scope": msg.broadcast_scope,
                "created_at": msg.created_at.isoformat() if msg.created_at else "",
                "stats": stats
            })
        
        total = db_manager.count_broadcast_messages()

        return Page(
            message="广播消息历史获取成功",
            data=result,
            total=total,
            page=page,
            page_size=page_size
        )

    except (ValidationError, AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get broadcast messages error", exception=e)
        raise APIError("获取广播消息历史失败")
