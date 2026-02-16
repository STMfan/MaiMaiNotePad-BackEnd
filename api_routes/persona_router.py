import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status as HTTPStatus, UploadFile, File, Form, Query
from fastapi.responses import FileResponse

from api_routes.response_util import Page, Success
from database_models import sqlite_db_manager
from error_handlers import (
    APIError, ValidationError, AuthenticationError,
    AuthorizationError, NotFoundError, ConflictError,
    FileOperationError, DatabaseError
)
from file_upload import file_upload_service
# 导入错误处理和日志记录模块
from logging_config import app_logger, log_exception, log_file_operation, log_database_operation
from models import (
    PersonaCardUpdate
)
from user_management import get_current_user, get_current_user_optional

# 创建路由器
persona_router = APIRouter()

# 使用SQLite数据库管理器
db_manager = sqlite_db_manager


# 人设卡相关路由
@persona_router.post("/persona/upload")
async def upload_persona_card(
        files: List[UploadFile] = File(...),
        name: str = Form(...),
        description: str = Form(...),
        copyright_owner: Optional[str] = Form(None),
        content: Optional[str] = Form(None),
        tags: Optional[str] = Form(None),
        is_public: Optional[bool] = Form(False),
        current_user: dict = Depends(get_current_user)
):
    """上传人设卡"""
    user_id = current_user.get("id", "")
    username = current_user.get("username", "")
    try:
        app_logger.info(f"Upload persona card: user_id={user_id}, name={name}")

        # 验证输入参数
        if not name or not description:
            raise ValidationError("名称和描述不能为空")

        if not files:
            raise ValidationError("至少需要上传一个文件")

        # 检查同一用户是否已有同名人设卡
        existing_pcs = db_manager.get_persona_cards_by_user_id(user_id)
        for existing_pc in existing_pcs:
            if existing_pc.name == name:
                raise ValidationError("人设卡名称不可以重复哦")

        pc = await file_upload_service.upload_persona_card(
            files=files,
            name=name,
            description=description,
            uploader_id=user_id,
            copyright_owner=copyright_owner if copyright_owner else username,
            content=content,
            tags=tags
        )

        try:
            pc_data = pc.to_dict()
            pc_data.pop("created_at", None)
            pc_data.pop("updated_at", None)

            if is_public:
                pc_data["is_public"] = False
                pc_data["is_pending"] = True
                upload_status = "pending"
            else:
                pc_data["is_public"] = False
                pc_data["is_pending"] = False
                upload_status = "success"

            pc = db_manager.save_persona_card(pc_data)
            if not pc:
                raise DatabaseError("保存人设卡失败")
        except Exception as e:
            log_exception(app_logger, "Update persona card visibility after upload error", exception=e)
            raise DatabaseError("更新人设卡可见性状态失败")

        # 创建上传记录
        try:
            db_manager.create_upload_record(
                uploader_id=user_id,
                target_id=pc.id,
                target_type="persona",
                name=name,
                description=description,
                status=upload_status
            )
        except Exception as e:
            app_logger.warning(f"Failed to create upload record: {str(e)}")

        # 记录文件操作成功
        log_file_operation(
            app_logger,
            "upload",
            f"persona_card/{pc.id}",
            user_id=user_id,
            success=True
        )

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "create",
            "persona_card",
            record_id=pc.id,
            user_id=user_id,
            success=True
        )

        return Success(
            message="人设卡上传成功",
            data=pc.to_dict()
        )

    except (ValidationError, FileOperationError, DatabaseError, HTTPException):
        raise
    except Exception as e:
        log_exception(app_logger, "Upload persona card error", exception=e)
        log_file_operation(
            app_logger,
            "upload",
            f"persona_card/{name}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("上传人设卡失败")


@persona_router.get("/persona/public")
async def get_public_persona_cards(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页数量"),
        name: str = Query(None, description="按名称搜索"),
        uploader_id: str = Query(None, description="按上传者ID筛选"),
        sort_by: str = Query(
            "created_at", description="排序字段(created_at, updated_at, star_count)"),
        sort_order: str = Query("desc", description="排序顺序(asc, desc)")
):
    """获取所有公开的人设卡，支持分页、搜索、按上传者筛选和排序"""
    try:
        app_logger.info("Get public persona cards")

        # 允许用用户名输入进行解析
        if uploader_id:
            try:
                user = db_manager.get_user_by_id(uploader_id)
                if not user:
                    user = db_manager.get_user_by_username(uploader_id)
                if user:
                    uploader_id = user.id
                else:
                    uploader_id = None
            except Exception:
                uploader_id = None

        pcs, total = db_manager.get_public_persona_cards(
            page=page,
            page_size=page_size,
            name=name,
            uploader_id=uploader_id,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return Page(
            data=[pc.to_dict() for pc in pcs],
            page=page,
            page_size=page_size,
            total=total,
            message="公开人设卡获取成功",
        )

    except Exception as e:
        log_exception(
            app_logger, "Get public persona cards error", exception=e)
        raise APIError("获取公开人设卡失败")


@persona_router.get("/persona/{pc_id}")
async def get_persona_card(pc_id: str):
    """获取人设卡详情"""
    try:
        app_logger.info(f"Get persona card detail: pc_id={pc_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 返回完整的人设卡信息（包含文件和metadata）
        pc_dict = pc.to_dict(include_files=True)
        return Success(
            message="人设卡详情获取成功",
            data=pc_dict
        )

    except NotFoundError:
        raise
    except Exception as e:
        log_exception(app_logger, "Get persona card detail error", exception=e)
        raise APIError("获取人设卡详情失败")


@persona_router.get("/persona/{pc_id}/starred")
async def check_persona_starred(
        pc_id: str,
        current_user: dict = Depends(get_current_user)
):
    """检查人设卡是否已被当前用户Star"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Check persona starred: pc_id={pc_id}, user_id={user_id}")
        starred = db_manager.is_starred(user_id, pc_id, "persona")
        return Success(
            message="Star状态检查成功",
            data={"starred": starred}
        )
    except Exception as e:
        log_exception(app_logger, "Check persona starred error", exception=e)
        raise APIError("检查Star状态失败")


@persona_router.get("/persona/user/{user_id}")
async def get_user_persona_cards(
        user_id: str,
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页数量"),
        name: str = Query(None, description="按名称搜索"),
        tag: str = Query(None, description="按标签搜索"),
        status: str = Query("all", description="状态过滤: all/pending/approved/rejected"),
        sort_by: str = Query("created_at", description="排序字段: created_at/updated_at/name/downloads/star_count"),
        sort_order: str = Query("desc", description="排序方向: asc/desc"),
        current_user: dict = Depends(get_current_user)
):
    """获取指定用户的人设卡，支持分页/筛选；管理员/审核员可查看他人"""
    current_user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Get user persona cards: user_id={user_id}, requester={current_user_id}")

        pcs = db_manager.get_persona_cards_by_uploader(user_id)

        sort_field_map = {
            "created_at": lambda pc: pc.created_at,
            "updated_at": lambda pc: pc.updated_at,
            "name": lambda pc: pc.name.lower(),
            "downloads": lambda pc: pc.downloads or 0,
            "star_count": lambda pc: pc.star_count or 0,
        }

        def match_status(pc):
            pending = getattr(pc, "is_pending", False)
            if status == "pending":
                return pending
            if status == "approved":
                return (pending is False) and pc.is_public
            if status == "rejected":
                return (pending is False) and (not pc.is_public)
            return True

        filtered = []
        for pc in pcs:
            if name and name.lower() not in pc.name.lower():
                continue
            if tag:
                tag_list = []
                if pc.tags:
                    tag_list = pc.tags.split(",") if isinstance(pc.tags, str) else pc.tags
                if not any(tag.lower() in t.lower() for t in tag_list):
                    continue
            if not match_status(pc):
                continue
            filtered.append(pc)

        key_func = sort_field_map.get(sort_by, sort_field_map["created_at"])
        reverse = sort_order.lower() != "asc"
        filtered.sort(key=key_func, reverse=reverse)

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = filtered[start:end]

        return Page(
            data=[pc.to_dict() for pc in page_items],
            total=total,
            page=page,
            page_size=page_size,
            message="用户人设卡获取成功"
        )

    except (AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get user persona cards error", exception=e)
        raise APIError("获取用户人设卡失败")


@persona_router.put("/persona/{pc_id}")
async def update_persona_card(
        pc_id: str,
        update_data: PersonaCardUpdate,
        current_user: dict = Depends(get_current_user)
):
    """修改人设卡信息"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Update persona card: pc_id={pc_id}, user_id={user_id}")

        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        if pc.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get(
                "is_moderator", False):
            raise AuthorizationError("没有权限修改此人设卡")

        update_dict = update_data.dict(exclude_unset=True)
        if not update_dict:
            raise ValidationError("没有提供要更新的字段")

        if pc.is_public or pc.is_pending:
            allowed_fields = {"content"}
            disallowed_fields = [key for key in update_dict.keys() if key not in allowed_fields]
            if disallowed_fields:
                raise AuthorizationError("公开或审核中的人设卡仅允许修改补充说明")

        if "copyright_owner" in update_dict:
            update_dict.pop("copyright_owner", None)

        if "name" in update_dict:
            update_dict.pop("name", None)

        if not (pc.is_public or pc.is_pending):
            if "is_public" in update_dict and not (current_user.get("is_admin", False) or current_user.get("is_moderator", False)):
                raise AuthorizationError("只有管理员可以直接修改公开状态")

        for key, value in update_dict.items():
            if hasattr(pc, key):
                setattr(pc, key, value)

        if any(field != "content" for field in update_dict.keys()):
            pc.updated_at = datetime.now()

        updated_pc = db_manager.save_persona_card(pc.to_dict())
        if not updated_pc:
            raise DatabaseError("更新人设卡失败")

        log_database_operation(
            app_logger,
            "update",
            "persona_card",
            record_id=pc_id,
            user_id=user_id,
            success=True
        )

        return Success(
            message="人设卡更新成功",
            data=updated_pc.to_dict()
        )

    except (NotFoundError, AuthorizationError, ValidationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Update persona card error", exception=e)
        log_database_operation(
            app_logger,
            "update",
            "persona_card",
            record_id=pc_id,
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("修改人设卡失败")


@persona_router.post("/persona/{pc_id}/star")
async def star_persona_card(
        pc_id: str,
        current_user: dict = Depends(get_current_user)
):
    """Star人设卡"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Star persona card: pc_id={pc_id}, user_id={user_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 与 Star 知识库修改逻辑相同，不再使用单独的 remove star接口

        operation = "create"
        message = "Star"

        is_star = db_manager.is_starred(user_id, pc_id, "persona")
        if not is_star:
            # 添加Star记录
            success = db_manager.add_star(user_id, pc_id, "persona")
            if not success:
                raise ConflictError("Star失败")
        else:
            success = db_manager.remove_star(user_id, pc_id, "persona")
            if not success:
                raise NotFoundError("取消Star失败")
            operation = "delete"
            message = "取消Star"

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            operation,
            "star",
            record_id=f"{user_id}_{pc_id}",
            user_id=user_id,
            success=True
        )

        return Success(
            message=message + "成功",
        )

    except (NotFoundError, ConflictError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Star persona card error", exception=e)
        log_database_operation(
            app_logger,
            operation,
            "star",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError(message + "人设卡失败")


@persona_router.delete("/persona/{pc_id}/star")
async def unstar_persona_card(
        pc_id: str,
        current_user: dict = Depends(get_current_user)
):
    """取消Star人设卡"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Unstar persona card: pc_id={pc_id}, user_id={user_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 移除Star记录
        success = db_manager.remove_star(user_id, pc_id, "persona")
        if not success:
            raise NotFoundError("未找到Star记录")

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "delete",
            "star",
            record_id=f"{user_id}_{pc_id}",
            user_id=user_id,
            success=True
        )

        return Success(
            message="取消Star成功",
        )

    except (NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Unstar persona card error", exception=e)
        log_database_operation(
            app_logger,
            "delete",
            "star",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("取消Star人设卡失败")


@persona_router.delete("/persona/{pc_id}")
async def delete_persona_card(
        pc_id: str,
        current_user: dict = Depends(get_current_user)
):
    """删除人设卡"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Delete persona card: pc_id={pc_id}, user_id={user_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise ValidationError("人设卡不存在")

        # 验证权限：只有上传者和管理员可以删除人设卡
        if pc.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get(
                "is_moderator", False):
            raise AuthorizationError("没有权限删除此人设卡")

        # 删除关联的文件
        file_delete_success = db_manager.delete_files_by_persona_card_id(pc_id)
        if not file_delete_success:
            app_logger.warning(
                f"Failed to delete associated files for persona card: pc_id={pc_id}")

        # 删除人设卡本身
        success = db_manager.delete_persona_card(pc_id)
        if not success:
            raise DatabaseError("删除人设卡失败")

        # 删除相关的上传记录
        try:
            db_manager.delete_upload_records_by_target(pc_id, "persona")
        except Exception as e:
            app_logger.warning(f"删除人设卡上传记录失败: {str(e)}")

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "delete",
            "persona_card",
            record_id=pc_id,
            user_id=user_id,
            success=True
        )

        return Success(
            message="人设卡删除成功",
        )

    except (NotFoundError, AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete persona card error", exception=e)
        log_database_operation(
            app_logger,
            "delete",
            "persona_card",
            record_id=pc_id,
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("删除人设卡失败")


@persona_router.post("/persona/{pc_id}/files")
async def add_files_to_persona_card(
        pc_id: str,
        files: List[UploadFile] = File(...),
        current_user: dict = Depends(get_current_user)
):
    """向人设卡添加文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Add files to persona card: pc_id={pc_id}, user_id={user_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise ValidationError("人设卡不存在")

        if pc.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get(
                "is_moderator", False):
            raise AuthorizationError("没有权限向此人设卡添加文件")

        if pc.is_public or pc.is_pending:
            raise AuthorizationError("公开或审核中的人设卡不允许修改文件")

        if not files:
            raise ValidationError("至少需要上传一个文件")

        # 添加文件
        updated_pc = await file_upload_service.add_files_to_persona_card(pc_id, files)

        if not updated_pc:
            raise FileOperationError("添加文件失败")

        # 记录文件操作成功
        log_file_operation(
            app_logger,
            "add_files",
            f"persona_card/{pc_id}",
            user_id=user_id,
            success=True
        )

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "update",
            "persona_card",
            record_id=pc_id,
            user_id=user_id,
            success=True
        )

        return Success(
            message="文件添加成功",
        )
    except (NotFoundError, AuthorizationError, ValidationError, FileOperationError, DatabaseError, HTTPException):
        raise
    except Exception as e:
        log_exception(
            app_logger, "Add files to persona card error", exception=e)
        log_file_operation(
            app_logger,
            "add_files",
            f"persona_card/{pc_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("添加文件失败")


@persona_router.delete("/persona/{pc_id}/{file_id}")
async def delete_files_from_persona_card(
        pc_id: str,
        file_id: str,
        current_user: dict = Depends(get_current_user)
):
    """从人设卡删除文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Delete files from persona card: pc_id={pc_id}, user_id={user_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        if pc.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get(
                "is_moderator", False):
            raise AuthorizationError("没有权限从此人设卡删除文件")

        if pc.is_public or pc.is_pending:
            raise AuthorizationError("公开或审核中的人设卡不允许修改文件")

        # 删除文件
        success = await file_upload_service.delete_files_from_persona_card(pc_id, file_id, user_id)

        if not success:
            raise FileOperationError("删除文件失败")

        persona_deleted = False

        # 检查是否还有剩余文件，没有则自动删除整个人设卡
        remaining_files = db_manager.get_files_by_persona_card_id(pc_id)
        if not remaining_files:
            # 删除人设卡记录
            if not db_manager.delete_persona_card(pc_id):
                raise DatabaseError("删除人设卡记录失败")

            # 删除相关的上传记录
            try:
                db_manager.delete_upload_records_by_target(pc_id, "persona")
            except Exception as e:
                app_logger.warning(f"删除人设卡上传记录失败: {str(e)}")

            persona_deleted = True

        # 记录文件操作成功
        log_file_operation(
            app_logger,
            "delete_files",
            f"persona_card/{pc_id}",
            user_id=user_id,
            success=True
        )

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "update",
            "persona_card",
            record_id=pc_id,
            user_id=user_id,
            success=True
        )

        if persona_deleted:
            # 补充记录人设卡删除日志
            log_database_operation(
                app_logger,
                "delete",
                "persona_card",
                record_id=pc_id,
                user_id=user_id,
                success=True
            )

        message = "最后一个文件删除，人设卡已自动删除" if persona_deleted else "文件删除成功"
        return Success(
            message=message,
        )

    except (NotFoundError, AuthorizationError, ValidationError, FileOperationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(
            app_logger, "Delete files from persona card error", exception=e)
        log_file_operation(
            app_logger,
            "delete_files",
            f"persona_card/{pc_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("删除文件失败")


@persona_router.get("/persona/{pc_id}/download")
async def download_persona_card_files(
        pc_id: str,
        current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """下载人设卡的所有文件压缩包"""
    try:
        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 权限检查：公开人设卡任何人都可以下载，私有人设卡需要认证
        if not pc.is_public:
            if not current_user:
                raise AuthenticationError("需要登录才能下载私有人设卡")
            # 检查权限：只有上传者、管理员或版主可以下载私有人设卡
            user_role = current_user.get("role", "user")
            is_admin_or_moderator = user_role in ["admin", "moderator"]
            if pc.uploader_id != current_user.get("id") and not is_admin_or_moderator:
                raise AuthorizationError("没有权限下载此人设卡")

        # 创建ZIP文件
        zip_result = await file_upload_service.create_persona_card_zip(pc_id)
        zip_path = zip_result["zip_path"]
        zip_filename = zip_result["zip_filename"]

        # 使用原子操作更新下载计数器
        success = db_manager.increment_persona_card_downloads(pc_id)
        if not success:
            # 如果更新计数器失败，记录日志但不影响下载
            app_logger.warning(f"更新人设卡下载计数器失败: pc_id={pc_id}")

        # 返回文件下载响应
        return FileResponse(
            path=zip_path,
            filename=zip_filename,
            media_type='application/zip'
        )

    except (HTTPException, NotFoundError, AuthenticationError, AuthorizationError):
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载失败: {str(e)}"
        )


@persona_router.get("/persona/{pc_id}/file/{file_id}")
async def download_persona_card_file(
        pc_id: str,
        file_id: str,
        current_user: dict = Depends(get_current_user)
):
    """下载人设卡中的单个文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Download persona card file: pc_id={pc_id}, file_id={file_id}, user_id={user_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 验证权限：公开人设卡任何人都可以下载，私有人设卡只有上传者和管理员可以下载
        if not pc.is_public and pc.uploader_id != user_id and not current_user.get("is_admin", False):
            raise AuthorizationError("没有权限下载此人设卡")

        # 获取文件信息
        file_info = await file_upload_service.get_persona_card_file_path(pc_id, file_id)
        if not file_info:
            raise NotFoundError("文件不存在")

        # 构建完整的文件路径
        file_full_path = os.path.join(pc.base_path, file_info.get("file_path"))
        if not os.path.exists(file_full_path):
            raise NotFoundError("文件不存在")

        # 记录文件操作成功
        log_file_operation(
            app_logger,
            "download",
            f"persona_card/{pc_id}/file/{file_id}",
            user_id=user_id,
            success=True
        )

        # 返回文件响应，使用原始文件名
        return FileResponse(
            path=file_full_path,
            filename=file_info.get("file_name"),
            media_type="application/octet-stream"
        )

    except (NotFoundError, AuthorizationError, FileOperationError):
        raise
    except Exception as e:
        log_exception(
            app_logger, "Download persona card file error", exception=e)
        log_file_operation(
            app_logger,
            "download",
            f"persona_card/{pc_id}/file/{file_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("下载文件失败")
