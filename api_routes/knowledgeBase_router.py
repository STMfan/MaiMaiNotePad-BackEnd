import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status as HTTPStatus, UploadFile, File, Form, Query
from fastapi.responses import FileResponse

from api_routes.response_util import Success, Page
from database_models import sqlite_db_manager
from error_handlers import (
    APIError, ValidationError,
    AuthorizationError, NotFoundError, ConflictError,
    FileOperationError, DatabaseError
)
from file_upload import file_upload_service
# 导入错误处理和日志记录模块
from logging_config import app_logger, log_exception, log_file_operation, log_database_operation
from models import (
    KnowledgeBaseUpdate
)
from user_management import get_current_user

# 创建路由器
knowledgeBase_router = APIRouter()

# 使用SQLite数据库管理器
db_manager = sqlite_db_manager


# 知识库相关路由
@knowledgeBase_router.post("/knowledge/upload")
async def upload_knowledge_base(
        files: List[UploadFile] = File(...),
        name: str = Form(...),
        description: str = Form(...),
        copyright_owner: Optional[str] = Form(None),
        content: Optional[str] = Form(None),
        tags: Optional[str] = Form(None),
        is_public: Optional[bool] = Form(False),
        current_user: dict = Depends(get_current_user)
):
    """上传知识库

    业务规则：
    - 未显式声明公开：默认作为私有上传（is_public=False, is_pending=False）
    - is_public=True：视为申请公开，进入审核队列（is_public=False, is_pending=True）
    """
    user_id = current_user.get("id", "")
    username = current_user.get("username", "")
    try:
        app_logger.info(
            f"Upload knowledge base: user_id={user_id}, name={name}")

        # 验证输入参数
        if not name or not description:
            raise ValidationError("名称和描述不能为空")

        if not files:
            raise ValidationError("至少需要上传一个文件")

        # 检查同一用户是否已有同名知识库
        existing_kbs = db_manager.get_knowledge_bases_by_uploader(user_id)
        for existing_kb in existing_kbs:
            if existing_kb.name == name:
                raise ValidationError("您已经创建过同名的知识库")

        # 上传知识库
        kb = await file_upload_service.upload_knowledge_base(
            files=files,
            name=name,
            description=description,
            uploader_id=user_id,
            copyright_owner=copyright_owner if copyright_owner else username,
            content=content,
            tags=tags
        )

        # 根据是否公开调整状态：
        # - 私有：直接可用，不进入审核（is_public=False, is_pending=False）
        # - 申请公开：进入审核列表（is_public=False, is_pending=True）
        try:
            kb_dict = kb.to_dict()

            # 避免将已序列化的时间字段写回数据库，交由 ORM 自己管理
            kb_dict.pop("created_at", None)
            kb_dict.pop("updated_at", None)

            if is_public:
                kb_dict["is_public"] = False
                kb_dict["is_pending"] = True
                upload_status = "pending"
            else:
                kb_dict["is_public"] = False
                kb_dict["is_pending"] = False
                upload_status = "success"

            kb = db_manager.save_knowledge_base(kb_dict)
            if not kb:
                raise DatabaseError("保存知识库失败")
        except Exception as e:
            log_exception(app_logger, "Update knowledge base visibility after upload error", exception=e)
            raise DatabaseError("更新知识库可见性状态失败")

        # 创建上传记录
        try:
            db_manager.create_upload_record(
                uploader_id=user_id,
                target_id=kb.id,
                target_type="knowledge",
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
            f"knowledge_base/{kb.id}",
            user_id=user_id,
            success=True
        )

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "create",
            "knowledge_base",
            record_id=kb.id,
            user_id=user_id,
            success=True
        )

        return Success(
            message="知识库上传成功",
            data=kb.to_dict()
        )

    except (ValidationError, FileOperationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Upload knowledge base error", exception=e)
        log_file_operation(
            app_logger,
            "upload",
            f"knowledge_base/{name}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("上传知识库失败")


@knowledgeBase_router.get("/knowledge/public")
async def get_public_knowledge_bases(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=100, description="每页数量"),
        name: str = Query(None, description="按名称搜索"),
        uploader_id: str = Query(None, description="按上传者ID筛选"),
        sort_by: str = Query(
            "created_at", description="排序字段(created_at, updated_at, star_count)"),
        sort_order: str = Query("desc", description="排序顺序(asc, desc)")
):
    """获取所有公开的知识库，支持分页、搜索、按上传者筛选和排序"""
    try:
        app_logger.info("Get public knowledge bases")

        # 允许使用用户名作为上传者筛选输入，若传入的不是ID则尝试用户名解析
        if uploader_id:
            try:
                # 如果找不到对应用户ID且输入不是标准UUID，则尝试按用户名查找
                user = db_manager.get_user_by_id(uploader_id)
                if not user:
                    user = db_manager.get_user_by_username(uploader_id)
                if user:
                    uploader_id = user.id
                else:
                    uploader_id = None
            except Exception:
                uploader_id = None

        kbs, total = db_manager.get_public_knowledge_bases(
            page=page,
            page_size=page_size,
            name=name,
            uploader_id=uploader_id,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return Page(
            data=[kb.to_dict() for kb in kbs],
            message="获取公开知识库成功",
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        log_exception(
            app_logger, "Get public knowledge bases error", exception=e)
        raise APIError("获取公开知识库失败")


@knowledgeBase_router.get("/knowledge/{kb_id}")
async def get_knowledge_base(kb_id: str):
    """获取知识库基本信息"""
    try:
        app_logger.info(f"Get knowledge base: kb_id={kb_id}")

        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        kb_dict = kb.to_dict(include_files=True)
        return Success(
            message="获取知识库成功",
            data=kb_dict
        )

    except NotFoundError:
        raise
    except Exception as e:
        log_exception(app_logger, "Get knowledge base error", exception=e)
        raise APIError("获取知识库失败")


@knowledgeBase_router.get("/knowledge/{kb_id}/starred")
async def check_knowledge_starred(
        kb_id: str,
        current_user: dict = Depends(get_current_user)
):
    """检查知识库是否已被当前用户Star"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Check knowledge starred: kb_id={kb_id}, user_id={user_id}")
        starred = db_manager.is_starred(user_id, kb_id, "knowledge")
        return Success(
            message="检查Star状态成功",
            data={"starred": starred}
        )
    except Exception as e:
        log_exception(app_logger, "Check knowledge starred error", exception=e)
        raise APIError("检查Star状态失败")


@knowledgeBase_router.get("/knowledge/user/{user_id}")
async def get_user_knowledge_bases(
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
    """获取指定用户上传的知识库"""
    current_user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Get user knowledge bases: user_id={user_id}, requester={current_user_id}")


        kbs = db_manager.get_knowledge_bases_by_uploader(user_id)

        def match_status(kb):
            if status == "pending":
                return kb.is_pending
            if status == "approved":
                return not kb.is_pending and kb.is_public
            if status == "rejected":
                return not kb.is_pending and (not kb.is_public)
            return True

        # 允许的排序字段
        sort_field_map = {
            "created_at": lambda kb: kb.created_at,
            "updated_at": lambda kb: kb.updated_at,
            "name": lambda kb: kb.name.lower(),
            "downloads": lambda kb: kb.downloads or 0,
            "star_count": lambda kb: kb.star_count or 0,
        }

        filtered = []
        for kb in kbs:
            if name and name.lower() not in kb.name.lower():
                continue
            if tag:
                tag_list = []
                if kb.tags:
                    tag_list = kb.tags.split(",") if isinstance(kb.tags, str) else kb.tags
                if not any(tag.lower() in t.lower() for t in tag_list):
                    continue
            if not match_status(kb):
                continue
            filtered.append(kb)

        # 排序
        key_func = sort_field_map.get(sort_by, sort_field_map["created_at"])
        reverse = sort_order.lower() != "asc"
        filtered.sort(key=key_func, reverse=reverse)

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = filtered[start:end]

        return Page(
            data=[kb.to_dict() for kb in page_items],
            message="获取用户知识库成功",
            total=total,
            page=page,
            page_size=page_size
        )

    except (AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(
            app_logger, "Get user knowledge bases error", exception=e)
        raise APIError("获取用户知识库失败")


@knowledgeBase_router.post("/knowledge/{kb_id}/star")
async def star_knowledge_base(
        kb_id: str,
        current_user: dict = Depends(get_current_user)
):
    """Star知识库"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Star knowledge base: kb_id={kb_id}, user_id={user_id}")

        # 个人认为原先将Star和取消Star知识库分为两个接口不太合理，故修改为了请求Star接口时，如果已经Star过，则取消Star，否则Star

        operation = "add"
        message = "Star"
        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        is_star = db_manager.is_starred(user_id, kb_id, "knowledge")
        if not is_star:
            # 添加Star记录
            success = db_manager.add_star(user_id, kb_id, "knowledge")
            if not success:
                raise ConflictError("已经Star过了")
        else:
            # 移除Star记录
            success = db_manager.remove_star(user_id, kb_id, "knowledge")
            if not success:
                raise NotFoundError("未找到Star记录")
            operation = "delete"
            message = "取消Star"

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            operation,
            "star",
            record_id=f"{user_id}_{kb_id}",
            user_id=user_id,
            success=True
        )

        return Success(
            message=message + "成功"
        )
    except (NotFoundError, ConflictError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Star knowledge base error", exception=e)
        log_database_operation(
            app_logger,
            operation,
            "star",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError(message + "知识库失败")


@knowledgeBase_router.delete("/knowledge/{kb_id}/star")
async def unstar_knowledge_base(
        kb_id: str,
        current_user: dict = Depends(get_current_user)
):
    """取消Star知识库"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Unstar knowledge base: kb_id={kb_id}, user_id={user_id}")

        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 移除Star记录
        success = db_manager.remove_star(user_id, kb_id, "knowledge")
        if not success:
            raise NotFoundError("未找到Star记录")

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "delete",
            "star",
            record_id=f"{user_id}_{kb_id}",
            user_id=user_id,
            success=True
        )

        return Success(
            message="取消Star成功"
        )
    except (NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Unstar knowledge base error", exception=e)
        log_database_operation(
            app_logger,
            "delete",
            "star",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("取消Star知识库失败")


@knowledgeBase_router.put("/knowledge/{kb_id}")
async def update_knowledge_base(
        kb_id: str,
        update_data: KnowledgeBaseUpdate,
        current_user: dict = Depends(get_current_user)
):
    """修改知识库的基本信息"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Update knowledge base: kb_id={kb_id}, user_id={user_id}")

        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 验证权限：只有上传者和管理员可以修改
        if kb.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get(
                "is_moderator", False):
            raise AuthorizationError("是你的知识库吗你就改")

        # 更新知识库信息
        update_dict = update_data.dict(exclude_unset=True)
        if not update_dict:
            raise ValidationError("没有提供要更新的字段")

        # 业务规则：
        # - 普通用户可以修改名称、描述等基础信息
        # - 普通用户可以将私有知识库标记为待审核（is_pending=True）以申请公开
        # - 只有管理员或审核员可以直接修改 is_public 状态
        if "is_public" in update_dict and not (current_user.get("is_admin", False) or current_user.get("is_moderator", False)):
            raise AuthorizationError("只有管理员可以直接修改公开状态")

        # 更新数据库记录
        for key, value in update_dict.items():
            if hasattr(kb, key):
                setattr(kb, key, value)

        kb.updated_at = datetime.now()

        updated_kb = db_manager.save_knowledge_base(kb.to_dict())
        if not updated_kb:
            raise DatabaseError("更新知识库失败")

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "update",
            "knowledge_base",
            record_id=kb_id,
            user_id=user_id,
            success=True
        )

        return Success(
            message="修改知识库成功",
            data=updated_kb.to_dict()
        )

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
            error_message=str(e)
        )
        raise APIError("修改知识库失败")


