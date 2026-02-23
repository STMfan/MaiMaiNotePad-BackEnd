"""
知识库路由模块

处理知识库相关的API端点，包括：
- 上传知识库
- 查询知识库（公开、个人、详情）
- 编辑知识库
- 删除知识库
- 收藏/取消收藏知识库
- 下载知识库
"""

import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status as HTTPStatus, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.response_util import Success, Page
from app.core.error_handlers import (
    APIError,
    ValidationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    FileOperationError,
    DatabaseError,
)

# 导入错误处理和日志记录模块
from app.core.logging import app_logger, log_exception, log_file_operation, log_database_operation
from app.models.schemas import KnowledgeBaseUpdate
from app.models.database import KnowledgeBase
from app.api.deps import get_current_user
from app.core.database import get_db
from app.services.knowledge_service import KnowledgeService
from app.services.file_service import FileService, FileValidationError, FileDatabaseError

# 创建路由器
router = APIRouter()


# 知识库相关路由（上传、查询、编辑、删除等）


def kb_to_dict(kb) -> dict:
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "uploader_id": kb.uploader_id,
        "author": getattr(kb, "uploader", None).username if getattr(kb, "uploader", None) else None,
        "author_id": kb.uploader_id,
        "copyright_owner": kb.copyright_owner,
        "content": kb.content,
        "tags": kb.tags,
        "star_count": kb.star_count,
        "downloads": kb.downloads,
        "base_path": kb.base_path,
        "is_public": kb.is_public,
        "is_pending": kb.is_pending,
        "rejection_reason": kb.rejection_reason,
        "version": kb.version,
        "created_at": kb.created_at.isoformat() if kb.created_at else None,
        "updated_at": kb.updated_at.isoformat() if kb.updated_at else None,
    }


