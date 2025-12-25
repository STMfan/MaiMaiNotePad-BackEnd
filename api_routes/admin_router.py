from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from typing import List, Optional, Dict, Any

from database_models import sqlite_db_manager
from user_management import get_current_user

# 导入错误处理和日志记录模块
from logging_config import app_logger, log_exception, log_api_request, log_database_operation
from error_handlers import (
    APIError, ValidationError, NotFoundError, ConflictError, DatabaseError
)
from api_routes.response_util import Success, Page

# 创建路由器
admin_router = APIRouter()

# 使用SQLite数据库管理器
db_manager = sqlite_db_manager


# 管理员相关路由
@admin_router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """获取管理员统计数据（仅限admin）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    try:
        app_logger.info(f"Get admin stats: user_id={current_user.get('id')}")

        # 查询统计数据
        with db_manager.get_session() as session:
            from sqlalchemy import func
            from database_models import User, KnowledgeBase, PersonaCard

            # 总用户数（只统计活跃用户）
            total_users = session.query(func.count(User.id)).filter(
                User.is_active == True).scalar() or 0

            # 知识库数量（包括待审核）
            total_knowledge = session.query(
                func.count(KnowledgeBase.id)).scalar() or 0

            # 人格数量（包括待审核）
            total_personas = session.query(
                func.count(PersonaCard.id)).scalar() or 0

            # 待审核知识库数量
            pending_knowledge = session.query(func.count(KnowledgeBase.id)).filter(
                KnowledgeBase.is_pending == True
            ).scalar() or 0

            # 待审核人格数量
            pending_personas = session.query(func.count(PersonaCard.id)).filter(
                PersonaCard.is_pending == True
            ).scalar() or 0

        stats = {
            "totalUsers": total_users,
            "totalKnowledge": total_knowledge,
            "totalPersonas": total_personas,
            "pendingKnowledge": pending_knowledge,
            "pendingPersonas": pending_personas
        }

        log_api_request(app_logger, "GET", "/admin/stats",
                        current_user.get("id"), status_code=200)
        return Success(data=stats)

    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get admin stats error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计数据失败: {str(e)}"
        )


@admin_router.get("/admin/recent-users")
async def get_recent_users(
        page_size: int = 10,
        page: int = 1,
        current_user: dict = Depends(get_current_user)
):
    """获取最近注册的用户列表（仅限admin，支持分页）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    try:
        app_logger.info(
            f"Get recent users: user_id={current_user.get('id')}, page_size={page_size}, page={page}")

        # 限制page_size范围
        if page_size < 1 or page_size > 100:
            page_size = 10
        if page < 1:
            page = 1

        with db_manager.get_session() as session:
            from database_models import User
            from sqlalchemy import desc

            offset = (page - 1) * page_size
            users = session.query(User).filter(
                User.is_active == True
            ).order_by(
                desc(User.created_at)
            ).offset(offset).limit(page_size).all()

            user_list = []
            for user in users:
                role = "admin" if user.is_admin else (
                    "moderator" if user.is_moderator else "user")
                user_list.append({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": role,
                    "createdAt": user.created_at.isoformat() if user.created_at else None
                })

        # 统计总用户数
        with db_manager.get_session() as session:
            total_users = session.query(User).count()

        log_api_request(app_logger, "GET", "/admin/recent-users",
                        current_user.get("id"), status_code=200)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取最近用户失败: {str(e)}"
        )