@knowledgeBase_router.post("/knowledge/{kb_id}/files")
async def add_files_to_knowledge_base(
        kb_id: str,
        files: List[UploadFile] = File(...),
        current_user: dict = Depends(get_current_user)
):
    """新增知识库中的文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Add files to knowledge base: kb_id={kb_id}, user_id={user_id}")
        if not files:
            raise ValidationError("至少需要上传一个文件")

        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 验证权限：只有上传者和管理员可以添加文件
        if kb.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get(
                "is_moderator", False):
            raise AuthorizationError("是你的知识库吗你就加")

        if not files:
            raise ValidationError("至少需要上传一个文件")

        # 添加文件
        updated_kb = await file_upload_service.add_files_to_knowledge_base(kb_id, files, user_id)

        if not updated_kb:
            raise FileOperationError("添加文件失败")

        # 记录文件操作成功
        log_file_operation(
            app_logger,
            "add_files",
            f"knowledge_base/{kb_id}",
            user_id=user_id,
            success=True
        )

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "update",
            "knowledge_base",
            record_id=kb_id,
            user_id=user_id,
            success=True
        )

        return Success(
            message="文件添加成功",
        )

    except (NotFoundError, AuthorizationError, ValidationError, FileOperationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(
            app_logger, "Add files to knowledge base error", exception=e)
        log_file_operation(
            app_logger,
            "add_files",
            f"knowledge_base/{kb_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("添加文件失败")


@knowledgeBase_router.delete("/knowledge/{kb_id}/{file_id}")
async def delete_files_from_knowledge_base(
        kb_id: str,
        file_id: str,
        current_user: dict = Depends(get_current_user)
):
    """删除知识库中的文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Delete files from knowledge base: kb_id={kb_id}, user_id={user_id}")

        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 验证权限：只有上传者和管理员可以删除文件
        if kb.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get(
                "is_moderator", False):
            raise AuthorizationError("是你的知识库吗你就删")

        if not file_id:
            return Success(
                message="文件删除成功",
            )

        # 删除文件
        success = await file_upload_service.delete_files_from_knowledge_base(kb_id, file_id, user_id)

        if not success:
            raise FileOperationError("删除文件失败")

        knowledge_deleted = False
        # 检查是否还有剩余文件，没有则自动删除整个知识库
        remaining_files = db_manager.get_files_by_knowledge_base_id(kb_id)
        if not remaining_files:
            cleanup_success = await file_upload_service.delete_knowledge_base(kb_id, user_id)
            if not cleanup_success:
                raise FileOperationError("删除知识库文件失败")

            if not db_manager.delete_knowledge_base(kb_id):
                raise DatabaseError("删除知识库记录失败")

            try:
                db_manager.delete_upload_records_by_target(kb_id, "knowledge")
            except Exception as e:
                app_logger.warning(f"删除知识库上传记录失败: {str(e)}")

            knowledge_deleted = True

        # 记录文件操作成功
        log_file_operation(
            app_logger,
            "delete_files",
            f"knowledge_base/{kb_id}",
            user_id=user_id,
            success=True
        )

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "update",
            "knowledge_base",
            record_id=kb_id,
            user_id=user_id,
            success=True
        )

        if knowledge_deleted:
            # 补充记录知识库删除日志
            log_file_operation(
                app_logger,
                "delete",
                f"knowledge_base/{kb_id}",
                user_id=user_id,
                success=True
            )
            log_database_operation(
                app_logger,
                "delete",
                "knowledge_base",
                record_id=kb_id,
                user_id=user_id,
                success=True
            )

        message = "最后一个文件删除，知识库已自动删除" if knowledge_deleted else "文件删除成功"
        return Success(
            message=message,
        )

    except (NotFoundError, AuthorizationError, ValidationError, FileOperationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(
            app_logger, "Delete files from knowledge base error", exception=e)
        log_file_operation(
            app_logger,
            "delete_files",
            f"knowledge_base/{kb_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("删除文件失败")


@knowledgeBase_router.get("/knowledge/{kb_id}/download")
async def download_knowledge_base_files(
        kb_id: str,
        current_user: dict = Depends(get_current_user)
):
    """下载知识库的所有文件压缩包"""
    try:
        # 创建ZIP文件
        zip_result = await file_upload_service.create_knowledge_base_zip(kb_id)
        zip_path = zip_result["zip_path"]
        zip_filename = zip_result["zip_filename"]

        # 使用原子操作更新下载计数器
        success = db_manager.increment_knowledge_base_downloads(kb_id)
        if not success:
            # 如果更新计数器失败，记录日志但不影响下载
            app_logger.warning(f"更新知识库下载计数器失败: kb_id={kb_id}")

        # 返回文件下载响应
        return FileResponse(
            path=zip_path,
            filename=zip_filename,
            media_type='application/zip'
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载失败: {str(e)}"
        )


@knowledgeBase_router.get("/knowledge/{kb_id}/file/{file_id}")
async def download_knowledge_base_file(
        kb_id: str,
        file_id: str,
        current_user: dict = Depends(get_current_user)
):
    """下载知识库中的单个文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Download knowledge base file: kb_id={kb_id}, file_id={file_id}, user_id={user_id}")

        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 验证权限：公开知识库任何人都可以下载，私有知识库只有上传者和管理员可以下载
        if not kb.is_public and kb.uploader_id != user_id and not current_user.get("is_admin", False):
            raise AuthorizationError("没有权限下载此知识库")

        # 获取文件信息
        file_info = await file_upload_service.get_knowledge_base_file_path(kb_id, file_id)
        if not file_info:
            raise NotFoundError("文件不存在")

        # 构建完整的文件路径
        file_full_path = os.path.join(kb.base_path, file_info.get("file_path"))
        if not os.path.exists(file_full_path):
            raise NotFoundError("文件不存在")

        # 记录文件操作成功
        log_file_operation(
            app_logger,
            "download",
            f"knowledge_base/{kb_id}/file/{file_id}",
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
            app_logger, "Download knowledge base file error", exception=e)
        log_file_operation(
            app_logger,
            "download",
            f"knowledge_base/{kb_id}/file/{file_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("下载文件失败")


@knowledgeBase_router.delete("/knowledge/{kb_id}")
async def delete_knowledge_base(
        kb_id: str,
        current_user: dict = Depends(get_current_user)
):
    """删除整个知识库"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Delete knowledge base: kb_id={kb_id}, user_id={user_id}")

        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 验证权限：只有上传者和管理员可以删除知识库
        if kb.uploader_id != user_id and not current_user.get("is_admin", False):
            raise AuthorizationError("没有权限删除此知识库")

        # 删除知识库文件和目录
        success = await file_upload_service.delete_knowledge_base(kb_id, user_id)

        if not success:
            raise FileOperationError("删除知识库文件失败")

        # 删除数据库记录
        if not db_manager.delete_knowledge_base(kb_id):
            raise DatabaseError("删除知识库记录失败")

        # 删除相关的上传记录
        try:
            db_manager.delete_upload_records_by_target(kb_id, "knowledge")
        except Exception as e:
            app_logger.warning(f"删除知识库上传记录失败: {str(e)}")

        # 记录文件操作成功
        log_file_operation(
            app_logger,
            "delete",
            f"knowledge_base/{kb_id}",
            user_id=user_id,
            success=True
        )

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "delete",
            "knowledge_base",
            record_id=kb_id,
            user_id=user_id,
            success=True
        )

        return Success(message="知识库删除成功")

    except (NotFoundError, AuthorizationError, FileOperationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete knowledge base error", exception=e)
        log_file_operation(
            app_logger,
            "delete",
            f"knowledge_base/{kb_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("删除知识库失败")
