"""
人设卡路由模块

处理人设卡相关的API端点，包括：
- 上传人设卡
- 查询人设卡（公开、个人、详情）
- 编辑人设卡
- 删除人设卡
- 收藏/取消收藏人设卡
- 下载人设卡
"""

import os
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi import status as http_status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_optional
from app.api.response_util import Page, Success
from app.core.database import get_db
from app.core.error_handlers import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    FileOperationError,
    NotFoundError,
    ValidationError,
)

# 导入错误处理和日志记录模块
from app.core.logging import app_logger, log_database_operation, log_exception, log_file_operation
from app.models.schemas import BaseResponse, PersonaCardUpdate
from app.services.file_service import FileDatabaseError, FileService, FileValidationError
from app.services.file_upload_service import FileUploadService
from app.services.persona_service import PersonaService

# 创建路由器
router = APIRouter()


# 人设卡相关路由（上传、查询、编辑、删除等）
def _validate_persona_card_upload_input(name: str, description: str, files: list[UploadFile]) -> None:
    """验证人设卡上传输入

    Args:
        name: 人设卡名称
        description: 人设卡描述
        files: 上传的文件列表

    Raises:
        ValidationError: 输入验证失败
    """
    if not name or not description:
        raise ValidationError("名称和描述不能为空")

    if not files:
        raise ValidationError("至少需要上传一个文件")


def _check_persona_card_uniqueness(persona_service: PersonaService) -> None:
    """检查系统中是否已存在人设卡

    Args:
        persona_service: 人设卡服务实例

    Raises:
        ValidationError: 系统已存在人设卡
    """
    existing_pcs = persona_service.get_all_persona_cards()
    if existing_pcs:
        raise ValidationError(
            message="当前系统已存在人设卡，暂不支持创建多个人设卡", details={"code": "PERSONA_ONLY_ONE_ALLOWED"}
        )