# 用户管理API
@admin_router.get("/admin/users")
async def get_all_users(
        page_size: int = 20,
        page: int = 1,
        search: Optional[str] = None,
        role: Optional[str] = None,
        current_user: dict = Depends(get_current_user)
):
    """获取所有用户列表（仅限admin，支持分页、搜索、角色筛选）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    try:
        app_logger.info(
            f"Get all users: user_id={current_user.get('id')}, page={page}, page_size={page_size}, search={search}, role={role}")

        # 限制参数范围
        if page_size < 1 or page_size > 100:
            page_size = 20
        if page < 1:
            page = 1

        with db_manager.get_session() as session:
            from database_models import User, KnowledgeBase, PersonaCard
            from sqlalchemy import func, or_, and_

            # 构建查询 - 只查询活跃用户（过滤已删除的用户）
            query = session.query(User).filter(User.is_active == True)

            # 搜索过滤（用户名或邮箱）
            if search:
                search_filter = or_(
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
                query = query.filter(search_filter)

            # 角色过滤
            if role == "admin":
                query = query.filter(User.is_admin == True)
            elif role == "moderator":
                query = query.filter(User.is_moderator ==
                                     True, User.is_admin == False)
            elif role == "user":
                query = query.filter(User.is_moderator ==
                                     False, User.is_admin == False)

            # 获取总数
            total = query.count()

            # 分页
            offset = (page - 1) * page_size
            users = query.order_by(User.created_at.desc()).offset(
                offset).limit(page_size).all()

            # 构建用户列表
            user_list = []
            for user in users:
                # 统计用户的知识库和人设卡数量
                kb_count = session.query(func.count(KnowledgeBase.id)).filter(
                    KnowledgeBase.uploader_id == user.id
                ).scalar() or 0
                pc_count = session.query(func.count(PersonaCard.id)).filter(
                    PersonaCard.uploader_id == user.id
                ).scalar() or 0

                role_str = "admin" if user.is_admin else (
                    "moderator" if user.is_moderator else "user")
                user_list.append({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": role_str,
                    "is_active": user.is_active,
                    "createdAt": user.created_at.isoformat() if user.created_at else None,
                    "knowledgeCount": kb_count,
                    "personaCount": pc_count
                })

        log_api_request(app_logger, "GET", "/admin/users",
                        current_user.get("id"), status_code=200)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户列表失败: {str(e)}"
        )


@admin_router.put("/admin/users/{user_id}/role")
async def update_user_role(
        user_id: str,
        role_data: dict = Body(...),
        current_user: dict = Depends(get_current_user)
):
    """更新用户角色（仅限admin）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    try:
        app_logger.info(
            f"Update user role: user_id={user_id}, new_role={role_data.get('role')}, operator={current_user.get('id')}")

        new_role = role_data.get("role")
        if new_role not in ["user", "moderator", "admin"]:
            raise ValidationError("角色必须是 user、moderator 或 admin")

        # 不能修改自己的角色
        if user_id == current_user.get("id"):
            raise ValidationError("不能修改自己的角色")

        with db_manager.get_session() as session:
            from database_models import User
            from sqlalchemy import func

            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise NotFoundError("用户不存在")

            # 检查是否是最后一个管理员（只统计活跃管理员）
            if user.is_admin and new_role != "admin":
                admin_count = session.query(func.count(User.id)).filter(
                    User.is_admin == True,
                    User.is_active == True
                ).scalar() or 0
                if admin_count <= 1:
                    raise ValidationError("不能删除最后一个管理员")

            # 更新角色
            user.is_admin = (new_role == "admin")
            user.is_moderator = (new_role == "moderator")
            session.commit()

            log_database_operation(
                app_logger,
                "update",
                "user_role",
                record_id=user_id,
                user_id=current_user.get("id"),
                success=True
            )

        log_api_request(
            app_logger, "PUT", f"/admin/users/{user_id}/role", current_user.get("id"), status_code=200)
        return Success(
            message="用户角色更新成功",
            data={
                "id": user_id,
                "username": user.username,
                "role": new_role
            }
        )

    except (ValidationError, NotFoundError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Update user role error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户角色失败: {str(e)}"
        )