# 知识库相关路由
@router.post("/upload")
async def upload_knowledge_base(
    files: List[UploadFile] = File(...),
    name: str = Form(...),
    description: str = Form(...),
    copyright_owner: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    is_public: Optional[bool] = Form(False),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传知识库

    业务规则：
    - 未显式声明公开：默认作为私有上传（is_public=False, is_pending=False）
    - is_public=True：视为申请公开，进入审核队列（is_public=False, is_pending=True）
    """
    user_id = current_user.get("id", "")
    username = current_user.get("username", "")
    try:
        app_logger.info(f"Upload knowledge base: user_id={user_id}, name={name}")

        # 验证输入参数
        _validate_upload_params(name, description, files)

        # 使用服务层检查重名
        knowledge_service = KnowledgeService(db)
        if knowledge_service.check_duplicate_name(name, user_id):
            raise ValidationError("您已经创建过同名的知识库")

        # 准备文件数据
        file_data = await _prepare_file_data(files)

        # 使用 FileService 上传知识库
        file_service = FileService(db)
        kb = file_service.upload_knowledge_base(
            files=file_data,
            name=name,
            description=description,
            uploader_id=user_id,
            copyright_owner=copyright_owner if copyright_owner else username,
            content=content,
            tags=tags,
        )

        # 设置知识库可见性状态
        _set_kb_visibility(kb, is_public, db)

        # 记录文件操作成功
        log_file_operation(app_logger, "upload", f"knowledge_base/{kb.id}", user_id=user_id, success=True)

        # 记录数据库操作成功
        log_database_operation(app_logger, "create", "knowledge_base", record_id=kb.id, user_id=user_id, success=True)

        return Success(message="知识库上传成功", data=kb_to_dict(kb))

    except (ValidationError, FileOperationError, DatabaseError, HTTPException):
        raise
    except FileValidationError as e:
        raise ValidationError(e.message)
    except FileDatabaseError as e:
        raise DatabaseError(e.message)
    except Exception as e:
        log_exception(app_logger, "Upload knowledge base error", exception=e)
        log_file_operation(
            app_logger, "upload", f"knowledge_base/{name}", user_id=user_id, success=False, error_message=str(e)
        )
        raise APIError("上传知识库失败")


def _validate_upload_params(name: str, description: str, files: List[UploadFile]) -> None:
    """验证上传参数

    Args:
        name: 知识库名称
        description: 知识库描述
        files: 上传的文件列表

    Raises:
        ValidationError: 参数验证失败
    """
    if not name or not description:
        raise ValidationError("名称和描述不能为空")

    if not files:
        raise ValidationError("至少需要上传一个文件")


async def _prepare_file_data(files: List[UploadFile]) -> List[tuple[str, bytes]]:
    """准备文件数据

    Args:
        files: 上传的文件列表

    Returns:
        文件数据列表，每个元素为 (文件名, 文件内容) 元组
    """
    file_data: List[tuple[str, bytes]] = []
    for file in files:
        content_bytes = await file.read()
        file_data.append((file.filename, content_bytes))
        await file.seek(0)  # 重置文件指针以防后续使用
    return file_data


def _set_kb_visibility(kb: KnowledgeBase, is_public: bool, db: Session) -> None:
    """设置知识库可见性状态

    根据是否公开调整状态：
    - 私有：直接可用，不进入审核（is_public=False, is_pending=False）
    - 申请公开：进入审核列表（is_public=False, is_pending=True）

    Args:
        kb: 知识库对象
        is_public: 是否申请公开
        db: 数据库会话

    Raises:
        DatabaseError: 数据库操作失败
    """
    try:
        if is_public:
            kb.is_public = False
            kb.is_pending = True
        else:
            kb.is_public = False
            kb.is_pending = False

        db.commit()
        db.refresh(kb)
    except Exception as e:
        db.rollback()
        log_exception(app_logger, "Update knowledge base visibility after upload error", exception=e)
        raise DatabaseError("更新知识库可见性状态失败")


@router.get("/public")
async def get_public_knowledge_bases(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    name: str = Query(None, description="按名称搜索"),
    uploader_id: str = Query(None, description="按上传者ID筛选"),
    sort_by: str = Query("created_at", description="排序字段(created_at, updated_at, star_count)"),
    sort_order: str = Query("desc", description="排序顺序(asc, desc)"),
    db: Session = Depends(get_db),
):
    """获取所有公开的知识库，支持分页、搜索、按上传者筛选和排序"""
    try:
        app_logger.info("Get public knowledge bases")

        # 使用服务层
        knowledge_service = KnowledgeService(db)

        # 允许使用用户名作为上传者筛选输入，若传入的不是ID则尝试用户名解析
        if uploader_id:
            uploader_id = knowledge_service.resolve_uploader_id(uploader_id)

        kbs, total = knowledge_service.get_public_knowledge_bases(
            page=page, page_size=page_size, name=name, uploader_id=uploader_id, sort_by=sort_by, sort_order=sort_order
        )
        return Page(
            data=[kb_to_dict(kb) for kb in kbs],
            message="获取公开知识库成功",
            total=total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        log_exception(app_logger, "Get public knowledge bases error", exception=e)
        raise APIError("获取公开知识库失败")


@router.get("/{kb_id}")
async def get_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    """获取知识库基本信息"""
    try:
        app_logger.info(f"Get knowledge base: kb_id={kb_id}")

        # 使用服务层
        knowledge_service = KnowledgeService(db)

        # 检查知识库是否存在
        kb = knowledge_service.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        kb_dict = kb_to_dict(kb)

        files = knowledge_service.get_files_by_knowledge_base_id(kb_id)
        kb_dict["files"] = (
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

        return Success(message="获取知识库成功", data=kb_dict)

    except NotFoundError:
        raise
    except Exception as e:
        log_exception(app_logger, "Get knowledge base error", exception=e)
        raise APIError("获取知识库失败")


@router.get("/{kb_id}/starred")
async def check_knowledge_starred(
    kb_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """检查知识库是否已被当前用户Star"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Check knowledge starred: kb_id={kb_id}, user_id={user_id}")

        knowledge_service = KnowledgeService(db)
        starred = knowledge_service.is_starred(user_id, kb_id)

        return Success(message="检查Star状态成功", data={"starred": starred})
    except Exception as e:
        log_exception(app_logger, "Check knowledge starred error", exception=e)
        raise APIError("检查Star状态失败")