async def _prepare_persona_card_file_data(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    """准备人设卡文件数据

    Args:
        files: 上传的文件列表

    Returns:
        文件数据列表，每个元素为 (文件名, 文件内容) 元组
    """
    file_data = []
    for file in files:
        content_bytes = await file.read()
        file_data.append((file.filename, content_bytes))
        await file.seek(0)
    return file_data


def _set_persona_card_visibility(pc, is_public: bool, db: Session) -> str:
    """设置人设卡可见性和审核状态

    Args:
        pc: 人设卡对象
        is_public: 是否公开
        db: 数据库会话

    Returns:
        上传状态（"pending" 或 "success"）

    Raises:
        DatabaseError: 更新可见性状态失败
    """
    try:
        if is_public:
            pc.is_public = False
            pc.is_pending = True
            upload_status = "pending"
        else:
            pc.is_public = False
            pc.is_pending = False
            upload_status = "success"

        db.commit()
        db.refresh(pc)
        return upload_status
    except Exception as e:
        db.rollback()
        log_exception(app_logger, "Update persona card visibility after upload error", exception=e)
        raise DatabaseError("更新人设卡可见性状态失败") from e


def _create_persona_card_upload_record(
    persona_service: PersonaService, user_id: str, pc_id: str, name: str, description: str, upload_status: str
) -> None:
    """创建人设卡上传记录

    Args:
        persona_service: 人设卡服务实例
        user_id: 用户ID
        pc_id: 人设卡ID
        name: 人设卡名称
        description: 人设卡描述
        upload_status: 上传状态
    """
    try:
        persona_service.create_upload_record(
            uploader_id=user_id, target_id=pc_id, name=name, description=description, status=upload_status
        )
    except Exception as e:
        app_logger.warning(f"Failed to create upload record: {str(e)}")


@router.post("/persona/upload")
async def upload_persona_card(
    files: list[UploadFile] = File(...),
    name: str = Form(...),
    description: str = Form(...),
    copyright_owner: str | None = Form(None),
    content: str | None = Form(None),
    tags: str | None = Form(None),
    is_public: bool | None = Form(False),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传人设卡"""
    user_id = current_user.get("id", "")
    username = current_user.get("username", "")
    try:
        app_logger.info(f"Upload persona card: user_id={user_id}, name={name}")

        _validate_persona_card_upload_input(name, description, files)

        persona_service = PersonaService(db)
        _check_persona_card_uniqueness(persona_service)

        file_data = await _prepare_persona_card_file_data(files)

        file_service = FileService(db)
        pc = file_service.upload_persona_card(
            files=file_data,
            name=name,
            description=description,
            uploader_id=user_id,
            copyright_owner=copyright_owner if copyright_owner else username,
            content=content,
            tags=tags,
        )

        upload_status = _set_persona_card_visibility(pc, is_public, db)
        _create_persona_card_upload_record(persona_service, user_id, pc.id, name, description, upload_status)

        log_file_operation(app_logger, "upload", f"persona_card/{pc.id}", user_id=user_id, success=True)
        log_database_operation(app_logger, "create", "persona_card", record_id=pc.id, user_id=user_id, success=True)

        return Success(message="人设卡上传成功", data=pc.to_dict())

    except FileValidationError as e:
        raise ValidationError(e.message, details=getattr(e, "details", {})) from e
    except FileDatabaseError as e:
        raise DatabaseError(e.message) from e
    except (ValidationError, FileOperationError, DatabaseError, HTTPException):
        raise
    except Exception as e:
        log_exception(app_logger, "Upload persona card error", exception=e)
        log_file_operation(
            app_logger, "upload", f"persona_card/{name}", user_id=user_id, success=False, error_message=str(e)
        )
        raise APIError("上传人设卡失败") from e


@router.get("/persona/public")
async def get_public_persona_cards(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    name: str = Query(None, description="按名称搜索"),
    uploader_id: str = Query(None, description="按上传者ID筛选"),
    sort_by: str = Query("created_at", description="排序字段(created_at, updated_at, star_count)"),
    sort_order: str = Query("desc", description="排序顺序(asc, desc)"),
    db: Session = Depends(get_db),
):
    """获取所有公开的人设卡，支持分页、搜索、按上传者筛选和排序"""
    try:
        app_logger.info("Get public persona cards")

        # 使用服务层
        persona_service = PersonaService(db)

        # 允许用用户名输入进行解析
        if uploader_id:
            uploader_id = persona_service.resolve_uploader_id(uploader_id)

        pcs, total = persona_service.get_public_persona_cards(
            page=page, page_size=page_size, name=name, uploader_id=uploader_id, sort_by=sort_by, sort_order=sort_order
        )
        return Page(
            data=[pc.to_dict() for pc in pcs],
            page=page,
            page_size=page_size,
            total=total,
            message="公开人设卡获取成功",
        )

    except Exception as e:
        log_exception(app_logger, "Get public persona cards error", exception=e)
        raise APIError("获取公开人设卡失败") from e


@router.get("/persona/{pc_id}")
async def get_persona_card(pc_id: str, db: Session = Depends(get_db)):
    """获取人设卡详情"""
    try:
        app_logger.info(f"Get persona card detail: pc_id={pc_id}")

        persona_service = PersonaService(db)

        pc = persona_service.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        pc_dict = pc.to_dict()

        files = persona_service.get_files_by_persona_card_id(pc_id)
        pc_dict["files"] = (
            [
                {
                    "file_id": f.id,
                    "file_name": f.file_name,
                    "original_name": f.original_name,
                    "file_type": f.file_type,
                    "file_size": f.file_size,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in files
            ]
            if files
            else []
        )

        return Success(message="人设卡详情获取成功", data=pc_dict)

    except NotFoundError:
        raise
    except Exception as e:
        log_exception(app_logger, "Get persona card detail error", exception=e)
        raise APIError("获取人设卡详情失败") from e


@router.get("/persona/{pc_id}/starred")
async def check_persona_starred(
    pc_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """检查人设卡是否已被当前用户Star"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Check persona starred: pc_id={pc_id}, user_id={user_id}")

        persona_service = PersonaService(db)
        starred = persona_service.is_starred(user_id, pc_id)

        return Success(message="Star状态检查成功", data={"starred": starred})
    except Exception as e:
        log_exception(app_logger, "Check persona starred error", exception=e)
        raise APIError("检查Star状态失败") from e


@router.get("/persona/user/{user_id}")
async def get_user_persona_cards(
    user_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    name: str = Query(None, description="按名称搜索"),
    tag: str = Query(None, description="按标签搜索"),
    status: str = Query("all", description="状态过滤: all/pending/approved/rejected"),
    sort_by: str = Query("created_at", description="排序字段: created_at/updated_at/name/downloads/star_count"),
    sort_order: str = Query("desc", description="排序方向: asc/desc"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定用户的人设卡，支持分页/筛选；管理员/审核员可查看他人"""
    current_user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Get user persona cards: user_id={user_id}, requester={current_user_id}")

        # 使用服务层
        persona_service = PersonaService(db)
        pcs, total = persona_service.get_user_persona_cards(
            user_id=user_id,
            page=page,
            page_size=page_size,
            name=name,
            tag=tag,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return Page(
            data=[pc.to_dict() for pc in pcs], total=total, page=page, page_size=page_size, message="用户人设卡获取成功"
        )

    except (AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get user persona cards error", exception=e)
        raise APIError("获取用户人设卡失败") from e


def _validate_persona_card_for_update(persona_service: PersonaService, pc_id: str, user_id: str, current_user: dict):
    """验证人设卡是否可以更新

    Args:
        persona_service: 人设卡服务实例
        pc_id: 人设卡ID
        user_id: 用户ID
        current_user: 当前用户信息

    Returns:
        人设卡对象

    Raises:
        NotFoundError: 人设卡不存在
        AuthorizationError: 无权限修改
    """
    pc = persona_service.get_persona_card_by_id(pc_id)
    if not pc:
        raise NotFoundError("人设卡不存在")

    if (
        pc.uploader_id != user_id
        and not current_user.get("is_admin", False)
        and not current_user.get("is_moderator", False)
    ):
        raise AuthorizationError("没有权限修改此人设卡")

    return pc


def _prepare_persona_card_update_dict(update_data: PersonaCardUpdate, pc, current_user: dict) -> dict:
    """准备人设卡更新字典并验证权限

    Args:
        update_data: 更新数据
        pc: 人设卡对象
        current_user: 当前用户信息

    Returns:
        处理后的更新字典

    Raises:
        ValidationError: 没有提供要更新的字段
        AuthorizationError: 权限不足
    """
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        raise ValidationError("没有提供要更新的字段")

    # 仅私有人设卡允许修改基础信息和文件；
    # 公开或审核中的人设卡仅允许修改补充说明（content）
    if pc.is_public or pc.is_pending:
        _validate_public_persona_card_updates(update_dict)

    # 移除不允许通过该接口修改的字段
    update_dict.pop("copyright_owner", None)
    update_dict.pop("name", None)

    # 验证 is_public 修改权限
    if not (pc.is_public or pc.is_pending):
        _validate_persona_card_public_status_change(update_dict, current_user)

    return update_dict


def _validate_public_persona_card_updates(update_dict: dict) -> None:
    """验证公开或审核中的人设卡更新

    Args:
        update_dict: 更新字典

    Raises:
        AuthorizationError: 尝试修改不允许的字段
    """
    allowed_fields = {"content"}
    disallowed_fields = [key for key in update_dict.keys() if key not in allowed_fields]
    if disallowed_fields:
        raise AuthorizationError("公开或审核中的人设卡仅允许修改补充说明")


def _validate_persona_card_public_status_change(update_dict: dict, current_user: dict) -> None:
    """验证人设卡公开状态修改权限

    Args:
        update_dict: 更新字典
        current_user: 当前用户信息

    Raises:
        AuthorizationError: 普通用户尝试直接修改公开状态
    """
    if "is_public" in update_dict and not (
        current_user.get("is_admin", False) or current_user.get("is_moderator", False)
    ):
        raise AuthorizationError("只有管理员可以直接修改公开状态")


def _execute_persona_card_update(
    persona_service: PersonaService, pc_id: str, update_dict: dict, user_id: str, current_user: dict
):
    """执行人设卡更新

    Args:
        persona_service: 人设卡服务实例
        pc_id: 人设卡ID
        update_dict: 更新字典
        user_id: 用户ID
        current_user: 当前用户信息

    Returns:
        更新后的人设卡对象

    Raises:
        AuthorizationError: 权限错误
        NotFoundError: 人设卡不存在
        DatabaseError: 数据库错误
    """
    success, message, updated_pc = persona_service.update_persona_card(
        pc_id=pc_id,
        update_data=update_dict,
        user_id=user_id,
        is_admin=current_user.get("is_admin", False),
        is_moderator=current_user.get("is_moderator", False),
    )

    if not success:
        if "权限" in message:
            raise AuthorizationError(message)
        elif "不存在" in message:
            raise NotFoundError(message)
        else:
            raise DatabaseError(message)

    return updated_pc


@router.put("/persona/{pc_id}")
async def update_persona_card(
    pc_id: str,
    update_data: PersonaCardUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改人设卡信息"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Update persona card: pc_id={pc_id}, user_id={user_id}")

        persona_service = PersonaService(db)
        pc = _validate_persona_card_for_update(persona_service, pc_id, user_id, current_user)

        update_dict = _prepare_persona_card_update_dict(update_data, pc, current_user)
        updated_pc = _execute_persona_card_update(persona_service, pc_id, update_dict, user_id, current_user)

        log_database_operation(app_logger, "update", "persona_card", record_id=pc_id, user_id=user_id, success=True)

        return Success(message="人设卡更新成功", data=updated_pc.to_dict())

    except (NotFoundError, AuthorizationError, ValidationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Update persona card error", exception=e)
        log_database_operation(
            app_logger, "update", "persona_card", record_id=pc_id, user_id=user_id, success=False, error_message=str(e)
        )
        raise APIError("修改人设卡失败") from e


@router.post("/persona/{pc_id}/star")
async def star_persona_card(pc_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Star人设卡"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Star persona card: pc_id={pc_id}, user_id={user_id}")

        # 使用服务层
        persona_service = PersonaService(db)

        # 检查人设卡是否存在
        pc = persona_service.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 与 Star 知识库修改逻辑相同，不再使用单独的 remove star接口

        operation = "create"
        message = "Star"

        is_star = persona_service.is_starred(user_id, pc_id)
        if not is_star:
            # 添加Star记录
            success = persona_service.add_star(user_id, pc_id)
            if not success:
                raise ConflictError("Star失败")
        else:
            success = persona_service.remove_star(user_id, pc_id)
            if not success:
                raise NotFoundError("取消Star失败")
            operation = "delete"
            message = "取消Star"

        # 记录数据库操作成功
        log_database_operation(
            app_logger, operation, "star", record_id=f"{user_id}_{pc_id}", user_id=user_id, success=True
        )

        return Success(
            message=message + "成功",
        )

    except (NotFoundError, ConflictError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Star persona card error", exception=e)
        log_database_operation(app_logger, operation, "star", user_id=user_id, success=False, error_message=str(e))
        raise APIError(message + "人设卡失败") from e


@router.delete("/persona/{pc_id}/star")
async def unstar_persona_card(
    pc_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """取消Star人设卡"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Unstar persona card: pc_id={pc_id}, user_id={user_id}")

        # 使用服务层
        persona_service = PersonaService(db)

        # 检查人设卡是否存在
        pc = persona_service.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 移除Star记录
        success = persona_service.remove_star(user_id, pc_id)
        if not success:
            raise NotFoundError("未找到Star记录")

        # 记录数据库操作成功
        log_database_operation(
            app_logger, "delete", "star", record_id=f"{user_id}_{pc_id}", user_id=user_id, success=True
        )

        return Success(
            message="取消Star成功",
        )

    except (NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Unstar persona card error", exception=e)
        log_database_operation(app_logger, "delete", "star", user_id=user_id, success=False, error_message=str(e))
        raise APIError("取消Star人设卡失败") from e


@router.delete("/persona/{pc_id}")
async def delete_persona_card(
    pc_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """删除人设卡"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Delete persona card: pc_id={pc_id}, user_id={user_id}")

        # 使用服务层
        persona_service = PersonaService(db)

        # 检查人设卡是否存在
        pc = persona_service.get_persona_card_by_id(pc_id)
        if not pc:
            raise ValidationError("人设卡不存在")

        # 验证权限：只有上传者和管理员可以删除人设卡
        if (
            pc.uploader_id != user_id
            and not current_user.get("is_admin", False)
            and not current_user.get("is_moderator", False)
        ):
            raise AuthorizationError("没有权限删除此人设卡")

        # 删除关联的文件
        file_delete_success = persona_service.delete_files_by_persona_card_id(pc_id)
        if not file_delete_success:
            app_logger.warning(f"Failed to delete associated files for persona card: pc_id={pc_id}")

        # 删除人设卡本身
        success = persona_service.delete_persona_card(pc_id)
        if not success:
            raise DatabaseError("删除人设卡失败")

        # 删除相关的上传记录
        try:
            persona_service.delete_upload_records_by_target(pc_id)
        except Exception as e:
            app_logger.warning(f"删除人设卡上传记录失败: {str(e)}")

        # 记录数据库操作成功
        log_database_operation(app_logger, "delete", "persona_card", record_id=pc_id, user_id=user_id, success=True)

        return Success(
            message="人设卡删除成功",
        )

    except (NotFoundError, AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete persona card error", exception=e)
        log_database_operation(
            app_logger, "delete", "persona_card", record_id=pc_id, user_id=user_id, success=False, error_message=str(e)
        )
        raise APIError("删除人设卡失败") from e


@router.post("/persona/{pc_id}/files")
async def add_files_to_persona_card(
    pc_id: str,
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """向人设卡添加文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Add files to persona card: pc_id={pc_id}, user_id={user_id}")

        # 使用服务层
        persona_service = PersonaService(db)

        # 检查人设卡是否存在
        pc = persona_service.get_persona_card_by_id(pc_id)
        if not pc:
            raise ValidationError("人设卡不存在")

        if (
            pc.uploader_id != user_id
            and not current_user.get("is_admin", False)
            and not current_user.get("is_moderator", False)
        ):
            raise AuthorizationError("没有权限向此人设卡添加文件")

        if pc.is_public or pc.is_pending:
            raise AuthorizationError("公开或审核中的人设卡不允许修改文件")

        if not files:
            raise ValidationError("至少需要上传一个文件")

        # 添加文件
        file_upload_service = FileUploadService(db)
        updated_pc = await file_upload_service.add_files_to_persona_card(pc_id, files)

        if not updated_pc:
            raise FileOperationError("添加文件失败")

        # 记录文件操作成功
        log_file_operation(app_logger, "add_files", f"persona_card/{pc_id}", user_id=user_id, success=True)

        # 记录数据库操作成功
        log_database_operation(app_logger, "update", "persona_card", record_id=pc_id, user_id=user_id, success=True)

        return Success(
            message="文件添加成功",
        )
    except (NotFoundError, AuthorizationError, ValidationError, FileOperationError, DatabaseError, HTTPException):
        raise
    except Exception as e:
        log_exception(app_logger, "Add files to persona card error", exception=e)
        log_file_operation(
            app_logger, "add_files", f"persona_card/{pc_id}", user_id=user_id, success=False, error_message=str(e)
        )
        raise APIError("添加文件失败") from e


@router.delete("/persona/{pc_id}/{file_id}", response_model=BaseResponse[dict])
async def delete_files_from_persona_card(
    pc_id: str, file_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """从人设卡删除文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Delete files from persona card: pc_id={pc_id}, user_id={user_id}")

        # 使用服务层
        persona_service = PersonaService(db)

        # 检查人设卡是否存在
        pc = persona_service.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 验证权限
        _validate_pc_file_deletion_permission(pc, user_id, current_user)

        # 删除文件
        file_upload_service = FileUploadService(db)
        success = await file_upload_service.delete_files_from_persona_card(pc_id, file_id, user_id)

        if not success:
            raise FileOperationError("删除文件失败")

        # 检查是否还有剩余文件，没有则自动删除整个人设卡
        persona_deleted = _cleanup_empty_pc_if_needed(persona_service, pc_id, user_id)

        # 记录文件操作成功
        log_file_operation(app_logger, "delete_files", f"persona_card/{pc_id}", user_id=user_id, success=True)

        # 记录数据库操作成功
        log_database_operation(app_logger, "update", "persona_card", record_id=pc_id, user_id=user_id, success=True)

        if persona_deleted:
            # 补充记录人设卡删除日志
            log_database_operation(app_logger, "delete", "persona_card", record_id=pc_id, user_id=user_id, success=True)

        message = "最后一个文件删除，人设卡已自动删除" if persona_deleted else "文件删除成功"
        return Success(message=message)

    except (NotFoundError, AuthorizationError, ValidationError, FileOperationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete files from persona card error", exception=e)
        log_file_operation(
            app_logger, "delete_files", f"persona_card/{pc_id}", user_id=user_id, success=False, error_message=str(e)
        )
        raise APIError("删除文件失败") from e


def _validate_pc_file_deletion_permission(pc: Any, user_id: str, current_user: dict) -> None:
    """验证人设卡文件删除权限

    Args:
        pc: 人设卡对象
        user_id: 当前用户ID
        current_user: 当前用户信息

    Raises:
        AuthorizationError: 权限验证失败
    """
    if (
        pc.uploader_id != user_id
        and not current_user.get("is_admin", False)
        and not current_user.get("is_moderator", False)
    ):
        raise AuthorizationError("没有权限从此人设卡删除文件")

    if pc.is_public or pc.is_pending:
        raise AuthorizationError("公开或审核中的人设卡不允许修改文件")


def _cleanup_empty_pc_if_needed(persona_service: Any, pc_id: str, user_id: str) -> bool:
    """如果人设卡没有剩余文件，则删除整个人设卡

    Args:
        persona_service: 人设卡服务
        pc_id: 人设卡ID
        user_id: 用户ID

    Returns:
        是否删除了人设卡

    Raises:
        DatabaseError: 数据库操作失败
    """
    remaining_files = persona_service.get_files_by_persona_card_id(pc_id)
    if not remaining_files:
        # 删除人设卡记录
        if not persona_service.delete_persona_card(pc_id):
            raise DatabaseError("删除人设卡记录失败")

        # 删除相关的上传记录
        try:
            persona_service.delete_upload_records_by_target(pc_id)
        except Exception as e:
            app_logger.warning(f"删除人设卡上传记录失败: {str(e)}")

        return True
    return False


@router.get("/persona/{pc_id}/download", response_class=FileResponse)
async def download_persona_card_files(
    pc_id: str, current_user: dict | None = Depends(get_current_user_optional), db: Session = Depends(get_db)
):
    """下载人设卡的所有文件压缩包"""
    try:
        # 使用服务层
        persona_service = PersonaService(db)

        # 检查人设卡是否存在
        pc = persona_service.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 验证下载权限
        _validate_pc_download_permission(pc, current_user)

        # 创建ZIP文件（使用文件服务）
        file_service = FileService(db)
        zip_result = file_service.create_persona_card_zip(pc_id)
        zip_path = zip_result["zip_path"]
        zip_filename = zip_result["zip_filename"]

        # 使用原子操作更新下载计数器
        success = persona_service.increment_downloads(pc_id)
        if not success:
            # 如果更新计数器失败，记录日志但不影响下载
            app_logger.warning(f"更新人设卡下载计数器失败: pc_id={pc_id}")

        # 返回文件下载响应
        return FileResponse(path=zip_path, filename=zip_filename, media_type="application/zip")

    except (HTTPException, NotFoundError, AuthenticationError, AuthorizationError):
        raise
    except FileValidationError as e:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=e.message) from e
    except FileDatabaseError as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message) from e
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"下载失败: {str(e)}") from e


def _validate_pc_download_permission(pc: Any, current_user: dict | None) -> None:
    """验证人设卡下载权限

    Args:
        pc: 人设卡对象
        current_user: 当前用户信息（可选）

    Raises:
        AuthenticationError: 需要认证
        AuthorizationError: 权限不足
    """
    # 公开人设卡任何人都可以下载
    if pc.is_public:
        return

    # 私有人设卡需要认证
    if not current_user:
        raise AuthenticationError("需要登录才能下载私有人设卡")

    # 检查权限：只有上传者、管理员或版主可以下载私有人设卡
    user_role = current_user.get("role", "user")
    is_admin_or_moderator = user_role in ["admin", "moderator"]
    if pc.uploader_id != current_user.get("id") and not is_admin_or_moderator:
        raise AuthorizationError("没有权限下载此人设卡")


@router.get("/persona/{pc_id}/file/{file_id}")
async def download_persona_card_file(
    pc_id: str, file_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """下载人设卡中的单个文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Download persona card file: pc_id={pc_id}, file_id={file_id}, user_id={user_id}")

        # 使用服务层
        persona_service = PersonaService(db)

        # 检查人设卡是否存在
        pc = persona_service.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 验证权限：公开人设卡任何人都可以下载，私有人设卡只有上传者和管理员可以下载
        if not pc.is_public and pc.uploader_id != user_id and not current_user.get("is_admin", False):
            raise AuthorizationError("没有权限下载此人设卡")

        # 获取文件信息（使用文件服务）
        file_service = FileService(db)
        file_info = file_service.get_persona_card_file_path(pc_id, file_id)
        if not file_info:
            raise NotFoundError("文件不存在")

        # 构建完整的文件路径
        file_full_path = os.path.join(pc.base_path, file_info.get("file_path"))
        if not os.path.exists(file_full_path):
            raise NotFoundError("文件不存在")

        # 记录文件操作成功
        log_file_operation(
            app_logger, "download", f"persona_card/{pc_id}/file/{file_id}", user_id=user_id, success=True
        )

        # 返回文件响应，使用原始文件名
        return FileResponse(
            path=file_full_path, filename=file_info.get("file_name"), media_type="application/octet-stream"
        )

    except (NotFoundError, AuthorizationError, FileOperationError):
        raise
    except Exception as e:
        log_exception(app_logger, "Download persona card file error", exception=e)
        log_file_operation(
            app_logger,
            "download",
            f"persona_card/{pc_id}/file/{file_id}",
            user_id=user_id,
            success=False,
            error_message=str(e),
        )
        raise APIError("下载文件失败") from e
