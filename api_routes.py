"""
API路由实现
包含知识库、人设卡、用户管理、审核等功能路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import os
from datetime import datetime

from models import (
    KnowledgeBase, PersonaCard, Message, MessageCreate, StarRecord,
    KnowledgeBaseUpdate
)
from database_models import sqlite_db_manager
from file_upload import file_upload_service
from user_management import get_current_user, pwd_context, create_user, get_user_by_username

# 导入错误处理和日志记录模块
from logging_config import app_logger, log_exception, log_api_request, log_file_operation, log_database_operation
from error_handlers import (
    APIError, ValidationError, AuthenticationError,
    AuthorizationError, NotFoundError, ConflictError,
    FileOperationError, DatabaseError
)

# 创建路由器
api_router = APIRouter()

# 使用SQLite数据库管理器
db_manager = sqlite_db_manager

# OAuth2 认证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# 响应模型
class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: str
    uploader_id: str
    copyright_owner: Optional[str]
    star_count: int
    is_public: bool
    is_pending: bool
    base_path: Optional[str]
    created_at: datetime
    updated_at: datetime


class PersonaCardResponse(BaseModel):
    id: str
    name: str
    description: str
    uploader_id: str
    copyright_owner: Optional[str]
    star_count: int
    is_public: bool
    is_pending: bool
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: str
    sender_id: str
    title: str
    content: str
    is_read: bool
    created_at: str


class StarResponse(BaseModel):
    id: str
    target_id: str
    target_type: str
    created_at: str

# 认证相关路由
@api_router.post("/token")
async def login(request: Request):
    """用户登录获取访问令牌，支持JSON和表单数据格式"""
    try:
        # 获取Content-Type
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            # 处理JSON格式
            try:
                data = await request.json()
                username = data.get("username")
                password = data.get("password")
                app_logger.info(f"Login attempt (JSON): username={username}")
            except Exception:
                raise ValidationError("无效的JSON格式")
        elif "application/x-www-form-urlencoded" in content_type:
            # 处理表单格式
            form_data = await request.form()
            username = form_data.get("username")
            password = form_data.get("password")
            app_logger.info(f"Login attempt (Form): username={username}")
        else:
            raise ValidationError("不支持的Content-Type")

        # 验证必填字段
        if not username or not password:
            raise ValidationError("请提供用户名和密码")

        # 导入用户管理模块的验证函数
        from user_management import get_user_by_credentials
        # 导入JWT工具
        from jwt_utils import create_user_token

        # 验证用户凭据
        user = get_user_by_credentials(username, password)

        if user:
            app_logger.info(f"Login successful: username={username}, role={user.role}")

            # 创建JWT访问令牌
            access_token = create_user_token(user.userID, user.username, user.role)

            return {"access_token": access_token, "token_type": "bearer"}

        # 登录失败
        app_logger.warning(f"Login failed: username={username}")
        raise AuthenticationError("用户名或密码错误")

    except AuthenticationError:
        raise
    except Exception as e:
        log_exception(app_logger, "Login error", exception=e)
        raise APIError("登录过程中发生错误")


@api_router.post("/send_verification_code")
async def send_verification_code(
        email: str = Form(...),
):
    try:
        app_logger.info(f"Send verification code: email={email}")

        # 1. 验证邮箱格式
        if "@" not in email:
            raise ValidationError("邮箱格式无效")

        # 2. 检查频率限制
        if not db_manager.check_email_rate_limit(email):
            raise APIError("请求发送验证码过于频繁，请稍后重试")

        # 3. 生成6位随机验证码
        import random
        code = "".join(random.choices("0123456789", k=6))

        # 4. 发送邮件
        email_content = f"mMaiMaiNotePad 验证码为：{code}，有效期为 2 分钟，请尽快使用哦！"
        email_title = "MaiMaiNotePad 验证码"

        from email_service import send_email
        send_email(
            receiver=email,
            subject=email_title,
            content=email_content
        )
        code_id = db_manager.save_verification_code(email, code)

        log_database_operation(
            app_logger,
            "create",
            "verification_code",
            record_id=code_id,
            success=True
        )

        return {"message": "验证码已发送"}

    except Exception as e:
        log_exception(app_logger, "Send verification code error", exception=e)
        raise APIError("发送验证码失败")

@api_router.post("/send_reset_password_code")
async def send_reset_password_code(
        email: str = Form(...),
):
    """发送重置密码验证码"""
    try:
        app_logger.info(f"Send reset password code: email={email}")

        # 1. 验证邮箱格式
        if "@" not in email:
            raise ValidationError("邮箱格式无效")

        # 2. 检查邮箱是否已注册
        user = db_manager.get_user_by_email(email)
        if not user:
            raise ValidationError("该邮箱未注册")

        # 3. 检查频率限制
        if not db_manager.check_email_rate_limit(email):
            raise APIError("请求发送验证码过于频繁，请稍后重试")

        # 4. 生成6位随机验证码
        import random
        code = "".join(random.choices("0123456789", k=6))

        # 5. 发送邮件
        email_content = f"mMaiMaiNotePad 重置密码验证码为：{code}，有效期为 2 分钟，请尽快使用哦！"
        email_title = "MaiMaiNotePad 重置密码"

        from email_service import send_email
        send_email(
            receiver=email,
            subject=email_title,
            content=email_content
        )
        code_id = db_manager.save_verification_code(email, code)

        log_database_operation(
            app_logger,
            "create",
            "reset_password_code",
            record_id=code_id,
            success=True
        )

        return {"message": "重置密码验证码已发送"}

    except Exception as e:
        log_exception(app_logger, "Send reset password code error", exception=e)
        raise APIError("发送重置密码验证码失败")

@api_router.post("/reset_password")
async def reset_password(
        email: str = Form(...),
        verification_code: str = Form(...),
        new_password: str = Form(...)
):
    """通过邮箱验证码重置密码"""
    try:
        app_logger.info(f"Reset password: email={email}")

        # 1. 验证输入参数
        if not email or not verification_code or not new_password:
            raise ValidationError("有未填写的字段")

        # 2. 验证密码长度
        if len(new_password) < 6:
            raise ValidationError("密码长度不能少于6位")

        # 3. 验证邮箱验证码
        if not db_manager.verify_email_code(email, verification_code):
            raise ValidationError("验证码错误或已失效")

        # 4. 更新密码
        if not db_manager.update_user_password(email, new_password):
            raise APIError("重置密码失败，请检查邮箱是否正确")

        log_database_operation(
            app_logger,
            "update",
            "user_password",
            success=True
        )

        return {
            "success": True,
            "message": "密码重置成功"
        }

    except Exception as e:
        log_exception(app_logger, "Reset password error", exception=e)
        raise APIError("重置密码失败")

@api_router.post("/user/register")
async def user_register(
        username: str = Form(...),
        password: str = Form(...),
        email: str = Form(...),
        verification_code: str = Form(...)
):
    try:
        if not username or not password or not email or not verification_code:
            raise ValidationError("有未填写的字段")

        message=db_manager.check_user_register_legality(username, email)
        if message != "ok":
            raise ValidationError(message)

        if not db_manager.verify_email_code(email, verification_code):
            raise ValidationError("验证码错误或已失效")


        new_user = create_user(username, password, email, role="user")
        if not new_user:
            raise APIError("注册失败，系统错误，请稍后重试")

        log_database_operation(
            app_logger,
            "create",
            "user",
            user_id=new_user.userID,
            success=True
        )

        return {
            "success": True,
            "message": "注册成功"
        }

    except Exception as e:
        log_exception(app_logger, "Register user error", exception=e)
        raise APIError("注册用户失败")

@api_router.get("/users/me", response_model=dict)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    try:
        user_id = current_user.get("id", "")
        app_logger.info(f"Get user info: user_id={user_id}")

        return {
            "id": user_id,
            "username": current_user.get("username", ""),
            "email": current_user.get("email", ""),
            "role": current_user.get("role", "user")
        }
    except Exception as e:
        log_exception(app_logger, "Get user info error", exception=e)
        raise APIError("获取用户信息失败")


# 知识库相关路由
@api_router.post("/knowledge/upload", response_model=KnowledgeBaseResponse)
async def upload_knowledge_base(
    files: List[UploadFile] = File(...),
    name: str = Form(...),
    description: str = Form(...),
    copyright_owner: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """上传知识库"""
    user_id = current_user.get("id", "")
    username = current_user.get("username", "")
    try:
        app_logger.info(f"Upload knowledge base: user_id={user_id}, name={name}")

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
            copyright_owner=copyright_owner if copyright_owner else username
        )

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
        
        return KnowledgeBaseResponse(**kb.to_dict())
        
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


@api_router.get("/knowledge/public", response_model=List[KnowledgeBaseResponse])
async def get_public_knowledge_bases():
    """获取所有公开的知识库"""
    try:
        app_logger.info("Get public knowledge bases")

        kbs = db_manager.get_public_knowledge_bases()
        return [KnowledgeBaseResponse(**kb.to_dict()) for kb in kbs]

    except Exception as e:
        log_exception(app_logger, "Get public knowledge bases error", exception=e)
        raise APIError("获取公开知识库失败")


@api_router.get("/knowledge/{kb_id}", response_model=dict)
async def get_knowledge_base(kb_id: str):
    """获取知识库内容"""
    # 这里改成获取知识库基本信息了，下载知识库文件改成其他接口了
    try:
        app_logger.info(f"Get knowledge base content: kb_id={kb_id}")

        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        content = file_upload_service.get_knowledge_base_content(kb_id)

        # 记录文件读取操作
        log_file_operation(
            app_logger,
            "read",
            f"knowledge_base/{kb_id}",
            success=True
        )

        return content

    except (NotFoundError, FileOperationError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get knowledge base content error", exception=e)
        log_file_operation(
            app_logger,
            "read",
            f"knowledge_base/{kb_id}",
            success=False,
            error_message=str(e)
        )
        raise APIError("获取知识库内容失败")


@api_router.get("/knowledge/user/{user_id}", response_model=List[KnowledgeBaseResponse])
async def get_user_knowledge_bases(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取用户上传的知识库"""
    current_user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Get user knowledge bases: user_id={user_id}, requester={current_user_id}")

        # 验证权限：只能查看自己的知识库
        if user_id != current_user_id:
            app_logger.warning(f"Unauthorized access attempt: user={current_user_id} trying to access user={user_id} data")
            raise AuthorizationError("没有权限查看其他用户的上传记录")

        kbs = db_manager.get_knowledge_bases_by_uploader(user_id)
        return [KnowledgeBaseResponse(**kb.to_dict()) for kb in kbs]

    except (AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get user knowledge bases error", exception=e)
        raise APIError("获取用户知识库失败")


@api_router.post("/knowledge/{kb_id}/star")
async def star_knowledge_base(
    kb_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Star知识库"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Star knowledge base: kb_id={kb_id}, user_id={user_id}")

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

        return {"message": message+"成功"}
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
        raise APIError(message+"知识库失败")


@api_router.delete("/knowledge/{kb_id}/star")
async def unstar_knowledge_base(
    kb_id: str,
    current_user: dict = Depends(get_current_user)
):
    """取消Star知识库"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Unstar knowledge base: kb_id={kb_id}, user_id={user_id}")

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

        return {"message": "取消Star成功"}
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


@api_router.put("/knowledge/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    update_data: KnowledgeBaseUpdate,
    current_user: dict = Depends(get_current_user)
):
    """修改知识库的基本信息"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Update knowledge base: kb_id={kb_id}, user_id={user_id}")

        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 验证权限：只有上传者和管理员可以修改
        if kb.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get("is_moderator", False):
            raise AuthorizationError("是你的知识库吗你就改")

        # 更新知识库信息
        update_dict = update_data.dict(exclude_unset=True)
        if not update_dict:
            raise ValidationError("没有提供要更新的字段")

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

        return KnowledgeBaseResponse(**updated_kb.to_dict())

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