@admin_router.delete("/admin/users/{user_id}")
async def delete_user(
        user_id: str,
        current_user: dict = Depends(get_current_user)
):
    """删除用户（仅限admin，软删除）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    try:
        app_logger.info(
            f"Delete user: user_id={user_id}, operator={current_user.get('id')}")

        # 不能删除自己
        if user_id == current_user.get("id"):
            raise ValidationError("不能删除自己")

        with db_manager.get_session() as session:
            from database_models import User
            from sqlalchemy import func

            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise NotFoundError("用户不存在")

            # 检查是否是最后一个管理员（只统计活跃管理员）
            if user.is_admin:
                admin_count = session.query(func.count(User.id)).filter(
                    User.is_admin == True,
                    User.is_active == True
                ).scalar() or 0
                if admin_count <= 1:
                    raise ValidationError("不能删除最后一个管理员")

            # 软删除：标记为不活跃
            user.is_active = False
            session.commit()

            log_database_operation(
                app_logger,
                "delete",
                "user",
                record_id=user_id,
                user_id=current_user.get("id"),
                success=True
            )

        log_api_request(app_logger, "DELETE",
                        f"/admin/users/{user_id}", current_user.get("id"), status_code=200)
        return Success(
            message="用户删除成功"
        )

    except (ValidationError, NotFoundError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Delete user error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除用户失败: {str(e)}"
        )


@admin_router.post("/admin/users")
async def create_user_by_admin(
        user_data: dict = Body(...),
        current_user: dict = Depends(get_current_user)
):
    """创建新用户（仅限admin）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    try:
        app_logger.info(
            f"Create user by admin: operator={current_user.get('id')}, username={user_data.get('username')}")

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

        # 验证密码强度（至少8位，包含字母和数字）
        if len(password) < 8:
            raise ValidationError("密码长度至少8位")
        if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            raise ValidationError("密码必须包含字母和数字")

        # 检查用户名和邮箱唯一性
        legality = db_manager.check_user_register_legality(username, email)
        if legality != "ok":
            raise ConflictError(legality)

        # 创建用户
        from user_management import create_user
        new_user = create_user(username, password, email, role)

        if not new_user:
            raise DatabaseError("创建用户失败")

        # 设置角色
        with db_manager.get_session() as session:
            from database_models import User
            user = session.query(User).filter(
                User.id == new_user.userID).first()
            if user:
                user.is_admin = (role == "admin")
                user.is_moderator = (role == "moderator")
                session.commit()

        log_database_operation(
            app_logger,
            "create",
            "user",
            record_id=new_user.userID,
            user_id=current_user.get("id"),
            success=True
        )

        log_api_request(app_logger, "POST", "/admin/users",
                        current_user.get("id"), status_code=200)
        return Success(
            message="用户创建成功",
            data={
                "id": new_user.userID,
                "username": new_user.username,
                "email": new_user.email,
                "role": role
            }
        )

    except (ValidationError, ConflictError, DatabaseError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Create user by admin error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建用户失败: {str(e)}"
        )


