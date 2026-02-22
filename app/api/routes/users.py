"""用户路由模块 - 处理用户信息、头像、收藏、上传历史等用户相关的API端点"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, Body, Query
from typing import Optional
import os
from datetime import datetime

from app.api.response_util import Success, Page
from app.core.database import get_db
from app.api.deps import get_current_user
from app.services.user_service import UserService
from app.models.schemas import (
    BaseResponse,
    PageResponse,
    CurrentUserResponse,
    AvatarInfo,
)
from app.utils.avatar import (
    validate_image_file,
    save_avatar_file,
    delete_avatar_file,
    ensure_avatar_dir,
    generate_initial_avatar,
)
from app.core.logging import app_logger, log_exception, log_file_operation, log_database_operation
from app.core.error_handlers import APIError, ValidationError, AuthenticationError, NotFoundError, DatabaseError
from sqlalchemy.orm import Session

# 创建路由器
router = APIRouter()


# 用户相关路由（个人信息、头像、收藏、上传历史等）


@router.get("/me", response_model=BaseResponse[CurrentUserResponse])
async def read_users_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户信息"""
    try:
        user_id = current_user.get("id", "")
        app_logger.info(f"Get user info: user_id={user_id}")

        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)

        avatar_url = None
        avatar_updated_at = None
        is_muted = False
        muted_until = None

        if user:
            if user.avatar_path:
                avatar_url = f"/{user.avatar_path}"
            if user.avatar_updated_at:
                avatar_updated_at = user.avatar_updated_at.isoformat()
            is_muted = bool(getattr(user, "is_muted", False))
            muted_until = getattr(user, "muted_until", None)

        return Success(
            message="用户信息获取成功",
            data=CurrentUserResponse(
                id=user_id,
                username=current_user.get("username", ""),
                email=current_user.get("email", ""),
                role=current_user.get("role", "user"),
                avatar_url=avatar_url,
                avatar_updated_at=avatar_updated_at,
                is_muted=is_muted,
                muted_until=muted_until,
            ),
        )
    except Exception as e:
        log_exception(app_logger, "Get user info error", exception=e)
        raise APIError("获取用户信息失败")


