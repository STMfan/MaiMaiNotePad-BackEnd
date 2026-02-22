"""
消息路由模块

处理消息相关的API端点，包括：
- 发送消息
- 查询消息
- 标记消息已读/未读
- 删除消息
- 广播消息
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.response_util import Success, Page
from app.core.error_handlers import APIError, ValidationError, AuthorizationError, NotFoundError, DatabaseError

# 导入错误处理和日志记录模块
from app.core.logging import app_logger, log_exception, log_database_operation
from app.models.schemas import MessageCreate, MessageUpdate, MessageResponse, BaseResponse, PageResponse
from app.api.deps import get_current_user
from app.core.database import get_db
from app.services.message_service import MessageService
from app.utils.websocket import message_ws_manager

# 创建路由器
router = APIRouter()


# 消息相关路由（发送、查询、标记已读、删除等）
def _validate_message_input(title: str, content: str) -> tuple[str, str]:
    """验证消息输入
    
    Args:
        title: 消息标题
        content: 消息内容
        
    Returns:
        清理后的标题和内容元组
        
    Raises:
        ValidationError: 输入验证失败
    """
    title = (title or "").strip()
    content = (content or "").strip()
    
    if not title:
        raise ValidationError("消息标题不能为空")
    if not content:
        raise ValidationError("消息内容不能为空")
    
    return title, content


def _validate_broadcast_permissions(
    message_type: str,
    broadcast_scope: Optional[str],
    user_role: str
) -> None:
    """验证广播权限
    
    Args:
        message_type: 消息类型
        broadcast_scope: 广播范围
        user_role: 用户角色
        
    Raises:
        ValidationError: 广播类型不匹配
        AuthorizationError: 权限不足
    """
    # 只有announcement类型可以使用broadcast_scope
    if broadcast_scope and message_type != "announcement":
        raise ValidationError("只有公告类型消息可以使用广播功能")
    
    # 发送全用户广播需要管理员或审核员权限
    if broadcast_scope == "all_users":
        is_admin_or_moderator = user_role in ["admin", "moderator", "super_admin"]
        if not is_admin_or_moderator:
            raise AuthorizationError("只有管理员和审核员可以发送全用户广播")


def _collect_recipient_ids(
    message_service: MessageService,
    recipient_id: Optional[str],
    recipient_ids: Optional[List[str]],
    message_type: str,
    broadcast_scope: Optional[str],
    sender_id: str
) -> set:
    """收集接收者ID
    
    Args:
        message_service: 消息服务实例
        recipient_id: 单个接收者ID
        recipient_ids: 多个接收者ID列表
        message_type: 消息类型
        broadcast_scope: 广播范围
        sender_id: 发送者ID
        
    Returns:
        接收者ID集合
        
    Raises:
        ValidationError: 接收者为空
    """
    recipients = set()
    
    # 收集指定的接收者
    if recipient_id:
        recipients.add(recipient_id)
    if recipient_ids:
        recipients.update(recipient_ids)
    
    # 处理全用户广播
    if broadcast_scope == "all_users":
        all_users = message_service.get_all_users()
        recipients.update(user.id for user in all_users if user.id)
    
    # 移除发送者自身（仅限全用户广播公告）
    if (
        sender_id in recipients
        and message_type == "announcement"
        and broadcast_scope == "all_users"
    ):
        recipients.discard(sender_id)
    
    # 验证接收者
    if message_type == "direct" and not recipients:
        raise ValidationError("接收者ID不能为空")
    
    if not recipients:
        raise ValidationError("没有有效的接收者")
    
    return recipients


def _validate_and_deduplicate_recipients(
    message_service: MessageService,
    recipient_ids: set
) -> dict:
    """验证并去重接收者
    
    Args:
        message_service: 消息服务实例
        recipient_ids: 接收者ID集合
        
    Returns:
        去重后的接收者字典 {user_id: user_object}
        
    Raises:
        NotFoundError: 接收者不存在
    """
    # 检查接收者是否存在
    recipient_objects = message_service.get_users_by_ids(list(recipient_ids))
    found_ids = {user.id for user in recipient_objects}
    missing = recipient_ids - found_ids
    
    if missing:
        raise NotFoundError(f"接收者不存在: {', '.join(missing)}")
    
    # 按用户ID去重，确保每个用户只创建一条消息
    unique_recipients = {}
    for user in recipient_objects:
        if user.id and user.id not in unique_recipients:
            unique_recipients[user.id] = user
    
    return unique_recipients


@router.post("/messages/send", response_model=BaseResponse[dict])
async def send_message(
    message: MessageCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """发送消息"""
    sender_id = current_user.get("id", "")
    
    try:
        app_logger.info(
            f"Send message: sender={sender_id}, type={message.message_type}, "
            f"recipient={message.recipient_id}, broadcast_scope={message.broadcast_scope}"
        )
        
        # 验证输入
        title, content = _validate_message_input(message.title, message.content)
        
        # 验证广播权限
        _validate_broadcast_permissions(
            message.message_type,
            message.broadcast_scope,
            current_user.get("role", "user")
        )
        
        # 使用服务层
        message_service = MessageService(db)
        
        # 收集接收者ID
        recipient_ids = _collect_recipient_ids(
            message_service,
            message.recipient_id,
            message.recipient_ids,
            message.message_type,
            message.broadcast_scope,
            sender_id
        )
        
        # 验证并去重接收者
        unique_recipients = _validate_and_deduplicate_recipients(
            message_service,
            recipient_ids
        )
        
        # 生成摘要
        summary = message.summary
        if not summary and content:
            summary = message_service.generate_summary(content)
        
        # 创建消息
        created_messages = message_service.create_messages(
            sender_id=sender_id,
            recipient_ids=set(unique_recipients.keys()),
            title=title,
            content=content,
            summary=summary,
            message_type=message.message_type,
            broadcast_scope=message.broadcast_scope,
        )
        
        if not created_messages:
            raise DatabaseError("消息创建失败")
        
        # 记录数据库操作成功
        for msg in created_messages:
            log_database_operation(app_logger, "create", "message", record_id=msg.id, user_id=sender_id, success=True)
        
        # 广播WebSocket更新
        await message_ws_manager.broadcast_user_update(set(unique_recipients.keys()))
        
        return Success(
            message="消息发送成功",
            data={
                "message_ids": [msg.id for msg in created_messages],
                "status": "sent",
                "count": len(created_messages),
            },
        )
    
    except (ValidationError, NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Send message error", exception=e)
        log_database_operation(app_logger, "create", "message", user_id=sender_id, success=False, error_message=str(e))
        raise APIError("发送消息失败")


@router.get("/messages/{message_id}", response_model=BaseResponse[MessageResponse])
async def get_message_detail(
    message_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """获取消息详情"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Get message detail: message_id={message_id}, user_id={user_id}")

        # 使用服务层
        message_service = MessageService(db)

        # 检查消息是否存在
        message = message_service.get_message_by_id(message_id)
        if not message:
            raise NotFoundError("消息不存在")

        # 验证权限：只有接收者可以查看消息详情
        recipient_id = str(message.recipient_id) if message.recipient_id else ""
        user_id_str = str(user_id) if user_id else ""

        if recipient_id != user_id_str:
            raise AuthorizationError("没有权限查看此消息")

        # Ensure message_type is a valid Literal type
        msg_type: Literal["direct", "announcement"] = "direct"
        if message.message_type == "announcement":
            msg_type = "announcement"

        return Success(
            message="消息详情获取成功",
            data=MessageResponse(
                id=message.id,
                sender_id=message.sender_id,
                recipient_id=message.recipient_id,
                title=message.title,
                content=message.content,
                summary=message.summary,
                message_type=msg_type,
                broadcast_scope=message.broadcast_scope,
                is_read=message.is_read or False,
                created_at=message.created_at if message.created_at else datetime.now(),
            ),
        )

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get message detail error", exception=e)
        raise APIError("获取消息详情失败")