# 内容管理API
@admin_router.get("/admin/knowledge/all")
async def get_all_knowledge_bases_admin(
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        uploader: Optional[str] = Query(
            None,
            description="上传者ID或用户名（支持模糊匹配）"
        ),
        order_by: Optional[str] = Query(
            "created_at",
            description="排序字段，支持 created_at、updated_at、star_count、name、downloads、is_public"
        ),
        order_dir: Optional[str] = Query(
            "desc",
            description="排序方向 asc/desc，默认 desc"
        ),
        current_user: dict = Depends(get_current_user)
):
    """获取所有知识库（管理员视图，仅限admin）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    try:
        app_logger.info(
            f"Get all knowledge bases (admin): user_id={current_user.get('id')}, page={page}, page_size={page_size}, status={status}, search={search}")

        # 限制参数范围
        if page_size < 1 or page_size > 100:
            page_size = 20
        if page < 1:
            page = 1

        with db_manager.get_session() as session:
            from database_models import KnowledgeBase, User
            from sqlalchemy import func, or_, and_

            # 构建查询
            query = session.query(KnowledgeBase)

            # 状态过滤
            if status == "pending":
                query = query.filter(KnowledgeBase.is_pending == True)
            elif status == "approved":
                query = query.filter(
                    KnowledgeBase.is_pending == False, KnowledgeBase.rejection_reason == None)
            elif status == "rejected":
                query = query.filter(
                    KnowledgeBase.is_pending == False, KnowledgeBase.rejection_reason != None)

            # 搜索过滤（名称或描述）
            if search:
                search_filter = or_(
                    KnowledgeBase.name.ilike(f"%{search}%"),
                    KnowledgeBase.description.ilike(f"%{search}%")
                )
                query = query.filter(search_filter)

            # 获取总数
            total = query.count()

            # 分页
            offset = (page - 1) * page_size
            knowledge_bases = query.order_by(
                KnowledgeBase.created_at.desc()).offset(offset).limit(page_size).all()

            # 获取上传者信息
            uploader_ids = list(
                set([kb.uploader_id for kb in knowledge_bases]))
            uploaders = {}
            if uploader_ids:
                users = db_manager.get_users_by_ids(uploader_ids)
                for user in users:
                    uploaders[user.id] = user.username

            # 构建知识库列表
            kb_list = []
            for kb in knowledge_bases:
                # 确定状态
                if kb.is_pending:
                    status_str = "pending"
                elif kb.rejection_reason:
                    status_str = "rejected"
                else:
                    status_str = "approved"

                kb_list.append({
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description,
                    "uploader_id": kb.uploader_id,
                    "uploader_name": uploaders.get(kb.uploader_id, "未知用户"),
                    "status": status_str,
                    "is_public": kb.is_public,
                    "star_count": kb.star_count,
                    "createdAt": kb.created_at.isoformat() if kb.created_at else None
                })

        log_api_request(app_logger, "GET", "/admin/knowledge/all",
                        current_user.get("id"), status_code=200)
        return Page(
            data = kb_list,
            page = page,
            page_size = page_size,
            total = total,
        )

    except HTTPException:
        raise
    except Exception as e:
        log_exception(
            app_logger, "Get all knowledge bases (admin) error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库列表失败: {str(e)}"
        )


@admin_router.get("/admin/persona/all")
async def get_all_personas_admin(
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        uploader: Optional[str] = Query(
            None,
            description="上传者ID或用户名（支持模糊匹配）"
        ),
        order_by: Optional[str] = Query(
            "created_at",
            description="排序字段，支持 created_at、updated_at、star_count、name、downloads、is_public"
        ),
        order_dir: Optional[str] = Query(
            "desc",
            description="排序方向 asc/desc，默认 desc"
        ),
        current_user: dict = Depends(get_current_user)
):
    """获取所有人设卡（管理员视图，仅限admin）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    try:
        app_logger.info(
            f"Get all personas (admin): user_id={current_user.get('id')}, page={page}, page_size={page_size}, status={status}, search={search}")

        # 限制参数范围
        if page_size < 1 or page_size > 100:
            page_size = 20
        if page < 1:
            page = 1

        with db_manager.get_session() as session:
            from database_models import PersonaCard, User
            from sqlalchemy import func, or_, and_

            # 构建查询
            query = session.query(PersonaCard)

            # 状态过滤
            if status == "pending":
                query = query.filter(PersonaCard.is_pending == True)
            elif status == "approved":
                query = query.filter(
                    PersonaCard.is_pending == False, PersonaCard.rejection_reason == None)
            elif status == "rejected":
                query = query.filter(
                    PersonaCard.is_pending == False, PersonaCard.rejection_reason != None)

            # 搜索过滤（名称或描述）
            if search:
                search_filter = or_(
                    PersonaCard.name.ilike(f"%{search}%"),
                    PersonaCard.description.ilike(f"%{search}%")
                )
                query = query.filter(search_filter)

            # 获取总数
            total = query.count()

            # 分页
            offset = (page - 1) * page_size
            persona_cards = query.order_by(
                PersonaCard.created_at.desc()).offset(offset).limit(page_size).all()

            # 获取上传者信息
            uploader_ids = list(set([pc.uploader_id for pc in persona_cards]))
            uploaders = {}
            if uploader_ids:
                users = db_manager.get_users_by_ids(uploader_ids)
                for user in users:
                    uploaders[user.id] = user.username

            # 构建人设卡列表
            pc_list = []
            for pc in persona_cards:
                # 确定状态
                if pc.is_pending:
                    status_str = "pending"
                elif pc.rejection_reason:
                    status_str = "rejected"
                else:
                    status_str = "approved"

                pc_list.append({
                    "id": pc.id,
                    "name": pc.name,
                    "description": pc.description,
                    "uploader_id": pc.uploader_id,
                    "uploader_name": uploaders.get(pc.uploader_id, "未知用户"),
                    "status": status_str,
                    "is_public": pc.is_public,
                    "star_count": pc.star_count,
                    "createdAt": pc.created_at.isoformat() if pc.created_at else None
                })

        log_api_request(app_logger, "GET", "/admin/persona/all",
                        current_user.get("id"), status_code=200)
        return Page(
            data=pc_list,
            page=page,
            page_size=page_size,
            total=total,
            message="获取人设卡列表成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        log_exception(
            app_logger, "Get all personas (admin) error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取人设卡列表失败: {str(e)}"
        )