@api_router.post("/knowledge/{kb_id}/files")
async def add_files_to_knowledge_base(
    kb_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """新增知识库中的文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Add files to knowledge base: kb_id={kb_id}, user_id={user_id}")

        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 验证权限：只有上传者和管理员可以添加文件
        if kb.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get("is_moderator", False):
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

        return {"message": "文件添加成功"}

    except (NotFoundError, AuthorizationError, ValidationError, FileOperationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Add files to knowledge base error", exception=e)
        log_file_operation(
            app_logger,
            "add_files",
            f"knowledge_base/{kb_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("添加文件失败")


@api_router.delete("/knowledge/{kb_id}/{file_id}")
async def delete_files_from_knowledge_base(
    kb_id: str,
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """删除知识库中的文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Delete files from knowledge base: kb_id={kb_id}, user_id={user_id}")

        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 验证权限：只有上传者和管理员可以删除文件
        if kb.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get("is_moderator", False):
            raise AuthorizationError("是你的知识库吗你就删")

        if not file_id:
            return {"message": "文件删除成功"}

        # 删除文件
        success = await file_upload_service.delete_files_from_knowledge_base(kb_id, file_id, user_id)
        
        if not success:
            raise FileOperationError("删除文件失败")

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

        return {"message": "文件删除成功"}

    except (NotFoundError, AuthorizationError, ValidationError, FileOperationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete files from knowledge base error", exception=e)
        log_file_operation(
            app_logger,
            "delete_files",
            f"knowledge_base/{kb_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("删除文件失败")


@api_router.get("/knowledge/{kb_id}/download")
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载失败: {str(e)}"
        )


@api_router.get("/knowledge/{kb_id}/file/{file_id}")
async def download_knowledge_base_file(
    kb_id: str,
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """下载知识库中的单个文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Download knowledge base file: kb_id={kb_id}, file_id={file_id}, user_id={user_id}")

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
        log_exception(app_logger, "Download knowledge base file error", exception=e)
        log_file_operation(
            app_logger,
            "download",
            f"knowledge_base/{kb_id}/file/{file_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("下载文件失败")


@api_router.delete("/knowledge/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    current_user: dict = Depends(get_current_user)
):
    """删除整个知识库"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Delete knowledge base: kb_id={kb_id}, user_id={user_id}")

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

        return {"message": "知识库删除成功"}

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


# 人设卡相关路由
@api_router.post("/persona/upload", response_model=PersonaCardResponse)
async def upload_persona_card(
    files: List[UploadFile] = File(...),
    name: str = Form(...),
    description: str = Form(...),
    copyright_owner: Optional[str] = Form(None),
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

        # 上传人设卡
        pc = await file_upload_service.upload_persona_card(
            files=files,
            name=name,
            description=description,
            uploader_id=user_id,
            copyright_owner=copyright_owner if copyright_owner else username
        )

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

        return PersonaCardResponse(**pc.to_dict())

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


@api_router.get("/persona/public", response_model=List[PersonaCardResponse])
async def get_public_persona_cards():
    """获取所有公开的人设卡"""
    try:
        app_logger.info("Get public persona cards")

        pcs = db_manager.get_public_persona_cards()
        return [PersonaCardResponse(**pc.to_dict()) for pc in pcs]

    except Exception as e:
        log_exception(app_logger, "Get public persona cards error", exception=e)
        raise APIError("获取公开人设卡失败")


@api_router.get("/persona/{pc_id}", response_model=dict)
async def get_persona_card(pc_id: str):
    """获取人设卡内容"""
    try:
        app_logger.info(f"Get persona card content: pc_id={pc_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        content = file_upload_service.get_persona_card_content(pc_id)

        # 记录文件读取操作
        log_file_operation(
            app_logger,
            "read",
            f"persona_card/{pc_id}",
            success=True
        )

        return content

    except (NotFoundError, FileOperationError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get persona card content error", exception=e)
        log_file_operation(
            app_logger,
            "read",
            f"persona_card/{pc_id}",
            success=False,
            error_message=str(e)
        )
        raise APIError("获取人设卡内容失败")


@api_router.get("/persona/user/{user_id}", response_model=List[PersonaCardResponse])
async def get_user_persona_cards(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取用户上传的人设卡"""
    current_user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Get user persona cards: user_id={user_id}, requester={current_user_id}")

        # 验证权限：只能查看自己的人设卡
        if user_id != current_user_id:
            app_logger.warning(f"Unauthorized access attempt: user={current_user_id} trying to access user={user_id} data")
            raise AuthorizationError("没有权限查看其他用户的上传记录")

        pcs = db_manager.get_persona_cards_by_uploader(user_id)
        return [PersonaCardResponse(**pc.to_dict()) for pc in pcs]

    except (AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get user persona cards error", exception=e)
        raise APIError("获取用户人设卡失败")


@api_router.put("/persona/{pc_id}", response_model=PersonaCardResponse)
async def update_persona_card(
    pc_id: str,
    name: str = Form(...),
    description: str = Form(...),
    copyright_owner: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """修改人设卡信息"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Update persona card: pc_id={pc_id}, user_id={user_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 验证权限：只有上传者和管理员可以修改人设卡
        if pc.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get("is_moderator", False):
            raise AuthorizationError("没有权限修改此人设卡")

        # 验证输入参数
        if not name or not description:
            raise ValidationError("名称和描述不能为空")

        # 更新人设卡信息
        pc_data = pc.to_dict()
        pc_data.update({
            "name": name,
            "description": description,
            "copyright_owner": copyright_owner,
            "updated_at": datetime.now()
        })
        
        updated_pc = db_manager.save_persona_card(pc_data)
        if not updated_pc:
            raise DatabaseError("更新人设卡失败")

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "update",
            "persona_card",
            record_id=pc_id,
            user_id=user_id,
            success=True
        )

        return PersonaCardResponse(**updated_pc.to_dict())

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


@api_router.post("/persona/{pc_id}/star")
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

        return {"message": message+"成功"}

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
        raise APIError(message+"人设卡失败")


@api_router.delete("/persona/{pc_id}/star")
async def unstar_persona_card(
    pc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """取消Star人设卡"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Unstar persona card: pc_id={pc_id}, user_id={user_id}")

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

        return {"message": "取消Star成功"}

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


@api_router.delete("/persona/{pc_id}")
async def delete_persona_card(
    pc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """删除人设卡"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Delete persona card: pc_id={pc_id}, user_id={user_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise ValidationError("人设卡不存在")

        # 验证权限：只有上传者和管理员可以删除人设卡
        if pc.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get("is_moderator", False):
            raise AuthorizationError("没有权限删除此人设卡")

        # 删除关联的文件
        file_delete_success = db_manager.delete_files_by_persona_card_id(pc_id)
        if not file_delete_success:
            app_logger.warning(f"Failed to delete associated files for persona card: pc_id={pc_id}")

        # 删除人设卡本身
        success = db_manager.delete_persona_card(pc_id)
        if not success:
            raise DatabaseError("删除人设卡失败")

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "delete",
            "persona_card",
            record_id=pc_id,
            user_id=user_id,
            success=True
        )

        return {"message": "人设卡删除成功"}

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


@api_router.post("/persona/{pc_id}/files")
async def add_files_to_persona_card(
    pc_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """向人设卡添加文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Add files to persona card: pc_id={pc_id}, user_id={user_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise ValidationError("人设卡不存在")

        # 验证权限：只有上传者和管理员可以添加文件
        if pc.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get("is_moderator", False):
            raise AuthorizationError("没有权限向此人设卡添加文件")

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

        return {"message": "文件添加成功"}
    except (NotFoundError, AuthorizationError, ValidationError, FileOperationError, DatabaseError, HTTPException):
        raise
    except Exception as e:
        log_exception(app_logger, "Add files to persona card error", exception=e)
        log_file_operation(
            app_logger,
            "add_files",
            f"persona_card/{pc_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("添加文件失败")


@api_router.delete("/persona/{pc_id}/{file_id}")
async def delete_files_from_persona_card(
    pc_id: str,
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """从人设卡删除文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Delete files from persona card: pc_id={pc_id}, user_id={user_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 验证权限：只有上传者和管理员可以删除文件
        if pc.uploader_id != user_id and not current_user.get("is_admin", False) and not current_user.get("is_moderator", False):
            raise AuthorizationError("没有权限从此人设卡删除文件")

        if not file_id:
            return {"message": "文件删除成功"}

        # 删除文件
        success = await file_upload_service.delete_files_from_persona_card(pc_id, file_id, user_id)
        
        if not success:
            raise FileOperationError("删除文件失败")

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

        return {"message": "文件删除成功"}

    except (NotFoundError, AuthorizationError, ValidationError, FileOperationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete files from persona card error", exception=e)
        log_file_operation(
            app_logger,
            "delete_files",
            f"persona_card/{pc_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("删除文件失败")


@api_router.get("/persona/{pc_id}/download")
async def download_persona_card_files(
    pc_id: str,
):
    """下载人设卡的所有文件压缩包"""
    try:
        # 创建ZIP文件
        zip_result = await file_upload_service.create_persona_card_zip(pc_id)
        zip_path = zip_result["zip_path"]
        zip_filename = zip_result["zip_filename"]
        
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载失败: {str(e)}"
        )


@api_router.get("/persona/{pc_id}/file/{file_id}")
async def download_persona_card_file(
    pc_id: str,
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """下载人设卡中的单个文件"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Download persona card file: pc_id={pc_id}, file_id={file_id}, user_id={user_id}")

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
        log_exception(app_logger, "Download persona card file error", exception=e)
        log_file_operation(
            app_logger,
            "download",
            f"persona_card/{pc_id}/file/{file_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("下载文件失败")


# 用户Star记录相关路由
@api_router.get("/user/stars", response_model=List[Dict[str, Any]])
async def get_user_stars(current_user: dict = Depends(get_current_user)):
    """获取用户Star的知识库和人设卡"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Get user stars: user_id={user_id}")

        stars = db_manager.get_stars_by_user(user_id)
        result = []

        for star in stars:
            if star.target_type == "knowledge":
                kb = db_manager.get_knowledge_base_by_id(star.target_id)
                if kb and kb.is_public:
                    result.append({
                        "id": star.id,
                        "type": "knowledge",
                        "target_id": star.target_id,
                        "name": kb.name,
                        "description": kb.description,
                        "star_count": kb.star_count,
                        "created_at": star.created_at.isoformat()
                    })
            elif star.target_type == "persona":
                pc = db_manager.get_persona_card_by_id(star.target_id)
                if pc and pc.is_public:
                    result.append({
                        "id": star.id,
                        "type": "persona",
                        "target_id": star.target_id,
                        "name": pc.name,
                        "description": pc.description,
                        "star_count": pc.star_count,
                        "created_at": star.created_at.isoformat()
                    })

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "read",
            "star",
            user_id=user_id,
            success=True
        )

        return result
    except DatabaseError:
        raise
    except Exception as e:
        log_exception(app_logger, "Get user stars error", exception=e)
        log_database_operation(
            app_logger,
            "read",
            "star",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("获取用户Star记录失败")


# 审核相关路由
@api_router.get("/review/knowledge/pending", response_model=List[KnowledgeBaseResponse])
async def get_pending_knowledge_bases(current_user: dict = Depends(get_current_user)):
    """获取待审核的知识库（需要admin或moderator权限）"""
    # 验证权限
    if current_user.get("role", "user") not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        kbs = db_manager.get_pending_knowledge_bases()
        return [KnowledgeBaseResponse(**kb.to_dict()) for kb in kbs]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取待审核知识库失败: {str(e)}"
        )


@api_router.get("/review/persona/pending", response_model=List[PersonaCardResponse])
async def get_pending_persona_cards(current_user: dict = Depends(get_current_user)):
    """获取待审核的人设卡（需要admin或moderator权限）"""
    # 验证权限
    if current_user.get("role", "user") not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        pcs = db_manager.get_pending_persona_cards()
        return [PersonaCardResponse(**pc.to_dict()) for pc in pcs]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取待审核人设卡失败: {str(e)}"
        )


@api_router.post("/review/knowledge/{kb_id}/approve")
async def approve_knowledge_base(
    kb_id: str,
    current_user: dict = Depends(get_current_user)
):
    """审核通过知识库（需要admin或moderator权限）"""
    # 验证权限
    if current_user.get("role", "user") not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识库不存在"
            )

        # 更新状态
        kb.is_public = True
        kb.is_pending = False
        kb.rejection_reason = None

        updated_kb = db_manager.save_knowledge_base(kb)
        if not updated_kb:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新知识库状态失败"
            )

        return {"message": "审核通过"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审核知识库失败: {str(e)}"
        )


@api_router.post("/review/knowledge/{kb_id}/reject")
async def reject_knowledge_base(
    kb_id: str,
    reason: str,
    current_user: dict = Depends(get_current_user)
):
    """审核拒绝知识库（需要admin或moderator权限）"""
    # 验证权限
    if current_user.get("role", "user") not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="知识库不存在"
            )

        # 更新状态
        kb.is_public = False
        kb.is_pending = False
        kb.rejection_reason = reason

        updated_kb = db_manager.save_knowledge_base(kb)
        if not updated_kb:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新知识库状态失败"
            )

        # 发送拒绝通知
        message = Message(
            recipient_id=kb.uploader_id,
            sender_id=current_user.get("id", ""),
            title="知识库审核未通过",
            content=f"您上传的知识库《{kb.name}》未通过审核。\n\n拒绝原因：{reason}"
        )

        db_manager.save_message(message)

        return {"message": "审核拒绝，已发送通知"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审核知识库失败: {str(e)}"
        )


@api_router.post("/review/persona/{pc_id}/approve")
async def approve_persona_card(
    pc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """审核通过人设卡（需要admin或moderator权限）"""
    # 验证权限
    if current_user.get("role", "user") not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="人设卡不存在"
            )

        # 更新状态
        pc.is_public = True
        pc.is_pending = False
        pc.rejection_reason = None

        updated_pc = db_manager.save_persona_card(pc)
        if not updated_pc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新人设卡状态失败"
            )

        return {"message": "审核通过"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审核人设卡失败: {str(e)}"
        )


@api_router.post("/review/persona/{pc_id}/reject")
async def reject_persona_card(
    pc_id: str,
    reason: str,
    current_user: dict = Depends(get_current_user)
):
    """审核拒绝人设卡（需要admin或moderator权限）"""
    # 验证权限
    if current_user.get("role", "user") not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="人设卡不存在"
            )

        # 更新状态
        pc.is_public = False
        pc.is_pending = False
        pc.rejection_reason = reason

        updated_pc = db_manager.save_persona_card(pc)
        if not updated_pc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新人设卡状态失败"
            )

        # 发送拒绝通知
        message = Message(
            recipient_id=pc.uploader_id,
            sender_id=current_user.get("id", ""),
            title="人设卡审核未通过",
            content=f"您上传的人设卡《{pc.name}》未通过审核。\n\n拒绝原因：{reason}"
        )

        db_manager.save_message(message)

        return {"message": "审核拒绝，已发送通知"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"审核人设卡失败: {str(e)}"
        )