@router.get("/messages", response_model=BaseResponse[list[MessageResponse]])
async def get_messages(
    current_user: dict = Depends(get_current_user),
    other_user_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """获取消息列表"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Get messages: user_id={user_id}, other_user_id={other_user_id}, page={page}, page_size={page_size}"
        )

        # 验证参数
        if page <= 0 or page_size <= 0 or page_size > 100:
            raise ValidationError("page和page_size必须大于0，page_size最多100条")

        # 使用服务层
        message_service = MessageService(db)

        # 获取消息列表
        if other_user_id:
            # 获取与特定用户的对话
            messages = message_service.get_conversation_messages(
                user_id=user_id, other_user_id=other_user_id, page=page, page_size=page_size
            )
        else:
            # 获取所有消息
            messages = message_service.get_user_messages(user_id=user_id, page=page, page_size=page_size)

        # Convert messages to response format with proper type handling
        message_responses = []
        for msg in messages:
            msg_type: Literal["direct", "announcement"] = "direct"
            if msg.message_type == "announcement":
                msg_type = "announcement"

            message_responses.append(
                MessageResponse(
                    id=msg.id,
                    sender_id=msg.sender_id,
                    recipient_id=msg.recipient_id,
                    title=msg.title,
                    content=msg.content,
                    summary=msg.summary,
                    message_type=msg_type,
                    broadcast_scope=msg.broadcast_scope,
                    is_read=msg.is_read or False,
                    created_at=msg.created_at if msg.created_at else datetime.now(),
                )
            )

        return Success(
            message="消息列表获取成功",
            data=message_responses,
        )

    except (ValidationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get messages error", exception=e)
        raise APIError("获取消息列表失败")


@router.get("/messages/by-type/{message_type}", response_model=BaseResponse[list[MessageResponse]])
async def get_messages_by_type(
    message_type: str,
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """按类型获取消息列表"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Get messages by type: user_id={user_id}, message_type={message_type}, page={page}, page_size={page_size}"
        )

        if page <= 0 or page_size <= 0 or page_size > 100:
            raise ValidationError("page和page_size必须大于0，page_size最多100条")

        # 使用服务层
        message_service = MessageService(db)
        messages = message_service.get_user_messages_by_type(
            user_id=user_id, message_type=message_type, page=page, page_size=page_size
        )

        # Convert messages to response format with proper type handling
        message_responses = []
        for msg in messages:
            msg_type: Literal["direct", "announcement"] = "direct"
            if msg.message_type == "announcement":
                msg_type = "announcement"

            message_responses.append(
                MessageResponse(
                    id=msg.id,
                    sender_id=msg.sender_id,
                    recipient_id=msg.recipient_id,
                    title=msg.title,
                    content=msg.content,
                    summary=msg.summary,
                    message_type=msg_type,
                    broadcast_scope=msg.broadcast_scope,
                    is_read=msg.is_read or False,
                    created_at=msg.created_at if msg.created_at else datetime.now(),
                )
            )

        return Success(
            message="按类型获取消息列表成功",
            data=message_responses,
        )

    except (ValidationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get messages by type error", exception=e)
        raise APIError("按类型获取消息列表失败")


@router.post("/messages/{message_id}/read", response_model=BaseResponse[None])
async def mark_message_read(
    message_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """标记消息为已读"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Mark message as read: message_id={message_id}, user_id={user_id}")

        # 验证用户ID
        if not user_id:
            raise AuthorizationError("用户ID无效")

        # 使用服务层
        message_service = MessageService(db)

        # 检查消息是否存在
        message = message_service.get_message_by_id(message_id)
        if not message:
            raise NotFoundError("消息不存在")

        # 验证权限：只有接收者可以标记消息为已读
        # 确保类型一致（都转换为字符串进行比较）
        recipient_id = str(message.recipient_id) if message.recipient_id else ""
        user_id_str = str(user_id) if user_id else ""

        if recipient_id != user_id_str:
            app_logger.warning(
                f"Unauthorized mark read attempt: user={user_id_str} (type={type(user_id)}) "
                f"trying to mark message={message_id} sent to {recipient_id} (type={type(message.recipient_id)})"
            )
            raise AuthorizationError("没有权限标记此消息为已读")

        # 标记为已读
        success = message_service.mark_message_read(message_id, user_id)

        if not success:
            raise DatabaseError("标记消息已读失败")

        # 记录数据库操作成功
        log_database_operation(app_logger, "update", "message", record_id=message_id, user_id=user_id, success=True)

        await message_ws_manager.broadcast_user_update({user_id})

        return Success(message="消息已标记为已读")

    except (ValidationError, NotFoundError, AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Mark message read error", exception=e)
        log_database_operation(
            app_logger, "update", "message", record_id=message_id, user_id=user_id, success=False, error_message=str(e)
        )
        raise APIError("标记消息已读失败")


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """删除消息（接收者可以删除，管理员可以删除公告）"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Delete message: message_id={message_id}, user_id={user_id}")

        # 验证用户ID
        if not user_id:
            raise AuthorizationError("用户ID无效")

        # 使用服务层
        message_service = MessageService(db)

        # 检查消息是否存在
        message = message_service.get_message_by_id(message_id)
        if not message:
            raise NotFoundError("消息不存在")

        # 验证权限
        recipient_id = str(message.recipient_id) if message.recipient_id else ""
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
        elif (
            is_admin_or_moderator
            and message.message_type == "announcement"
            and message.broadcast_scope == "all_users"
            and sender_id == user_id_str
        ):
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
        if (
            recipient_id != user_id_str  # 不是作为接收者删除
            and is_admin_or_moderator
            and message.message_type == "announcement"
            and message.broadcast_scope == "all_users"
            and sender_id == user_id_str
        ):
            # 管理员作为发送者删除公告，批量删除所有相关消息
            deleted_count = message_service.delete_broadcast_messages(message_id, user_id)
            if deleted_count == 0:
                raise DatabaseError("删除公告失败")
        else:
            # 普通消息或接收者删除消息，使用单条删除方法
            success = message_service.delete_message(message_id, user_id)
            if not success:
                raise DatabaseError("删除消息失败")
            deleted_count = 1

        # 记录数据库操作成功
        log_database_operation(app_logger, "delete", "message", record_id=message_id, user_id=user_id, success=True)

        return Success(message="消息已删除", data={"deleted_count": deleted_count})

    except (NotFoundError, AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete message error", exception=e)
        log_database_operation(
            app_logger, "delete", "message", record_id=message_id, user_id=user_id, success=False, error_message=str(e)
        )
        raise APIError("删除消息失败")


@router.put("/messages/{message_id}")
async def update_message(
    message_id: str,
    update_data: MessageUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改消息（接收者可以修改，管理员可以修改公告）"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Update message: message_id={message_id}, user_id={user_id}")

        # 验证用户ID
        if not user_id:
            raise AuthorizationError("用户ID无效")

        # 验证更新数据
        title = update_data.title.strip() if update_data.title and update_data.title.strip() else None
        content = update_data.content.strip() if update_data.content and update_data.content.strip() else None
        summary = update_data.summary.strip() if update_data.summary and update_data.summary.strip() else None

        if not title and not content and summary is None:
            raise ValidationError("至少需要提供标题、内容或简介之一")

        # 使用服务层
        message_service = MessageService(db)

        # 检查消息是否存在
        message = message_service.get_message_by_id(message_id)
        if not message:
            raise NotFoundError("消息不存在")

        # 验证权限
        recipient_id = str(message.recipient_id) if message.recipient_id else ""
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
        elif (
            is_admin_or_moderator
            and message.message_type == "announcement"
            and message.broadcast_scope == "all_users"
            and sender_id == user_id_str
        ):
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
        if (
            message.message_type == "announcement"
            and message.broadcast_scope == "all_users"
            and sender_id == user_id_str
        ):
            updated_count = message_service.update_broadcast_messages(
                message_id, user_id, title=title, content=content, summary=summary
            )
            if updated_count == 0:
                raise DatabaseError("更新公告失败")
        else:
            # 普通消息，直接更新单条
            success = message_service.update_message(message_id, user_id, title=title, content=content, summary=summary)
            if not success:
                raise DatabaseError("更新消息失败")
            updated_count = 1

        # 记录数据库操作成功
        log_database_operation(app_logger, "update", "message", record_id=message_id, user_id=user_id, success=True)

        return Success(message="消息已更新", data={"updated_count": updated_count})

    except (ValidationError, NotFoundError, AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Update message error", exception=e)
        log_database_operation(
            app_logger, "update", "message", record_id=message_id, user_id=user_id, success=False, error_message=str(e)
        )
        raise APIError("更新消息失败")


@router.get("/admin/broadcast-messages", response_model=PageResponse[dict])
async def get_broadcast_messages(
    current_user: dict = Depends(get_current_user), page: int = 1, page_size: int = 20, db: Session = Depends(get_db)
):
    """获取广播消息历史（仅限admin和moderator）"""
    # 验证权限：admin或moderator
    user_role = current_user.get("role", "user")
    is_admin_or_moderator = user_role in ["admin", "moderator", "super_admin"]
    if not is_admin_or_moderator:
        raise AuthorizationError("需要管理员或审核员权限")

    try:
        app_logger.info(f"Get broadcast messages: user_id={current_user.get('id')}, page={page}, page_size={page_size}")

        # 验证参数
        if page_size <= 0 or page_size > 100:
            raise ValidationError("page_size必须在1-100之间")

        if page < 1:
            raise ValidationError("page必须大于等于1")

        # 使用服务层
        message_service = MessageService(db)

        # 获取广播消息
        messages = message_service.get_broadcast_messages(page=page, page_size=page_size)

        # 获取发送者信息
        sender_ids = list(set([msg.sender_id for msg in messages]))
        senders = {}
        if sender_ids:
            users = message_service.get_users_by_ids(sender_ids)
            for user in users:
                senders[user.id] = {"id": user.id, "username": user.username, "email": user.email}

        # 构建返回数据，包含统计信息
        result: List[Dict[str, Any]] = []
        for msg in messages:
            stats = message_service.get_broadcast_message_stats(message_id=msg.id)

            result.append(
                {
                    "id": msg.id,
                    "sender_id": msg.sender_id,
                    "sender": senders.get(msg.sender_id, {"id": msg.sender_id, "username": "未知用户", "email": ""}),
                    "title": msg.title,
                    "content": msg.content,
                    "message_type": msg.message_type,
                    "broadcast_scope": msg.broadcast_scope,
                    "created_at": msg.created_at.isoformat() if msg.created_at else "",
                    "stats": stats,
                }
            )

        total = message_service.count_broadcast_messages()

        return Page(message="广播消息历史获取成功", data=result, total=total, page=page, page_size=page_size)

    except (ValidationError, AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get broadcast messages error", exception=e)
        raise APIError("获取广播消息历史失败")
