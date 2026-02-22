"""
管理员路由模块

处理管理员相关的API端点，包括：
- 获取管理员统计数据
- 用户管理（查询、创建、更新角色、删除）
- 用户禁言/解除禁言
- 用户封禁/解除封禁
- 内容审核管理
"""

from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status as HTTPStatus, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc

from app.api.response_util import Success, Page
from app.core.database import get_db
from app.models.database import (
    User,
    KnowledgeBase,
    PersonaCard,
    UploadRecord,
    Message,
)
from app.core.error_handlers import ValidationError, NotFoundError, ConflictError, DatabaseError
from app.services.user_service import UserService

# 导入错误处理和日志记录模块
from app.core.logging import app_logger, log_exception, log_api_request, log_database_operation
from app.api.deps import get_current_user

# 创建路由器
router = APIRouter()


# 管理员相关路由（获取统计数据、用户管理、禁言、封禁等）
@router.get("/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取管理员统计数据（仅限admin）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    try:
        app_logger.info(f"Get admin stats: user_id={current_user.get('id')}")

        # 总用户数（只统计活跃用户）
        total_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0

        # 知识库数量（包括待审核）
        total_knowledge = db.query(func.count(KnowledgeBase.id)).scalar() or 0

        # 人格数量（包括待审核）
        total_personas = db.query(func.count(PersonaCard.id)).scalar() or 0

        # 待审核知识库数量
        pending_knowledge = (
            db.query(func.count(KnowledgeBase.id)).filter(KnowledgeBase.is_pending.is_(True)).scalar() or 0
        )

        # 待审核人格数量
        pending_personas = db.query(func.count(PersonaCard.id)).filter(PersonaCard.is_pending.is_(True)).scalar() or 0

        stats = {
            "totalUsers": total_users,
            "totalKnowledge": total_knowledge,
            "totalPersonas": total_personas,
            "pendingKnowledge": pending_knowledge,
            "pendingPersonas": pending_personas,
        }

        log_api_request(app_logger, "GET", "/api/admin/stats", current_user.get("id"), status_code=200)
        return Success(data=stats)

    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get admin stats error", exception=e)
        raise HTTPException(status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取统计数据失败: {str(e)}")


@router.get("/recent-users")
async def get_recent_users(
    page_size: int = 10, page: int = 1, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """获取最近注册的用户列表（仅限admin，支持分页）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    try:
        app_logger.info(f"Get recent users: user_id={current_user.get('id')}, page_size={page_size}, page={page}")

        # 限制page_size范围
        if page_size < 1 or page_size > 100:
            page_size = 10
        if page < 1:
            page = 1

        offset = (page - 1) * page_size
        users = (
            db.query(User)
            .filter(User.is_active.is_(True))
            .order_by(desc(User.created_at))
            .offset(offset)
            .limit(page_size)
            .all()
        )

        user_list = []
        for user in users:
            role = "admin" if user.is_admin else ("moderator" if user.is_moderator else "user")
            user_list.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": role,
                    "createdAt": user.created_at.isoformat() if user.created_at else None,
                }
            )

        # 统计总用户数
        total_users = db.query(User).count()

        log_api_request(app_logger, "GET", "/api/admin/recent-users", current_user.get("id"), status_code=200)
        return Page(
            data=user_list,
            page=page,
            page_size=page_size,
            total=total_users,
        )

    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get recent users error", exception=e)
        raise HTTPException(status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取最近用户失败: {str(e)}")


# 用户管理API
@router.get("/users")
async def get_all_users(
    page_size: int = 20,
    page: int = 1,
    search: Optional[str] = None,
    role: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取所有用户列表（仅限admin，支持分页、搜索、角色筛选）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    try:
        app_logger.info(
            f"Get all users: user_id={current_user.get('id')}, page={page}, page_size={page_size}, search={search}, role={role}"
        )

        # 限制参数范围
        if page_size < 1 or page_size > 100:
            page_size = 20
        if page < 1:
            page = 1

        # 构建查询 - 只查询活跃用户（过滤已删除的用户），并排除超级管理员
        query = db.query(User).filter(User.is_active.is_(True), User.is_super_admin.is_(False))

        # 搜索过滤（用户名或邮箱）
        if search:
            search_filter = or_(User.username.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
            query = query.filter(search_filter)

        # 角色过滤（此处 admin 仅包含普通管理员，不包含超级管理员）
        if role == "admin":
            query = query.filter(User.is_admin.is_(True))
        elif role == "moderator":
            query = query.filter(User.is_moderator.is_(True), User.is_admin.is_(False))
        elif role == "user":
            query = query.filter(User.is_moderator.is_(False), User.is_admin.is_(False))

        # 获取总数
        total = query.count()

        # 分页
        offset = (page - 1) * page_size
        users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

        user_ids = [user.id for user in users]

        last_upload_map = {}
        if user_ids:
            subquery = (
                db.query(
                    UploadRecord.uploader_id.label("uploader_id"),
                    func.max(UploadRecord.created_at).label("last_upload_at"),
                )
                .filter(UploadRecord.uploader_id.in_(user_ids))
                .group_by(UploadRecord.uploader_id)
                .subquery()
            )

            upload_rows = db.query(subquery.c.uploader_id, subquery.c.last_upload_at).all()
            for row in upload_rows:
                last_upload_map[row.uploader_id] = row.last_upload_at

        user_list = []
        for user in users:
            kb_count = db.query(func.count(KnowledgeBase.id)).filter(KnowledgeBase.uploader_id == user.id).scalar() or 0
            pc_count = db.query(func.count(PersonaCard.id)).filter(PersonaCard.uploader_id == user.id).scalar() or 0

            role_str = (
                "super_admin"
                if getattr(user, "is_super_admin", False)
                else ("admin" if user.is_admin else ("moderator" if user.is_moderator else "user"))
            )
            last_upload_at = last_upload_map.get(user.id)

            user_list.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": role_str,
                    "is_active": user.is_active,
                    "createdAt": user.created_at.isoformat() if user.created_at else None,
                    "knowledgeCount": kb_count,
                    "personaCount": pc_count,
                    "lastUploadAt": last_upload_at.isoformat() if last_upload_at else None,
                    "lastLoginAt": None,
                    "lockedUntil": user.locked_until.isoformat() if user.locked_until else None,
                    "isMuted": user.is_muted,
                    "mutedUntil": user.muted_until.isoformat() if user.muted_until else None,
                    "banReason": getattr(user, "ban_reason", None),
                    "muteReason": getattr(user, "mute_reason", None),
                }
            )

        log_api_request(app_logger, "GET", "/api/admin/users", current_user.get("id"), status_code=200)
        return Page(
            data=user_list,
            page=page,
            page_size=page_size,
            total=total,
        )

    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get all users error", exception=e)
        raise HTTPException(status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取用户列表失败: {str(e)}")


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_data: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新用户角色（仅限admin）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    try:
        app_logger.info(
            f"Update user role: user_id={user_id}, new_role={role_data.get('role')}, operator={current_user.get('id')}"
        )

        new_role = role_data.get("role")
        if new_role not in ["user", "moderator", "admin"]:
            raise ValidationError("角色必须是 user、moderator 或 admin")

        # 不能修改自己的角色
        if user_id == current_user.get("id"):
            raise ValidationError("不能修改自己的角色")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError("用户不存在")

        # 管理员不能操作其它管理员账号，仅超级管理员可以调整管理员角色
        is_target_admin_like = bool(getattr(user, "is_admin", False) or getattr(user, "is_super_admin", False))
        is_operator_super_admin = bool(current_user.get("is_super_admin", False))
        if is_target_admin_like and not is_operator_super_admin:
            raise ValidationError("只有超级管理员可以修改管理员或超级管理员的角色")

        # 只有超级管理员可以将用户提升为管理员
        if new_role == "admin" and not is_operator_super_admin:
            raise ValidationError("只有超级管理员可以任命管理员")

        # 检查是否是最后一个管理员（只统计活跃管理员，不含超级管理员）
        if user.is_admin and new_role != "admin":
            admin_count = (
                db.query(func.count(User.id)).filter(User.is_admin.is_(True), User.is_active.is_(True)).scalar() or 0
            )
            if admin_count <= 1:
                raise ValidationError("不能删除最后一个管理员")

        # 更新角色
        user.is_admin = new_role == "admin"
        user.is_moderator = new_role == "moderator"
        username = user.username
        db.commit()

        log_database_operation(
            app_logger, "update", "user_role", record_id=user_id, user_id=current_user.get("id"), success=True
        )

        log_api_request(app_logger, "PUT", f"/api/admin/users/{user_id}/role", current_user.get("id"), status_code=200)
        return Success(message="用户角色更新成功", data={"id": user_id, "username": username, "role": new_role})

    except (ValidationError, NotFoundError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Update user role error", exception=e)
        raise HTTPException(status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"更新用户角色失败: {str(e)}")


@router.post("/users/{user_id}/mute")
async def mute_user(
    user_id: str, body: dict = Body(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """禁言用户（仅限admin）"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    try:
        duration = body.get("duration", "7d")
        reason = (body.get("reason") or "").strip()

        app_logger.info(
            f"禁言用户: user_id={user_id}, duration={duration}, reason={reason}, operator={current_user.get('id')}"
        )

        now = datetime.now()
        if duration == "1d":
            muted_until = now + timedelta(days=1)
        elif duration == "7d":
            muted_until = now + timedelta(days=7)
        elif duration == "30d":
            muted_until = now + timedelta(days=30)
        elif duration == "permanent":
            muted_until = None
        else:
            raise ValidationError("禁言时长无效")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError("用户不存在")

        if user.id == current_user.get("id"):
            raise ValidationError("不能对自己进行禁言操作")

        # 管理员不能操作其它管理员账号，仅超级管理员可以对管理员禁言
        is_target_admin_like = bool(getattr(user, "is_admin", False) or getattr(user, "is_super_admin", False))
        if is_target_admin_like and not current_user.get("is_super_admin", False):
            raise ValidationError("管理员不能对其它管理员或超级管理员进行禁言操作")

        user.is_muted = True
        user.muted_until = muted_until
        user.mute_reason = reason or None
        db.commit()

        # 发送禁言站内信（尽量不影响主流程）
        try:
            operator_id = current_user.get("id", "")
            muted_until_text = "永久禁言" if muted_until is None else muted_until.strftime("%Y-%m-%d %H:%M")
            reason_text = reason or "违反社区行为规范"
            content = (
                "你好，你的账号已被禁言。\n\n"
                f"禁言时长：{muted_until_text}\n"
                f"禁言原因：{reason_text}\n\n"
                "在禁言期间，你将无法在站内发表评论和回复内容。\n"
                "如有疑问，可以联系管理员。\n\n"
                "—— 麦麦"
            )
            message = Message(
                sender_id=str(operator_id),
                recipient_id=str(user_id),
                title="禁言通知",
                content=content,
                message_type="announcement",
                summary=None,
            )
            db.add(message)
            db.commit()
        except Exception as e:
            app_logger.warning(f"Failed to send mute notification message: {str(e)}")

        return Success(
            message="用户禁言成功",
            data={
                "userId": user_id,
                "isMuted": True,
                "mutedUntil": muted_until.isoformat() if muted_until else None,
                "muteReason": reason or "",
            },
        )
    except (ValidationError, NotFoundError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Mute user error", exception=e)
        raise HTTPException(status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"禁言用户失败: {str(e)}")


@router.post("/users/{user_id}/unmute")
async def unmute_user(user_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """解除禁言（仅限admin）"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    try:
        app_logger.info(f"解除禁言: user_id={user_id}, operator={current_user.get('id')}")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError("用户不存在")

        # 管理员不能操作其它管理员账号，仅超级管理员可以解除管理员禁言
        is_target_admin_like = bool(getattr(user, "is_admin", False) or getattr(user, "is_super_admin", False))
        if is_target_admin_like and not current_user.get("is_super_admin", False):
            raise ValidationError("管理员不能对其它管理员或超级管理员进行禁言操作")

        user.is_muted = False
        user.muted_until = None
        user.mute_reason = None
        db.commit()

        # 发送解除禁言站内信
        try:
            operator_id = current_user.get("id", "")
            content = (
                "你好，你的账号禁言状态已解除。\n\n"
                "现在你可以正常在站内发表评论和回复内容。\n"
                "请遵守社区行为规范，避免再次被禁言。\n\n"
                "—— 麦麦"
            )
            message = Message(
                sender_id=str(operator_id),
                recipient_id=str(user_id),
                title="禁言解除通知",
                content=content,
                message_type="announcement",
                summary=None,
            )
            db.add(message)
            db.commit()
        except Exception as e:
            app_logger.warning(f"Failed to send unmute notification message: {str(e)}")

        return Success(message="用户已解除禁言", data={"userId": user_id, "isMuted": False, "mutedUntil": None})
    except NotFoundError as e:
        raise HTTPException(status_code=HTTPStatus.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        log_exception(app_logger, "Unmute user error", exception=e)
        raise HTTPException(status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"解除禁言失败: {str(e)}")


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除用户（仅限admin，软删除）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    try:
        app_logger.info(f"Delete user: user_id={user_id}, operator={current_user.get('id')}")

        # 不能删除自己
        if user_id == current_user.get("id"):
            raise ValidationError("不能删除自己")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError("用户不存在")

        # 管理员不能删除其它管理员账号，仅超级管理员可以删除管理员
        is_target_admin_like = bool(getattr(user, "is_admin", False) or getattr(user, "is_super_admin", False))
        if is_target_admin_like and not current_user.get("is_super_admin", False):
            raise ValidationError("管理员不能删除其它管理员或超级管理员账号")

        # 检查是否是最后一个管理员（只统计活跃管理员）
        if user.is_admin:
            admin_count = (
                db.query(func.count(User.id)).filter(User.is_admin.is_(True), User.is_active.is_(True)).scalar() or 0
            )
            if admin_count <= 1:
                raise ValidationError("不能删除最后一个管理员")

        # 软删除：标记为不活跃
        user.is_active = False
        db.commit()

        log_database_operation(
            app_logger, "delete", "user", record_id=user_id, user_id=current_user.get("id"), success=True
        )

        log_api_request(app_logger, "DELETE", f"/api/admin/users/{user_id}", current_user.get("id"), status_code=200)
        return Success(message="用户删除成功")

    except (ValidationError, NotFoundError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Delete user error", exception=e)
        raise HTTPException(status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除用户失败: {str(e)}")


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str, body: dict = Body(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """封禁用户（仅限admin），支持按时长封禁"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    try:
        duration = body.get("duration", "permanent")
        reason = (body.get("reason") or "").strip()
        app_logger.info(
            f"Ban user: user_id={user_id}, duration={duration}, reason={reason}, operator={current_user.get('id')}"
        )

        if user_id == current_user.get("id"):
            raise ValidationError("不能封禁自己")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError("用户不存在")

        # 管理员不能封禁其它管理员账号，仅超级管理员可以封禁管理员
        is_target_admin_like = bool(getattr(user, "is_admin", False) or getattr(user, "is_super_admin", False))
        if is_target_admin_like and not current_user.get("is_super_admin", False):
            raise ValidationError("管理员不能封禁其它管理员或超级管理员账号")

        # 计算封禁截止时间
        now = datetime.now()
        if duration == "1d":
            locked_until = now + timedelta(days=1)
        elif duration == "7d":
            locked_until = now + timedelta(days=7)
        elif duration == "30d":
            locked_until = now + timedelta(days=30)
        elif duration == "permanent":
            locked_until = now + timedelta(days=365 * 100)
        else:
            raise ValidationError("封禁时长无效")

        # 检查是否是最后一个管理员（只统计未被永久封禁的活跃管理员）
        if user.is_admin:
            admin_query = db.query(func.count(User.id)).filter(User.is_admin.is_(True), User.is_active.is_(True))
            # 只统计未被永久封禁（locked_until 为空或已经过期）的管理员
            admin_query = admin_query.filter((User.locked_until == None) | (User.locked_until <= now))  # noqa: E711
            admin_count = admin_query.scalar() or 0
            if admin_count <= 1:
                raise ValidationError("不能封禁最后一个管理员")

        user.locked_until = locked_until
        user.ban_reason = reason or None
        db.commit()

        log_database_operation(
            app_logger, "update", "user", record_id=user_id, user_id=current_user.get("id"), success=True
        )

        # 发送封禁站内信
        try:
            operator_id = current_user.get("id", "")
            if duration == "permanent":
                locked_text = "永久封禁"
            else:
                locked_text = locked_until.strftime("%Y-%m-%d %H:%M")
            reason_text = reason or "违反社区行为规范"
            content = (
                "你好，你的账号已被封禁，暂时无法登录系统。\n\n"
                f"封禁时长：{locked_text}\n"
                f"封禁原因：{reason_text}\n\n"
                "在封禁期间，你将无法登录并使用站内功能。\n"
                "如有疑问，可以联系管理员。\n\n"
                "—— 麦麦"
            )
            message = Message(
                sender_id=str(operator_id),
                recipient_id=str(user_id),
                title="封禁通知",
                content=content,
                message_type="announcement",
                summary=None,
            )
            db.add(message)
            db.commit()
        except Exception as e:
            app_logger.warning(f"Failed to send ban notification message: {str(e)}")

        log_api_request(app_logger, "POST", f"/api/admin/users/{user_id}/ban", current_user.get("id"), status_code=200)
        return Success(
            message="用户封禁成功", data={"locked_until": locked_until.isoformat(), "ban_reason": reason or ""}
        )

    except (ValidationError, NotFoundError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Ban user error", exception=e)
        raise HTTPException(status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"封禁用户失败: {str(e)}")


@router.post("/users/{user_id}/unban")
async def unban_user(user_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """解封用户（仅限admin）"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    try:
        app_logger.info(f"Unban user: user_id={user_id}, operator={current_user.get('id')}")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError("用户不存在")

        # 管理员不能解封其它管理员账号，仅超级管理员可以解封管理员
        is_target_admin_like = bool(getattr(user, "is_admin", False) or getattr(user, "is_super_admin", False))
        if is_target_admin_like and not current_user.get("is_super_admin", False):
            raise ValidationError("管理员不能解封其它管理员或超级管理员账号")

        user.locked_until = None
        user.failed_login_attempts = 0
        user.ban_reason = None
        db.commit()

        log_database_operation(
            app_logger, "update", "user", record_id=user_id, user_id=current_user.get("id"), success=True
        )

        # 发送解封站内信
        try:
            operator_id = current_user.get("id", "")
            content = (
                "你好，你的账号封禁状态已解除。\n\n"
                "现在你可以重新登录并正常使用站内功能。\n"
                "请遵守社区行为规范，避免再次被封禁。\n\n"
                "—— 麦麦"
            )
            message = Message(
                sender_id=str(operator_id),
                recipient_id=str(user_id),
                title="解封通知",
                content=content,
                message_type="announcement",
                summary=None,
            )
            db.add(message)
            db.commit()
        except Exception as e:
            app_logger.warning(f"Failed to send unban notification message: {str(e)}")

        log_api_request(
            app_logger, "POST", f"/api/admin/users/{user_id}/unban", current_user.get("id"), status_code=200
        )
        return Success(message="用户已解封")

    except (ValidationError, NotFoundError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Unban user error", exception=e)
        raise HTTPException(status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"解封用户失败: {str(e)}")


@router.post("/users")
async def create_user_by_admin(
    user_data: dict = Body(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """创建新用户（仅限admin）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=HTTPStatus.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    try:
        app_logger.info(
            f"Create user by admin: operator={current_user.get('id')}, username={user_data.get('username')}"
        )

        username = user_data.get("username", "").strip()
        email = user_data.get("email", "").strip().lower()
        password = user_data.get("password", "")
        role = user_data.get("role", "user")

        # 验证输入
        if not username:
            raise ValidationError("用户名不能为空")
        if not email:
            raise ValidationError("邮箱不能为空")
        if not password:
            raise ValidationError("密码不能为空")
        if role not in ["user", "moderator", "admin"]:
            raise ValidationError("角色必须是 user、moderator 或 admin")

        # 只有超级管理员可以创建管理员账号
        if role == "admin" and not current_user.get("is_super_admin", False):
            raise ValidationError("只有超级管理员可以创建管理员账号")

        # 验证密码强度（至少8位，包含字母和数字）
        if len(password) < 8:
            raise ValidationError("密码长度至少8位")
        if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            raise ValidationError("密码必须包含字母和数字")

        # 使用 UserService 创建用户
        user_service = UserService(db)

        # 检查用户名和邮箱唯一性
        if user_service.get_user_by_username(username):
            raise ConflictError("用户名已存在")
        if user_service.get_user_by_email(email):
            raise ConflictError("邮箱已存在")

        # 创建用户
        new_user = user_service.create_user(
            username=username,
            email=email,
            password=password,
            is_admin=(role == "admin"),
            is_moderator=(role == "moderator"),
        )

        if not new_user:
            raise DatabaseError("创建用户失败")

        log_database_operation(
            app_logger, "create", "user", record_id=new_user.id, user_id=current_user.get("id"), success=True
        )

        log_api_request(app_logger, "POST", "/api/admin/users", current_user.get("id"), status_code=200)
        return Success(
            message="用户创建成功",
            data={"id": new_user.id, "username": new_user.username, "email": new_user.email, "role": role},
        )

    except (ValidationError, ConflictError, DatabaseError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Create user by admin error", exception=e)
        raise HTTPException(status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建用户失败: {str(e)}")