# 消息相关路由
@api_router.post("/messages/send", response_model=dict)
async def send_message(
    message: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """发送消息"""
    sender_id = current_user.get("id", "")
    try:
        app_logger.info(f"Send message: sender={sender_id}, recipient={message.recipient_id}")

        # 验证输入参数
        if not message.content or not message.content.strip():
            raise ValidationError("消息内容不能为空")

        if not message.recipient_id:
            raise ValidationError("接收者ID不能为空")

        # 检查接收者是否存在
        recipient = db_manager.get_user_by_id(message.recipient_id)
        if not recipient:
            raise NotFoundError("接收者不存在")

        # 创建消息
        msg = db_manager.create_message(
            sender_id=sender_id,
            recipient_id=message.recipient_id,
            content=message.content,
            message_type=message.message_type
        )

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "create",
            "message",
            record_id=msg.id,
            user_id=sender_id,
            success=True
        )

        return {"message_id": msg.id, "status": "sent"}

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


@api_router.get("/messages", response_model=List[MessageResponse])
async def get_messages(
    current_user: dict = Depends(get_current_user),
    other_user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """获取消息列表"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Get messages: user_id={user_id}, other_user_id={other_user_id}, limit={limit}, offset={offset}")

        # 验证参数
        if limit <= 0 or limit > 100:
            raise ValidationError("limit必须在1-100之间")

        if offset < 0:
            raise ValidationError("offset不能为负数")

        # 获取消息列表
        if other_user_id:
            # 获取与特定用户的对话
            messages = db_manager.get_conversation_messages(
                user_id=user_id,
                other_user_id=other_user_id,
                limit=limit,
                offset=offset
            )
        else:
            # 获取所有消息
            messages = db_manager.get_user_messages(
                user_id=user_id,
                limit=limit,
                offset=offset
            )

        return [MessageResponse(**msg.to_dict()) for msg in messages]

    except (ValidationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get messages error", exception=e)
        raise APIError("获取消息列表失败")


@api_router.post("/messages/{message_id}/read", response_model=dict)
async def mark_message_read(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """标记消息为已读"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Mark message as read: message_id={message_id}, user_id={user_id}")

        # 检查消息是否存在
        message = db_manager.get_message_by_id(message_id)
        if not message:
            raise NotFoundError("消息不存在")

        # 验证权限：只有接收者可以标记消息为已读
        if message.recipient_id != user_id:
            app_logger.warning(f"Unauthorized mark read attempt: user={user_id} trying to mark message={message_id} sent to {message.recipient_id}")
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

        return {"status": "success", "message": "消息已标记为已读"}

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


# 导出路由器
router = api_router