@router.put("/me/password", response_model=BaseResponse[None])
async def change_password(
    password_data: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """修改密码（带速率限制：每分钟最多5次尝试）"""
    try:
        user_id = current_user.get("id", "")
        app_logger.info(f"Change password request: user_id={user_id}")

        # 验证参数
        current_password = password_data.get("current_password")
        new_password = password_data.get("new_password")
        confirm_password = password_data.get("confirm_password")

        if not current_password or not new_password or not confirm_password:
            raise ValidationError("有未填写的字段")

        # 验证新密码匹配
        if new_password != confirm_password:
            raise ValidationError("新密码与确认密码不匹配")

        # 验证密码强度（与注册保持一致）
        if len(new_password) < 6:
            raise ValidationError("密码长度不能少于6位")

        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")

        # 验证当前密码
        from app.core.security import verify_password, get_password_hash

        if not verify_password(current_password, user.hashed_password):
            app_logger.warning(f"Password change failed: wrong current password, user_id={user_id}")
            raise AuthenticationError("当前密码错误")

        # 检查新密码是否与当前密码相同
        if verify_password(new_password, user.hashed_password):
            raise ValidationError("新密码不能与当前密码相同")

        # 更新密码（增加password_version）
        user.hashed_password = get_password_hash(new_password)
        user.password_version = (user.password_version or 0) + 1

        # 保存到数据库
        db.commit()
        db.refresh(user)

        log_database_operation(app_logger, "update", "user_password", success=True, user_id=user_id)

        app_logger.info(f"Password changed successfully: user_id={user_id}")

        return Success(message="密码修改成功，请重新登录")

    except (ValidationError, AuthenticationError, NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Change password error", exception=e)
        raise APIError("修改密码失败")


@router.post("/me/avatar", response_model=BaseResponse[AvatarInfo])
async def upload_avatar(
    avatar: UploadFile = File(...), current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """上传/更新头像"""
    try:
        user_id = current_user.get("id", "")
        app_logger.info(f"Upload avatar request: user_id={user_id}")

        # 读取文件内容
        content = await avatar.read()

        # 验证文件
        is_valid, error_message = validate_image_file(content, avatar.filename)
        if not is_valid:
            raise ValidationError(error_message)

        # 获取文件扩展名
        file_ext = os.path.splitext(avatar.filename)[1].lower()
        if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            file_ext = ".jpg"  # 默认使用jpg

        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")

        # 删除旧头像（如果存在）
        if user.avatar_path:
            delete_avatar_file(user.avatar_path)

        # 处理并保存头像
        ensure_avatar_dir()
        file_path, thumbnail_path = save_avatar_file(user_id, content, file_ext)

        # 更新数据库
        user.avatar_path = file_path
        user.avatar_updated_at = datetime.now()
        try:
            db.commit()
        except Exception:
            db.rollback()
            # 如果保存失败，删除已上传的文件
            delete_avatar_file(file_path)
            raise DatabaseError("保存头像信息失败")

        log_file_operation(app_logger, "upload", file_path, user_id=user_id, success=True)

        app_logger.info(f"头像上传成功: user_id={user_id}, path={file_path}")

        return Success(
            message="头像上传成功",
            data=AvatarInfo(avatar_url=f"/{file_path}", avatar_updated_at=user.avatar_updated_at.isoformat()),
        )

    except (ValidationError, NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Upload avatar error", exception=e)
        raise APIError("上传头像失败")


@router.delete("/me/avatar", response_model=BaseResponse[None])
async def delete_avatar_endpoint(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除头像（恢复为默认头像）"""
    try:
        user_id = current_user.get("id", "")
        app_logger.info(f"Delete avatar request: user_id={user_id}")

        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")

        # 如果存在头像文件，删除它
        if user.avatar_path:
            delete_avatar_file(user.avatar_path)

        # 更新数据库
        user.avatar_path = None
        user.avatar_updated_at = datetime.now()
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise DatabaseError("保存头像信息失败")

        log_file_operation(app_logger, "delete", "avatar", success=True, user_id=user_id)

        app_logger.info(f"Avatar deleted successfully: user_id={user_id}")

        return Success(message="头像已删除，已恢复为默认头像")

    except (NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete avatar error", exception=e)
        raise APIError("删除头像失败")


@router.get("/{user_id}/avatar")
async def get_user_avatar(user_id: str, size: int = 200, db: Session = Depends(get_db)):
    """获取用户头像（如果不存在则生成首字母头像）"""
    try:
        from fastapi.responses import Response, FileResponse

        user_service = UserService(db)
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")

        if user.avatar_path and os.path.exists(user.avatar_path):
            return FileResponse(user.avatar_path)

        username = user.username or "?"
        avatar_bytes = generate_initial_avatar(username, size)

        ensure_avatar_dir()
        file_path, thumbnail_path = save_avatar_file(user_id, avatar_bytes, ".jpg")

        user.avatar_path = file_path
        user.avatar_updated_at = datetime.now()
        try:
            db.commit()
        except Exception:
            db.rollback()
            delete_avatar_file(file_path)
            raise DatabaseError("保存头像信息失败")

        log_file_operation(app_logger, "upload", file_path, user_id=user_id, success=True)

        app_logger.info(f"默认首字母头像生成并保存成功: user_id={user_id}, path={file_path}")

        return Response(content=avatar_bytes, media_type="image/png")

    except NotFoundError:
        raise
    except Exception as e:
        log_exception(app_logger, "Get user avatar error", exception=e)
        raise APIError("获取用户头像失败")


# 用户Star记录相关路由
@router.get("/stars", response_model=PageResponse[dict], summary="获取用户收藏")
async def get_user_stars(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_details: bool = False,
    page: int = Query(1, description="页码，从1开始"),
    page_size: int = Query(20, description="每页条数，最大50"),
    sort_by: str = Query("created_at", description="排序字段: created_at / star_count"),
    sort_order: str = Query("desc", description="排序方向: asc / desc"),
    type: str = Query("all", description="收藏类型: knowledge / persona"),
):
    """获取用户Star的知识库和人设卡"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Get user stars: user_id={user_id}, include_details={include_details}, "
            f"page={page}, page_size={page_size}, sort_by={sort_by}, sort_order={sort_order}, type={type}"
        )

        page_size = min(page_size, 50)
        stars = _get_user_star_records(db, user_id, type)
        stars = _sort_star_records(db, stars, sort_by, sort_order)
        result = _build_star_result_list(db, stars, include_details)

        total = len(result)
        page_items = _paginate_results(result, page, page_size)

        log_database_operation(app_logger, "read", "star", user_id=user_id, success=True)
        app_logger.info(f"Returning {len(page_items)} items out of {total} total items")

        return Page(data=page_items, page=page, page_size=page_size, total=total, message="获取收藏记录成功")
    except DatabaseError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get user stars error", exception=e)
        log_database_operation(app_logger, "read", "star", user_id=user_id, success=False, error_message=str(e))
        raise APIError("获取收藏记录失败")


def _get_user_star_records(db: Session, user_id: str, type_filter: str):
    """获取用户的Star记录并按类型过滤"""
    from app.models.database import StarRecord

    stars = db.query(StarRecord).filter(StarRecord.user_id == user_id).all()

    if type_filter != "all":
        stars = [star for star in stars if star.target_type == type_filter]

    return stars


def _sort_star_records(db: Session, stars: list, sort_by: str, sort_order: str):
    """对Star记录进行排序"""
    from app.models.database import KnowledgeBase, PersonaCard

    reverse_order = sort_order == "desc"

    if sort_by == "star_count":
        star_items = []
        for star in stars:
            if star.target_type == "knowledge":
                kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == star.target_id).first()
                if kb and kb.is_public:
                    star_items.append((star, kb.star_count))
            elif star.target_type == "persona":
                pc = db.query(PersonaCard).filter(PersonaCard.id == star.target_id).first()
                if pc and pc.is_public:
                    star_items.append((star, pc.star_count))

        star_items.sort(key=lambda x: x[1], reverse=reverse_order)
        return [item[0] for item in star_items]
    else:
        stars.sort(key=lambda x: x.created_at, reverse=reverse_order)
        return stars


def _build_star_result_list(db: Session, stars: list, include_details: bool):
    """构建Star结果列表"""
    result = []
    for star in stars:
        if star.target_type == "knowledge":
            item = _build_knowledge_star_item(db, star, include_details)
            if item:
                result.append(item)
        elif star.target_type == "persona":
            item = _build_persona_star_item(db, star, include_details)
            if item:
                result.append(item)
    return result


def _build_knowledge_star_item(db: Session, star, include_details: bool):
    """构建知识库Star项"""
    from app.models.database import KnowledgeBase

    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == star.target_id).first()
    if not kb or not kb.is_public:
        return None

    item = {
        "id": star.id,
        "type": "knowledge",
        "target_id": star.target_id,
        "name": kb.name,
        "description": kb.description,
        "star_count": kb.star_count,
        "created_at": star.created_at.isoformat(),
    }

    if include_details:
        kb_dict = kb.to_dict()
        item.update(kb_dict)

    return item


def _build_persona_star_item(db: Session, star, include_details: bool):
    """构建人设卡Star项"""
    from app.models.database import PersonaCard

    pc = db.query(PersonaCard).filter(PersonaCard.id == star.target_id).first()
    if not pc or not pc.is_public:
        return None

    item = {
        "id": star.id,
        "type": "persona",
        "target_id": star.target_id,
        "name": pc.name,
        "description": pc.description,
        "star_count": pc.star_count,
        "created_at": star.created_at.isoformat(),
    }

    if include_details:
        pc_dict = pc.to_dict()
        item.update(pc_dict)

    return item


def _paginate_results(result: list, page: int, page_size: int):
    """对结果进行分页"""
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    return result[start_idx:end_idx]


# 用户上传历史和统计接口
@router.get("/me/upload-history", response_model=PageResponse[dict])
async def get_my_upload_history(
    page: int = Query(1, description="页码，从1开始"),
    page_size: int = Query(20, description="每页条数，最大100"),
    status: Optional[str] = Query(None, description="状态过滤：approved, rejected, pending"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的个人上传历史记录（分页）"""
    try:
        user_id = current_user.get("id", "")
        app_logger.info(
            f"Get user upload history: user_id={user_id}, page={page}, page_size={page_size}, status={status}"
        )

        # 限制参数范围
        if page_size < 1 or page_size > 100:
            page_size = 20
        if page < 1:
            page = 1

        user_service = UserService(db)
        upload_records = user_service.get_upload_records_by_uploader(
            user_id, page=page, page_size=page_size, status=status
        )

        # 构建返回数据
        history_list = []
        for record in upload_records:
            # 确定状态文本（映射到前端期望的状态）
            status_text = "processing"  # 默认处理中
            if record.status == "approved":
                status_text = "success"
            elif record.status == "rejected":
                status_text = "failed"
            elif record.status == "pending":
                status_text = "processing"

            # 检查目标（知识库/人设卡）是否存在
            target_exists = False
            if record.target_type == "knowledge":
                kb = user_service.get_knowledge_base_by_id(record.target_id)
                target_exists = kb is not None
            elif record.target_type == "persona":
                pc = user_service.get_persona_card_by_id(record.target_id)
                target_exists = pc is not None

            # 获取文件大小
            total_file_size = user_service.get_total_file_size_by_target(record.target_id, record.target_type)
            has_files = total_file_size > 0

            # 构建记录信息
            history_list.append(
                {
                    "id": record.id,
                    "target_id": record.target_id,
                    "type": record.target_type,
                    "name": record.name,
                    "description": record.description,
                    "status": status_text,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "updated_at": record.updated_at.isoformat() if record.updated_at else None,
                    "target_exists": target_exists,
                    "has_files": has_files,
                    # 前端期望的字段
                    "fileType": record.target_type,
                    "fileName": record.name,
                    "fileSize": total_file_size,
                    "uploadedAt": record.created_at.isoformat() if record.created_at else None,
                }
            )

        # 获取总数量
        total_count = user_service.get_upload_records_count_by_uploader(user_id, status=status)

        log_database_operation(app_logger, "read", "upload_record", user_id=user_id, success=True)

        app_logger.info(f"Returning {len(history_list)} items out of {total_count} total items")

        return Page(
            message="获取上传历史成功",
            data=history_list,
            total=total_count,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        log_exception(app_logger, "Get user upload history error", exception=e)
        log_database_operation(
            app_logger, "read", "upload_record", user_id=current_user.get("id", ""), success=False, error_message=str(e)
        )
        raise APIError("获取上传历史失败")


@router.get("/me/upload-stats", response_model=BaseResponse[dict])
async def get_my_upload_stats(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户的个人上传统计"""
    try:
        user_id = current_user.get("id", "")
        app_logger.info(f"Get user upload stats: user_id={user_id}")

        user_service = UserService(db)
        stats = user_service.get_upload_stats_by_uploader(user_id)

        log_database_operation(app_logger, "read", "upload_stats", user_id=user_id, success=True)

        app_logger.info(f"Upload stats for user {user_id}")

        return Success(
            message="获取上传统计成功",
            data={
                "total": stats["total"],
                "success": stats["success"],
                "pending": stats["pending"],
                "failed": stats["failed"],
                "knowledge": stats["knowledge"],
                "persona": stats["persona"],
            },
        )

    except Exception as e:
        log_exception(app_logger, "Get user upload stats error", exception=e)
        log_database_operation(app_logger, "read", "upload_stats", user_id=user_id, success=False, error_message=str(e))
        raise APIError("获取上传统计失败")


@router.get("/me/dashboard-stats", response_model=BaseResponse[dict])
async def get_my_dashboard_stats(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户的个人数据概览统计"""
    try:
        user_id = current_user.get("id", "")
        app_logger.info(f"Get user dashboard stats: user_id={user_id}")

        user_service = UserService(db)

        # 上传统计
        upload_stats = user_service.get_upload_stats_by_uploader(user_id)
        total_uploads = upload_stats.get("total", 0)
        knowledge_uploads = upload_stats.get("knowledge", 0)
        persona_uploads = upload_stats.get("persona", 0)

        # 下载与收藏统计
        from sqlalchemy import func
        from app.models.database import KnowledgeBase, PersonaCard

        kb_downloads = (
            db.query(func.sum(KnowledgeBase.downloads)).filter(KnowledgeBase.uploader_id == user_id).scalar() or 0
        )
        pc_downloads = (
            db.query(func.sum(PersonaCard.downloads)).filter(PersonaCard.uploader_id == user_id).scalar() or 0
        )

        kb_stars = (
            db.query(func.sum(KnowledgeBase.star_count)).filter(KnowledgeBase.uploader_id == user_id).scalar() or 0
        )
        pc_stars = db.query(func.sum(PersonaCard.star_count)).filter(PersonaCard.uploader_id == user_id).scalar() or 0

        data = {
            "totalUploads": total_uploads,
            "knowledgeUploads": knowledge_uploads,
            "personaUploads": persona_uploads,
            "totalDownloads": kb_downloads + pc_downloads,
            "knowledgeDownloads": kb_downloads,
            "personaDownloads": pc_downloads,
            "totalStars": kb_stars + pc_stars,
            "knowledgeStars": kb_stars,
            "personaStars": pc_stars,
        }

        log_database_operation(app_logger, "read", "dashboard_stats", user_id=user_id, success=True)

        return Success(message="获取个人数据概览成功", data=data)

    except Exception as e:
        log_exception(app_logger, "Get user dashboard stats error", exception=e)
        log_database_operation(
            app_logger,
            "read",
            "dashboard_stats",
            user_id=current_user.get("id", ""),
            success=False,
            error_message=str(e),
        )
        raise APIError("获取个人数据概览失败")


@router.get("/me/dashboard-trends", response_model=BaseResponse[dict])
async def get_my_dashboard_trends(
    days: int = Query(30, ge=1, le=90, description="统计天数，默认30天，最大90天"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户最近N天的下载与收藏趋势"""
    try:
        user_id = current_user.get("id", "")
        app_logger.info(f"Get user dashboard trends: user_id={user_id}, days={days}")

        user_service = UserService(db)
        trend_stats = user_service.get_dashboard_trend_stats(user_id, days=days)

        log_database_operation(
            app_logger,
            "read",
            "dashboard_trends",
            user_id=user_id,
            success=True,
        )

        return Success(
            message="获取个人数据趋势成功",
            data=trend_stats,
        )
    except Exception as e:
        log_exception(app_logger, "Get user dashboard trends error", exception=e)
        log_database_operation(
            app_logger,
            "read",
            "dashboard_trends",
            user_id=current_user.get("id", ""),
            success=False,
            error_message=str(e),
        )
        raise APIError("获取个人数据趋势失败")