@router.get("/user/{user_id}")
async def get_user_knowledge_bases(
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
    """获取指定用户上传的知识库"""
    current_user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Get user knowledge bases: user_id={user_id}, requester={current_user_id}")

        # 使用服务层
        knowledge_service = KnowledgeService(db)
        kbs, total = knowledge_service.get_user_knowledge_bases(
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
            data=[kb_to_dict(kb) for kb in kbs],
            page=page,
            page_size=page_size,
            total=total,
            message="获取用户知识库成功",
        )

    except (AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get user knowledge bases error", exception=e)
        raise APIError("获取用户知识库失败")


@router.post("/{kb_id}/star")
async def star_knowledge_base(
    kb_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Star知识库"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Star knowledge base: kb_id={kb_id}, user_id={user_id}")

        # 使用服务层
        knowledge_service = KnowledgeService(db)

        operation = "add"
        message = "Star"

        # 检查知识库是否存在
        kb = knowledge_service.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        is_star = knowledge_service.is_starred(user_id, kb_id)
        if not is_star:
            # 添加Star记录
            success = knowledge_service.add_star(user_id, kb_id)
            if not success:
                raise ConflictError("已经Star过了")
        else:
            # 移除Star记录
            success = knowledge_service.remove_star(user_id, kb_id)
            if not success:
                raise NotFoundError("未找到Star记录")
            operation = "delete"
            message = "取消Star"

        # 记录数据库操作成功
        log_database_operation(
            app_logger, operation, "star", record_id=f"{user_id}_{kb_id}", user_id=user_id, success=True
        )

        return Success(message=message + "成功")
    except (NotFoundError, ConflictError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Star knowledge base error", exception=e)
        log_database_operation(app_logger, operation, "star", user_id=user_id, success=False, error_message=str(e))
        raise APIError(message + "知识库失败")


@router.delete("/{kb_id}/star")
async def unstar_knowledge_base(
    kb_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """取消Star知识库"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Unstar knowledge base: kb_id={kb_id}, user_id={user_id}")

        # 使用服务层
        knowledge_service = KnowledgeService(db)

        # 检查知识库是否存在
        kb = knowledge_service.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 移除Star记录
        success = knowledge_service.remove_star(user_id, kb_id)
        if not success:
            raise NotFoundError("未找到Star记录")

        # 记录数据库操作成功
        log_database_operation(
            app_logger, "delete", "star", record_id=f"{user_id}_{kb_id}", user_id=user_id, success=True
        )

        return Success(message="取消Star成功")
    except (NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Unstar knowledge base error", exception=e)
        log_database_operation(app_logger, "delete", "star", user_id=user_id, success=False, error_message=str(e))
        raise APIError("取消Star知识库失败")


@router.put("/{kb_id}")
async def update_knowledge_base(
    kb_id: str,
    update_data: KnowledgeBaseUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改知识库的基本信息（补充说明在公开/审核中也允许修改）"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Update knowledge base: kb_id={kb_id}, user_id={user_id}")

        knowledge_service = KnowledgeService(db)
        kb = _validate_kb_for_update(knowledge_service, kb_id, user_id, current_user)

        update_dict = _prepare_update_dict(update_data, kb, current_user)
        _apply_kb_updates(kb, update_dict, db)

        log_database_operation(app_logger, "update", "knowledge_base", record_id=kb_id, user_id=user_id, success=True)
        return Success(message="修改知识库成功", data=kb_to_dict(kb))

    except (NotFoundError, AuthorizationError, ValidationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Update knowledge base error", exception=e)
        log_database_operation(
            app_logger,
            "update",
            "knowledge_base",
            record_id=kb_id,
            user_id=user_id,
            success=False,
            error_message=str(e),
        )
        raise APIError("修改知识库失败")


def _validate_kb_for_update(
    knowledge_service: KnowledgeService, kb_id: str, user_id: str, current_user: dict
) -> KnowledgeBase:
    """验证知识库是否可以更新

    Args:
        knowledge_service: 知识库服务实例
        kb_id: 知识库ID
        user_id: 用户ID
        current_user: 当前用户信息

    Returns:
        知识库对象

    Raises:
        NotFoundError: 知识库不存在
        AuthorizationError: 无权限修改
    """
    kb = knowledge_service.get_knowledge_base_by_id(kb_id)
    if not kb:
        raise NotFoundError("知识库不存在")

    # 验证权限：只有上传者和管理员可以修改
    if (
        kb.uploader_id != user_id
        and not current_user.get("is_admin", False)
        and not current_user.get("is_moderator", False)
    ):
        raise AuthorizationError("是你的知识库吗你就改")

    return kb


def _prepare_update_dict(update_data: KnowledgeBaseUpdate, kb: KnowledgeBase, current_user: dict) -> dict:
    """准备更新字典并验证权限

    Args:
        update_data: 更新数据
        kb: 知识库对象
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

    # 仅私有知识库允许修改基础信息和文件；
    # 公开或审核中的知识库仅允许修改补充说明（content）
    if kb.is_public or kb.is_pending:
        _validate_public_kb_updates(update_dict)

    # 移除不允许通过该接口修改的字段
    update_dict.pop("copyright_owner", None)
    update_dict.pop("name", None)

    # 验证 is_public 修改权限
    if not (kb.is_public or kb.is_pending):
        _validate_public_status_change(update_dict, current_user)

    return update_dict


def _validate_public_kb_updates(update_dict: dict) -> None:
    """验证公开或审核中的知识库更新

    Args:
        update_dict: 更新字典

    Raises:
        AuthorizationError: 尝试修改不允许的字段
    """
    allowed_fields = {"content"}
    disallowed_fields = [key for key in update_dict.keys() if key not in allowed_fields]
    if disallowed_fields:
        raise AuthorizationError("公开或审核中的知识库仅允许修改补充说明")


def _validate_public_status_change(update_dict: dict, current_user: dict) -> None:
    """验证公开状态修改权限

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


def _apply_kb_updates(kb: KnowledgeBase, update_dict: dict, db: Session) -> None:
    """应用知识库更新

    Args:
        kb: 知识库对象
        update_dict: 更新字典
        db: 数据库会话
    """
    tags_value = update_dict.get("tags", None)
    if tags_value is not None:
        if isinstance(tags_value, list):
            cleaned_tags = []
            for item in tags_value:
                if item is None:
                    continue
                text = str(item).strip()
                if text:
                    cleaned_tags.append(text)
            update_dict["tags"] = ",".join(cleaned_tags) if cleaned_tags else None
        elif isinstance(tags_value, str):
            normalized = tags_value.replace("，", ",")
            parts = [part.strip() for part in normalized.split(",") if part.strip()]
            update_dict["tags"] = ",".join(parts) if parts else None

    for key, value in update_dict.items():
        if hasattr(kb, key):
            setattr(kb, key, value)

    if any(field != "content" for field in update_dict.keys()):
        kb.updated_at = datetime.now()

    db.commit()
    db.refresh(kb)


@router.post("/{kb_id}/files")
async def add_files_to_knowledge_base(
    kb_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """新增知识库中的文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Add files to knowledge base: kb_id={kb_id}, user_id={user_id}")

        # 验证文件列表
        if not files:
            raise ValidationError("至少需要上传一个文件")

        # 使用服务层检查知识库是否存在
        knowledge_service = KnowledgeService(db)
        kb = knowledge_service.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 验证权限和状态
        _validate_kb_for_file_addition(kb, user_id, current_user)

        # 准备文件数据
        file_data = await _prepare_file_data(files)

        # 使用 FileService 添加文件
        file_service = FileService(db)
        updated_kb = file_service.add_files_to_knowledge_base(kb_id, file_data, user_id)

        if not updated_kb:
            raise FileOperationError("添加文件失败")

        # 记录文件操作成功
        log_file_operation(app_logger, "add_files", f"knowledge_base/{kb_id}", user_id=user_id, success=True)

        # 记录数据库操作成功
        log_database_operation(app_logger, "update", "knowledge_base", record_id=kb_id, user_id=user_id, success=True)

        return Success(message="文件添加成功")

    except (NotFoundError, AuthorizationError, ValidationError, FileOperationError, DatabaseError):
        raise
    except FileValidationError as e:
        raise ValidationError(e.message)
    except FileDatabaseError as e:
        raise DatabaseError(e.message)
    except Exception as e:
        log_exception(app_logger, "Add files to knowledge base error", exception=e)
        log_file_operation(
            app_logger, "add_files", f"knowledge_base/{kb_id}", user_id=user_id, success=False, error_message=str(e)
        )
        raise APIError("添加文件失败")


def _validate_kb_for_file_addition(kb: KnowledgeBase, user_id: str, current_user: dict) -> None:
    """验证知识库是否允许添加文件

    Args:
        kb: 知识库对象
        user_id: 当前用户ID
        current_user: 当前用户信息

    Raises:
        AuthorizationError: 权限验证失败
    """
    # 验证权限：只有上传者和管理员可以添加文件
    if (
        kb.uploader_id != user_id
        and not current_user.get("is_admin", False)
        and not current_user.get("is_moderator", False)
    ):
        raise AuthorizationError("是你的知识库吗你就加")

    # 仅私有知识库允许追加文件，公开或审核中的知识库不允许修改文件
    if kb.is_public or kb.is_pending:
        raise AuthorizationError("公开或审核中的知识库不允许修改文件")


@router.delete("/{kb_id}/{file_id}")
async def delete_files_from_knowledge_base(
    kb_id: str, file_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """删除知识库中的文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Delete files from knowledge base: kb_id={kb_id}, user_id={user_id}")

        knowledge_service = KnowledgeService(db)
        _ = _validate_kb_for_file_deletion(knowledge_service, kb_id, user_id, current_user)

        if not file_id:
            return Success(message="文件删除成功")

        file_service = FileService(db)
        _delete_file_from_kb(file_service, kb_id, file_id, user_id)

        knowledge_deleted = _cleanup_empty_kb_if_needed(knowledge_service, file_service, kb_id, user_id)

        _log_file_deletion_success(kb_id, user_id, knowledge_deleted)

        message = "最后一个文件删除，知识库已自动删除" if knowledge_deleted else "文件删除成功"
        return Success(message=message)

    except (NotFoundError, AuthorizationError, ValidationError, FileOperationError, DatabaseError):
        raise
    except FileValidationError as e:
        raise ValidationError(e.message)
    except FileDatabaseError as e:
        raise DatabaseError(e.message)
    except Exception as e:
        log_exception(app_logger, "Delete files from knowledge base error", exception=e)
        log_file_operation(
            app_logger, "delete_files", f"knowledge_base/{kb_id}", user_id=user_id, success=False, error_message=str(e)
        )
        raise APIError("删除文件失败")


def _validate_kb_for_file_deletion(
    knowledge_service: KnowledgeService, kb_id: str, user_id: str, current_user: dict
) -> KnowledgeBase:
    """验证知识库是否可以删除文件

    Args:
        knowledge_service: 知识库服务实例
        kb_id: 知识库ID
        user_id: 用户ID
        current_user: 当前用户信息

    Returns:
        知识库对象

    Raises:
        NotFoundError: 知识库不存在
        AuthorizationError: 无权限或知识库状态不允许删除
    """
    kb = knowledge_service.get_knowledge_base_by_id(kb_id)
    if not kb:
        raise NotFoundError("知识库不存在")

    # 验证权限：只有上传者和管理员可以删除文件
    if (
        kb.uploader_id != user_id
        and not current_user.get("is_admin", False)
        and not current_user.get("is_moderator", False)
    ):
        raise AuthorizationError("是你的知识库吗你就删")

    # 仅私有知识库允许删除文件，公开或审核中的知识库不允许修改文件
    if kb.is_public or kb.is_pending:
        raise AuthorizationError("公开或审核中的知识库不允许修改文件")

    return kb


def _delete_file_from_kb(file_service: FileService, kb_id: str, file_id: str, user_id: str) -> None:
    """从知识库中删除文件

    Args:
        file_service: 文件服务实例
        kb_id: 知识库ID
        file_id: 文件ID
        user_id: 用户ID

    Raises:
        FileOperationError: 删除文件失败
    """
    success = file_service.delete_file_from_knowledge_base(kb_id, file_id, user_id)
    if not success:
        raise FileOperationError("删除文件失败")


def _cleanup_empty_kb_if_needed(
    knowledge_service: KnowledgeService, file_service: FileService, kb_id: str, user_id: str
) -> bool:
    """如果知识库没有剩余文件，则自动删除整个知识库

    Args:
        knowledge_service: 知识库服务实例
        file_service: 文件服务实例
        kb_id: 知识库ID
        user_id: 用户ID

    Returns:
        是否删除了知识库

    Raises:
        FileOperationError: 删除知识库文件失败
        DatabaseError: 删除知识库记录失败
    """
    remaining_files = knowledge_service.get_files_by_knowledge_base_id(kb_id)
    if remaining_files:
        return False

    cleanup_success = file_service.delete_knowledge_base(kb_id, user_id)
    if not cleanup_success:
        raise FileOperationError("删除知识库文件失败")

    if not knowledge_service.delete_knowledge_base(kb_id):
        raise DatabaseError("删除知识库记录失败")

    try:
        knowledge_service.delete_upload_records_by_target(kb_id)
    except Exception as e:
        app_logger.warning(f"删除知识库上传记录失败: {str(e)}")

    return True


def _log_file_deletion_success(kb_id: str, user_id: str, knowledge_deleted: bool) -> None:
    """记录文件删除成功的日志

    Args:
        kb_id: 知识库ID
        user_id: 用户ID
        knowledge_deleted: 是否删除了整个知识库
    """
    log_file_operation(app_logger, "delete_files", f"knowledge_base/{kb_id}", user_id=user_id, success=True)
    log_database_operation(app_logger, "update", "knowledge_base", record_id=kb_id, user_id=user_id, success=True)

    if knowledge_deleted:
        log_file_operation(app_logger, "delete", f"knowledge_base/{kb_id}", user_id=user_id, success=True)
        log_database_operation(app_logger, "delete", "knowledge_base", record_id=kb_id, user_id=user_id, success=True)


@router.get("/{kb_id}/download")
async def download_knowledge_base_files(
    kb_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """下载知识库的所有文件压缩包"""
    try:
        # 使用服务层
        knowledge_service = KnowledgeService(db)

        # 使用 FileService 创建ZIP文件
        file_service = FileService(db)
        zip_result = file_service.create_knowledge_base_zip(kb_id)
        zip_path = zip_result["zip_path"]
        zip_filename = zip_result["zip_filename"]

        # 使用原子操作更新下载计数器
        success = knowledge_service.increment_downloads(kb_id)
        if not success:
            # 如果更新计数器失败，记录日志但不影响下载
            app_logger.warning(f"更新知识库下载计数器失败: kb_id={kb_id}")

        # 返回文件下载响应
        return FileResponse(path=zip_path, filename=zip_filename, media_type="application/zip")

    except HTTPException:
        raise
    except FileValidationError as e:
        raise HTTPException(status_code=HTTPStatus.HTTP_404_NOT_FOUND, detail=e.message)
    except FileDatabaseError as e:
        raise HTTPException(status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"下载失败: {str(e)}")


@router.get("/{kb_id}/file/{file_id}")
async def download_knowledge_base_file(
    kb_id: str, file_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """下载知识库中的单个文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Download knowledge base file: kb_id={kb_id}, file_id={file_id}, user_id={user_id}")

        # 使用服务层
        knowledge_service = KnowledgeService(db)

        # 检查知识库是否存在
        kb = knowledge_service.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 验证权限：公开知识库任何人都可以下载，私有知识库只有上传者和管理员可以下载
        if not kb.is_public and kb.uploader_id != user_id and not current_user.get("is_admin", False):
            raise AuthorizationError("没有权限下载此知识库")

        # 获取文件信息
        file_service = FileService(db)
        file_info = file_service.get_knowledge_base_file_path(kb_id, file_id)
        if not file_info:
            raise NotFoundError("文件不存在")

        # 构建完整的文件路径
        file_full_path = os.path.join(kb.base_path, file_info.get("file_path"))
        if not os.path.exists(file_full_path):
            raise NotFoundError("文件不存在")

        # 记录文件操作成功
        log_file_operation(
            app_logger, "download", f"knowledge_base/{kb_id}/file/{file_id}", user_id=user_id, success=True
        )

        # 返回文件响应，使用原始文件名
        return FileResponse(
            path=file_full_path, filename=file_info.get("file_name"), media_type="application/octet-stream"
        )

    except (NotFoundError, AuthorizationError, FileOperationError):
        raise
    except FileValidationError as e:
        raise NotFoundError(e.message)
    except FileDatabaseError as e:
        raise FileOperationError(e.message)
    except Exception as e:
        log_exception(app_logger, "Download knowledge base file error", exception=e)
        log_file_operation(
            app_logger,
            "download",
            f"knowledge_base/{kb_id}/file/{file_id}",
            user_id=user_id,
            success=False,
            error_message=str(e),
        )
        raise APIError("下载文件失败")


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """删除整个知识库"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Delete knowledge base: kb_id={kb_id}, user_id={user_id}")

        # 使用服务层检查知识库是否存在
        knowledge_service = KnowledgeService(db)
        kb = knowledge_service.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 验证删除权限
        _validate_kb_deletion_permission(kb, user_id, current_user)

        # 删除文件和数据库记录
        file_service = FileService(db)
        _delete_kb_files_and_records(kb_id, user_id, file_service, knowledge_service)

        # 记录文件操作成功
        log_file_operation(app_logger, "delete", f"knowledge_base/{kb_id}", user_id=user_id, success=True)

        # 记录数据库操作成功
        log_database_operation(app_logger, "delete", "knowledge_base", record_id=kb_id, user_id=user_id, success=True)

        return Success(message="知识库删除成功")

    except (NotFoundError, AuthorizationError, FileOperationError, DatabaseError):
        raise
    except FileValidationError as e:
        raise NotFoundError(e.message)
    except FileDatabaseError as e:
        raise FileOperationError(e.message)
    except Exception as e:
        log_exception(app_logger, "Delete knowledge base error", exception=e)
        log_file_operation(
            app_logger, "delete", f"knowledge_base/{kb_id}", user_id=user_id, success=False, error_message=str(e)
        )
        raise APIError("删除知识库失败")


def _validate_kb_deletion_permission(kb: KnowledgeBase, user_id: str, current_user: dict) -> None:
    """验证知识库删除权限

    Args:
        kb: 知识库对象
        user_id: 当前用户ID
        current_user: 当前用户信息

    Raises:
        AuthorizationError: 权限验证失败
    """
    if kb.uploader_id != user_id and not current_user.get("is_admin", False):
        raise AuthorizationError("没有权限删除此知识库")


def _delete_kb_files_and_records(
    kb_id: str, user_id: str, file_service: FileService, knowledge_service: KnowledgeService
) -> None:
    """删除知识库文件和数据库记录

    Args:
        kb_id: 知识库ID
        user_id: 用户ID
        file_service: 文件服务
        knowledge_service: 知识库服务

    Raises:
        FileOperationError: 文件删除失败
        DatabaseError: 数据库删除失败
    """
    # 删除知识库文件和目录
    success = file_service.delete_knowledge_base(kb_id, user_id)
    if not success:
        raise FileOperationError("删除知识库文件失败")

    # 删除数据库记录
    if not knowledge_service.delete_knowledge_base(kb_id):
        raise DatabaseError("删除知识库记录失败")

    # 删除相关的上传记录
    try:
        knowledge_service.delete_upload_records_by_target(kb_id)
    except Exception as e:
        app_logger.warning(f"删除知识库上传记录失败: {str(e)}")