@admin_router.post("/admin/knowledge/{kb_id}/revert")
async def revert_knowledge_base(
        kb_id: str,
        reason_data: Optional[dict] = Body(None),
        current_user: dict = Depends(get_current_user)
):
    """退回知识库（将已审核通过的知识库退回为待审核状态，仅限admin）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    try:
        app_logger.info(
            f"Revert knowledge base: kb_id={kb_id}, operator={current_user.get('id')}")

        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 只能退回已审核通过的内容
        if kb.is_pending:
            raise ValidationError("该知识库已经是待审核状态")
        if kb.rejection_reason:
            raise ValidationError("不能退回已拒绝的知识库")

        # 更新状态为待审核
        kb.is_pending = True
        kb.rejection_reason = None  # 清除之前的拒绝原因

        reason = reason_data.get("reason", "") if reason_data else ""
        if reason:
            # 可选：记录退回原因（可以存储在某个字段中，这里暂时不存储）
            app_logger.info(f"Revert reason: {reason}")

        updated_kb = db_manager.save_knowledge_base(kb.to_dict())
        if not updated_kb:
            raise DatabaseError("更新知识库状态失败")

        # 更新上传记录状态
        try:
            db_manager.update_upload_record_status(kb_id, "pending")
        except Exception as e:
            app_logger.warning(
                f"Failed to update upload record status: {str(e)}")

        # 发送通知给上传者（可选）
        try:
            from models import Message
            message = Message(
                recipient_id=kb.uploader_id,
                sender_id=current_user.get("id", ""),
                title="知识库已退回待审核",
                content=f"您上传的知识库《{kb.name}》已被退回待审核状态，请等待重新审核。\n\n退回原因：{reason if reason else '无'}"
            )
            db_manager.create_message(message.to_dict())
        except Exception as e:
            app_logger.warning(f"Failed to send notification: {str(e)}")

        log_database_operation(
            app_logger,
            "update",
            "knowledge_base_revert",
            record_id=kb_id,
            user_id=current_user.get("id"),
            success=True
        )

        log_api_request(
            app_logger, "POST", f"/admin/knowledge/{kb_id}/revert", current_user.get("id"), status_code=200)
        return Success(
            message="知识库已退回待审核"
        )

    except (ValidationError, NotFoundError, DatabaseError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Revert knowledge base error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"退回知识库失败: {str(e)}"
        )


@admin_router.post("/admin/persona/{pc_id}/revert")
async def revert_persona_card(
        pc_id: str,
        reason_data: Optional[dict] = Body(None),
        current_user: dict = Depends(get_current_user)
):
    """退回人设卡（将已审核通过的人设卡退回为待审核状态，仅限admin）"""
    # 验证权限：仅admin
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    try:
        app_logger.info(
            f"Revert persona card: pc_id={pc_id}, operator={current_user.get('id')}")

        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 只能退回已审核通过的内容
        if pc.is_pending:
            raise ValidationError("该人设卡已经是待审核状态")
        if pc.rejection_reason:
            raise ValidationError("不能退回已拒绝的人设卡")

        # 更新状态为待审核
        pc.is_pending = True
        pc.rejection_reason = None  # 清除之前的拒绝原因

        reason = reason_data.get("reason", "") if reason_data else ""
        if reason:
            app_logger.info(f"Revert reason: {reason}")

        updated_pc = db_manager.save_persona_card(pc.to_dict())
        if not updated_pc:
            raise DatabaseError("更新人设卡状态失败")

        # 更新上传记录状态
        try:
            db_manager.update_upload_record_status(pc_id, "pending")
        except Exception as e:
            app_logger.warning(
                f"Failed to update upload record status: {str(e)}")

        # 发送通知给上传者（可选）
        try:
            from models import Message
            message = Message(
                recipient_id=pc.uploader_id,
                sender_id=current_user.get("id", ""),
                title="人设卡已退回待审核",
                content=f"您上传的人设卡《{pc.name}》已被退回待审核状态，请等待重新审核。\n\n退回原因：{reason if reason else '无'}"
            )
            db_manager.create_message(message.to_dict())
        except Exception as e:
            app_logger.warning(f"Failed to send notification: {str(e)}")

        log_database_operation(
            app_logger,
            "update",
            "persona_card_revert",
            record_id=pc_id,
            user_id=current_user.get("id"),
            success=True
        )

        log_api_request(
            app_logger, "POST", f"/admin/persona/{pc_id}/revert", current_user.get("id"), status_code=200)
        return Success(
            message="人设卡已退回待审核"
        )

    except (ValidationError, NotFoundError, DatabaseError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Revert persona card error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"退回人设卡失败: {str(e)}"
        )


@admin_router.get("/admin/upload-history")
async def get_upload_history(
        page: int = 1,
        page_size: int = 20,
        current_user: dict = Depends(get_current_user)
):
    """获取上传历史记录（admin和moderator权限，支持分页）"""
    # 验证权限：admin或moderator
    if not (current_user.get("is_admin", False) or current_user.get("is_moderator", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员或审核员权限"
        )

    try:
        app_logger.info(
            f"Get upload history: user_id={current_user.get('id')}, page={page}, page_size={page_size}")

        # 限制参数范围
        if page_size < 1 or page_size > 100:
            page_size = 20
        if page < 1:
            page = 1

        # 获取上传记录
        upload_records = db_manager.get_all_upload_records(
            page=page, page_size=page_size)

        total=len(upload_records)

        # 获取上传者信息
        uploader_ids = list(
            set([record.uploader_id for record in upload_records]))
        uploaders = {}
        if uploader_ids:
            users = db_manager.get_users_by_ids(uploader_ids)
            for user in users:
                uploaders[user.id] = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }

        # 构建返回数据
        history_list = []
        for record in upload_records:
            uploader_info = uploaders.get(record.uploader_id, {
                "id": record.uploader_id,
                "username": "未知用户",
                "email": ""
            })

            # 确定状态文本（映射到前端期望的状态）
            # 前端期望：success, processing, failed
            # 后端状态：approved, pending, rejected
            status_text = "processing"  # 默认处理中
            if record.status == "approved":
                status_text = "success"  # 已通过 = 成功
            elif record.status == "rejected":
                status_text = "failed"  # 已拒绝 = 失败
            elif record.status == "pending":
                status_text = "processing"  # 待审核 = 处理中

            # 检查目标（知识库/人设卡）是否存在
            target_exists = False
            if record.target_type == "knowledge":
                kb = db_manager.get_knowledge_base_by_id(record.target_id)
                target_exists = kb is not None
            elif record.target_type == "persona":
                pc = db_manager.get_persona_card_by_id(record.target_id)
                target_exists = pc is not None

            # 获取文件大小
            total_file_size = db_manager.get_total_file_size_by_target(
                record.target_id,
                record.target_type
            )
            has_files = total_file_size > 0

            # 为了兼容前端，同时提供两种格式
            history_list.append({
                "id": record.id,
                "target_id": record.target_id,
                "type": record.target_type,
                "name": record.name,
                "description": record.description,
                "uploader_id": record.uploader_id,
                "uploader": uploader_info,
                "status": status_text,  # 使用前端期望的状态值
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "target_exists": target_exists,  # 目标是否存在
                "has_files": has_files,  # 是否有文件
                # 前端期望的字段
                "fileType": record.target_type,  # knowledge 或 persona
                "fileName": record.name,
                "fileSize": total_file_size,  # 从文件表获取实际文件大小
                "uploaderName": uploader_info.get("username", "未知用户"),
                "uploadedAt": record.created_at.isoformat() if record.created_at else None
            })

        log_api_request(app_logger, "GET", "/admin/upload-history",
                        current_user.get("id"), status_code=200)
        return Page(
            data=history_list,
            page=page,
            page_size=page_size,
            total=total,
            message="获取上传历史记录成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get upload history error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取上传历史失败: {str(e)}"
        )


@admin_router.get("/admin/upload-stats")
async def get_upload_stats(current_user: dict = Depends(get_current_user)):
    """获取上传统计数据（admin和moderator权限）

    注意：处理失败暂时无法定义，按照预期效果来看应该为知识库安全审计失败，故功能暂时留空
    """
    # 验证权限：admin或moderator
    if not (current_user.get("is_admin", False) or current_user.get("is_moderator", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员或审核员权限"
        )

    try:
        app_logger.info(f"Get upload stats: user_id={current_user.get('id')}")

        with db_manager.get_session() as session:
            from sqlalchemy import func
            from database_models import KnowledgeBase, PersonaCard, UploadRecord

            # 总上传数（知识库+人设卡）
            total_knowledge = session.query(
                func.count(KnowledgeBase.id)).scalar() or 0
            total_personas = session.query(
                func.count(PersonaCard.id)).scalar() or 0
            total_uploads = total_knowledge + total_personas

            # 成功处理数（is_pending=False）
            approved_knowledge = session.query(func.count(KnowledgeBase.id)).filter(
                KnowledgeBase.is_pending == False
            ).scalar() or 0
            approved_personas = session.query(func.count(PersonaCard.id)).filter(
                PersonaCard.is_pending == False
            ).scalar() or 0
            success_count = approved_knowledge + approved_personas

            # 处理中数（is_pending=True）
            pending_knowledge = session.query(func.count(KnowledgeBase.id)).filter(
                KnowledgeBase.is_pending == True
            ).scalar() or 0
            pending_personas = session.query(func.count(PersonaCard.id)).filter(
                PersonaCard.is_pending == True
            ).scalar() or 0
            pending_count = pending_knowledge + pending_personas

            # 处理失败数（暂时留空，因为目前没有失败状态字段）
            # 按照预期效果来看应该为知识库安全审计失败，故功能暂时留空
            failed_count = 0

        stats = {
            "totalUploads": total_uploads,
            "successCount": success_count,
            "failedCount": failed_count,  # 暂时为0，功能留空
            "pendingCount": pending_count,
            # 前端期望的字段名
            "successfulUploads": success_count,
            "failedUploads": failed_count,
            "processingUploads": pending_count
        }

        log_api_request(app_logger, "GET", "/admin/upload-stats",
                        current_user.get("id"), status_code=200)
        return Success(
            message="获取上传统计成功",
            data=stats
        )

    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get upload stats error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取上传统计失败: {str(e)}"
        )


@admin_router.post("/messages/batch-delete")
async def delete_messages(
        message_ids: List[str] = Body(...),
        current_user: dict = Depends(get_current_user)
):
    """批量删除消息（仅接收者可以删除）"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Batch delete messages: message_ids={message_ids}, user_id={user_id}")

        if not message_ids:
            raise ValidationError("消息ID列表不能为空")

        # 批量删除消息
        deleted_count = db_manager.delete_messages(message_ids, user_id)

        if deleted_count == 0:
            raise NotFoundError("没有可删除的消息")

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "delete",
            "messages",
            record_id=f"batch_{len(message_ids)}",
            user_id=user_id,
            success=True
        )

        return Success(
            message=f"成功删除 {deleted_count} 条消息",
        )

    except (ValidationError, NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Batch delete messages error", exception=e)
        log_database_operation(
            app_logger,
            "delete",
            "messages",
            record_id=f"batch_{len(message_ids)}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("批量删除消息失败")


@admin_router.delete("/admin/uploads/{upload_id}")
async def delete_upload_record(
        upload_id: str,
        current_user: dict = Depends(get_current_user)
):
    """删除上传记录（admin和moderator权限）"""
    # 验证权限
    if not (current_user.get("is_admin", False) or current_user.get("is_moderator", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员或审核员权限"
        )

    try:
        app_logger.info(
            f"Delete upload record: upload_id={upload_id}, user_id={current_user.get('id')}")

        # 检查记录是否存在
        upload_record = db_manager.get_upload_record_by_id(upload_id)
        if not upload_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="上传记录不存在"
            )

        # 删除记录
        success = db_manager.delete_upload_record(upload_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除上传记录失败"
            )

        log_api_request(app_logger, "DELETE",
                        f"/admin/uploads/{upload_id}", current_user.get("id"), status_code=200)
        return Success(
            message="上传记录已删除"
        )

    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Delete upload record error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除上传记录失败: {str(e)}"
        )


@admin_router.post("/admin/uploads/{upload_id}/reprocess")
async def reprocess_upload_record(
        upload_id: str,
        current_user: dict = Depends(get_current_user)
):
    """重新处理上传记录（admin和moderator权限）"""
    # 验证权限
    if not (current_user.get("is_admin", False) or current_user.get("is_moderator", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员或审核员权限"
        )

    try:
        app_logger.info(
            f"Reprocess upload record: upload_id={upload_id}, user_id={current_user.get('id')}")

        # 检查记录是否存在
        upload_record = db_manager.get_upload_record_by_id(upload_id)
        if not upload_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="上传记录不存在"
            )

        # 只有失败状态的记录才能重新处理
        if upload_record.status != "rejected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只能重新处理失败的上传记录"
            )

        # 检查目标（知识库/人设卡）是否存在
        target_exists = False
        if upload_record.target_type == "knowledge":
            kb = db_manager.get_knowledge_base_by_id(upload_record.target_id)
            target_exists = kb is not None
        elif upload_record.target_type == "persona":
            pc = db_manager.get_persona_card_by_id(upload_record.target_id)
            target_exists = pc is not None

        if not target_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标（知识库或人设卡）不存在，无法重新处理"
            )

        # 检查是否有文件存在
        total_file_size = db_manager.get_total_file_size_by_target(
            upload_record.target_id,
            upload_record.target_type
        )
        if total_file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="目标没有文件，无法重新处理"
            )

        # 将状态重置为 pending
        success = db_manager.update_upload_record_status_by_id(
            upload_id, "pending")
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="重新处理失败"
            )

        log_api_request(
            app_logger, "POST", f"/admin/uploads/{upload_id}/reprocess", current_user.get("id"), status_code=200)
        return Success(
            message="已提交重新处理，等待审核"
        )

    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Reprocess upload record error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新处理失败: {str(e)}"
        )
