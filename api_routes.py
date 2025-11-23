"""
API路由实现
包含知识库、人设卡、用户管理、审核等功能路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request, Body, Query
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import os
import hashlib
from datetime import datetime

from models import (
    KnowledgeBase, PersonaCard, Message, MessageCreate, MessageUpdate, StarRecord,
    KnowledgeBaseUpdate, MessageResponse, KnowledgeBaseResponse, PersonaCardResponse,
    StarResponse, KnowledgeBasePaginatedResponse, PersonaCardPaginatedResponse
)
from database_models import sqlite_db_manager, KnowledgeBase, PersonaCard, UploadRecord
from file_upload import file_upload_service
from user_management import get_current_user, get_current_user_optional, pwd_context, create_user, get_user_by_username

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

# 注意：速率限制通过main.py中的中间件实现

# OAuth2 认证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 认证相关路由
@api_router.post("/token")
async def login(request: Request):
    """用户登录获取访问令牌，支持JSON和表单数据格式（带速率限制和账户锁定）"""
    # 速率限制：每分钟最多5次登录尝试（通过装饰器实现）
    try:
        # 获取Content-Type
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            # 处理JSON格式
            try:
                data = await request.json()
                username = data.get("username", "").strip()
                password = data.get("password", "")
            except Exception:
                raise ValidationError("无效的JSON格式")
        elif "application/x-www-form-urlencoded" in content_type:
            # 处理表单格式
            form_data = await request.form()
            username = form_data.get("username", "").strip()
            password = form_data.get("password", "")
        else:
            raise ValidationError("不支持的Content-Type")

        # 验证必填字段
        if not username or not password:
            raise ValidationError("请提供用户名和密码")

        # 用户名哈希用于日志（不记录真实用户名，保护隐私）
        username_hash = hashlib.sha256(username.encode()).hexdigest()[:8]
        app_logger.info(f"Login attempt: username_hash={username_hash}")

        # 导入用户管理模块的验证函数（带账户锁定检查）
        from user_management import get_user_by_credentials_with_lock_check
        # 导入JWT工具
        from jwt_utils import create_user_token, create_refresh_token

        # 验证用户凭据（带账户锁定检查）
        user = get_user_by_credentials_with_lock_check(username, password)

        if user:
            app_logger.info(f"Login successful: user_id={user.userID}, role={user.role}")

            # 获取密码版本号
            password_version = 0
            if user._db_user:
                password_version = user._db_user.password_version or 0

            # 创建JWT访问令牌和刷新令牌
            access_token = create_user_token(user.userID, user.username, user.role, password_version)
            refresh_token = create_refresh_token(user.userID)

            # 返回token和用户信息
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 900,  # 15分钟
                "user": {
                    "id": user.userID,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role
                }
            }

        # 登录失败（统一错误消息，防止用户枚举）
        app_logger.warning(f"Login failed: username_hash={username_hash}")
        raise AuthenticationError("用户名或密码错误")

    except AuthenticationError:
        raise
    except Exception as e:
        log_exception(app_logger, "Login error", exception=e)
        raise APIError("登录过程中发生错误")


@api_router.post("/refresh")
async def refresh_token(request: Request):
    """刷新访问令牌"""
    try:
        # 获取Content-Type
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            data = await request.json()
            refresh_token = data.get("refresh_token")
        elif "application/x-www-form-urlencoded" in content_type:
            form_data = await request.form()
            refresh_token = form_data.get("refresh_token")
        else:
            raise ValidationError("不支持的Content-Type")
        
        if not refresh_token:
            raise ValidationError("请提供刷新令牌")
        
        # 验证刷新令牌
        from jwt_utils import verify_token, create_user_token
        payload = verify_token(refresh_token)
        
        if not payload:
            raise AuthenticationError("无效的刷新令牌")
        
        # 检查令牌类型
        if payload.get("type") != "refresh":
            raise AuthenticationError("无效的令牌类型")
        
        # 获取用户ID
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("无效的令牌")
        
        # 获取用户信息
        from user_management import get_user_by_id
        user = get_user_by_id(user_id)
        
        if not user:
            raise AuthenticationError("用户不存在")
        
        # 获取密码版本号
        password_version = 0
        if user._db_user:
            password_version = user._db_user.password_version or 0
        
        # 创建新的访问令牌
        access_token = create_user_token(user.userID, user.username, user.role, password_version)
        
        app_logger.info(f"Token refreshed: user_id={user.userID}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 900  # 15分钟
        }
        
    except (AuthenticationError, ValidationError):
        raise
    except Exception as e:
        log_exception(app_logger, "Refresh token error", exception=e)
        raise APIError("刷新令牌过程中发生错误")


@api_router.post("/send_verification_code")
async def send_verification_code(
        email: str = Form(...),
):
    try:
        # 统一转换为小写
        email = email.lower()
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
        error_msg = str(e)
        # 提取更详细的错误信息
        if "Connection unexpectedly closed" in error_msg:
            raise APIError("邮件发送失败: SMTP连接被意外关闭，请检查邮件服务器配置和网络连接")
        elif "authentication failed" in error_msg.lower() or "login" in error_msg.lower():
            raise APIError("邮件发送失败: 邮箱认证失败，请检查邮箱账号和授权码")
        elif "timeout" in error_msg.lower():
            raise APIError("邮件发送失败: 连接超时，请检查网络连接和邮件服务器地址")
        else:
            raise APIError(f"发送验证码失败: {error_msg}")

@api_router.post("/send_reset_password_code")
async def send_reset_password_code(
        email: str = Form(...),
):
    """发送重置密码验证码"""
    try:
        # 统一转换为小写
        email = email.lower()
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
        error_msg = str(e)
        # 提取更详细的错误信息
        if "Connection unexpectedly closed" in error_msg:
            raise APIError("邮件发送失败: SMTP连接被意外关闭，请检查邮件服务器配置和网络连接")
        elif "authentication failed" in error_msg.lower() or "login" in error_msg.lower():
            raise APIError("邮件发送失败: 邮箱认证失败，请检查邮箱账号和授权码")
        elif "timeout" in error_msg.lower():
            raise APIError("邮件发送失败: 连接超时，请检查网络连接和邮件服务器地址")
        else:
            raise APIError(f"发送重置密码验证码失败: {error_msg}")

@api_router.post("/reset_password")
async def reset_password(
        email: str = Form(...),
        verification_code: str = Form(...),
        new_password: str = Form(...)
):
    """通过邮箱验证码重置密码"""
    try:
        # 统一转换为小写
        email = email.lower()
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

        # 统一转换为小写
        email = email.lower()
        
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

        # 从数据库获取用户信息（包含头像信息）
        user = db_manager.get_user_by_id(user_id)
        avatar_url = None
        avatar_updated_at = None
        
        if user:
            if user.avatar_path:
                avatar_url = f"/{user.avatar_path}"
            if user.avatar_updated_at:
                avatar_updated_at = user.avatar_updated_at.isoformat()

        return {
            "id": user_id,
            "username": current_user.get("username", ""),
            "email": current_user.get("email", ""),
            "role": current_user.get("role", "user"),
            "avatar_url": avatar_url,
            "avatar_updated_at": avatar_updated_at
        }
    except Exception as e:
        log_exception(app_logger, "Get user info error", exception=e)
        raise APIError("获取用户信息失败")


@api_router.put("/users/me/password", response_model=dict)
async def change_password(
    password_data: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    request: Request = None
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
        
        # 获取用户
        user = db_manager.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")
        
        # 验证当前密码
        if not user.verify_password(current_password):
            app_logger.warning(f"Password change failed: wrong current password, user_id={user_id}")
            raise AuthenticationError("当前密码错误")
        
        # 检查新密码是否与当前密码相同
        if user.verify_password(new_password):
            raise ValidationError("新密码不能与当前密码相同")
        
        # 更新密码（会自动增加password_version）
        user.update_password(new_password)
        
        # 保存到数据库
        user_data = user.to_dict()
        if not db_manager.save_user(user_data):
            raise DatabaseError("保存密码失败")
        
        log_database_operation(
            app_logger,
            "update",
            "user_password",
            success=True,
            user_id=user_id
        )
        
        app_logger.info(f"Password changed successfully: user_id={user_id}")
        
        return {
            "success": True,
            "message": "密码修改成功，请重新登录"
        }
        
    except (ValidationError, AuthenticationError, NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Change password error", exception=e)
        raise APIError("修改密码失败")


@api_router.post("/users/me/avatar", response_model=dict)
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """上传/更新头像"""
    try:
        from avatar_utils import (
            validate_image_file, process_avatar_image, save_avatar_file,
            delete_avatar_file, ensure_avatar_dir
        )
        
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
        if file_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            file_ext = '.jpg'  # 默认使用jpg
        
        # 获取用户
        user = db_manager.get_user_by_id(user_id)
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
        user_data = user.to_dict()
        if not db_manager.save_user(user_data):
            # 如果保存失败，删除已上传的文件
            delete_avatar_file(file_path)
            raise DatabaseError("保存头像信息失败")
        
        log_file_operation(
            app_logger,
            "upload",
            "avatar",
            success=True,
            user_id=user_id,
            file_path=file_path
        )
        
        app_logger.info(f"Avatar uploaded successfully: user_id={user_id}, path={file_path}")
        
        return {
            "success": True,
            "message": "头像上传成功",
            "avatar_url": f"/{file_path}",
            "avatar_updated_at": user.avatar_updated_at.isoformat()
        }
        
    except (ValidationError, NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Upload avatar error", exception=e)
        raise APIError("上传头像失败")


@api_router.delete("/users/me/avatar", response_model=dict)
async def delete_avatar(current_user: dict = Depends(get_current_user)):
    """删除头像（恢复为默认头像）"""
    try:
        from avatar_utils import delete_avatar_file
        
        user_id = current_user.get("id", "")
        app_logger.info(f"Delete avatar request: user_id={user_id}")
        
        # 获取用户
        user = db_manager.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")
        
        # 如果存在头像文件，删除它
        if user.avatar_path:
            delete_avatar_file(user.avatar_path)
        
        # 更新数据库
        user.avatar_path = None
        user.avatar_updated_at = datetime.now()
        user_data = user.to_dict()
        if not db_manager.save_user(user_data):
            raise DatabaseError("保存头像信息失败")
        
        log_file_operation(
            app_logger,
            "delete",
            "avatar",
            success=True,
            user_id=user_id
        )
        
        app_logger.info(f"Avatar deleted successfully: user_id={user_id}")
        
        return {
            "success": True,
            "message": "头像已删除，已恢复为默认头像"
        }
        
    except (NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete avatar error", exception=e)
        raise APIError("删除头像失败")


@api_router.get("/users/{user_id}/avatar")
async def get_user_avatar(user_id: str, size: int = 200):
    """获取用户头像（如果不存在则生成首字母头像）"""
    try:
        from fastapi.responses import Response
        from avatar_utils import generate_initial_avatar
        import os
        
        # 获取用户信息
        user = db_manager.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")
        
        # 如果用户有上传的头像，返回头像URL
        if user.avatar_path and os.path.exists(user.avatar_path):
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=f"/{user.avatar_path}")
        
        # 否则生成首字母头像
        username = user.username or "?"
        avatar_bytes = generate_initial_avatar(username, size)
        
        return Response(
            content=avatar_bytes,
            media_type="image/png"
        )
        
    except NotFoundError:
        raise
    except Exception as e:
        log_exception(app_logger, "Get user avatar error", exception=e)
        raise APIError("获取用户头像失败")


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

        # 创建上传记录
        try:
            db_manager.create_upload_record(
                uploader_id=user_id,
                target_id=kb.id,
                target_type="knowledge",
                name=name,
                description=description,
                status="pending"
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


@api_router.get("/knowledge/public", response_model=KnowledgeBasePaginatedResponse)
async def get_public_knowledge_bases(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    name: str = Query(None, description="按名称搜索"),
    uploader_id: str = Query(None, description="按上传者ID筛选"),
    sort_by: str = Query("created_at", description="排序字段(created_at, updated_at, star_count)"),
    sort_order: str = Query("desc", description="排序顺序(asc, desc)")
):
    """获取所有公开的知识库，支持分页、搜索、按上传者筛选和排序"""
    try:
        app_logger.info("Get public knowledge bases")

        kbs, total = db_manager.get_public_knowledge_bases(
            page=page,
            page_size=page_size,
            name=name,
            uploader_id=uploader_id,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return KnowledgeBasePaginatedResponse(
            items=[KnowledgeBaseResponse(**kb.to_dict()) for kb in kbs],
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        log_exception(app_logger, "Get public knowledge bases error", exception=e)
        raise APIError("获取公开知识库失败")


@api_router.get("/knowledge/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(kb_id: str):
    """获取知识库基本信息"""
    try:
        app_logger.info(f"Get knowledge base: kb_id={kb_id}")

        # 检查知识库是否存在
        kb = db_manager.get_knowledge_base_by_id(kb_id)
        if not kb:
            raise NotFoundError("知识库不存在")

        # 返回完整的知识库信息（包含文件和metadata）
        kb_dict = kb.to_dict(include_files=True, include_metadata=True)
        return KnowledgeBaseResponse(**kb_dict)

    except NotFoundError:
        raise
    except Exception as e:
        log_exception(app_logger, "Get knowledge base error", exception=e)
        raise APIError("获取知识库失败")


@api_router.get("/knowledge/{kb_id}/starred", response_model=Dict[str, bool])
async def check_knowledge_starred(
    kb_id: str,
    current_user: dict = Depends(get_current_user)
):
    """检查知识库是否已被当前用户Star"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Check knowledge starred: kb_id={kb_id}, user_id={user_id}")
        starred = db_manager.is_starred(user_id, kb_id, "knowledge")
        return {"starred": starred}
    except Exception as e:
        log_exception(app_logger, "Check knowledge starred error", exception=e)
        raise APIError("检查Star状态失败")


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

        # 创建上传记录
        try:
            db_manager.create_upload_record(
                uploader_id=user_id,
                target_id=pc.id,
                target_type="persona",
                name=name,
                description=description,
                status="pending"
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


@api_router.get("/persona/public", response_model=PersonaCardPaginatedResponse)
async def get_public_persona_cards(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    name: str = Query(None, description="按名称搜索"),
    uploader_id: str = Query(None, description="按上传者ID筛选"),
    sort_by: str = Query("created_at", description="排序字段(created_at, updated_at, star_count)"),
    sort_order: str = Query("desc", description="排序顺序(asc, desc)")
):
    """获取所有公开的人设卡，支持分页、搜索、按上传者筛选和排序"""
    try:
        app_logger.info("Get public persona cards")

        pcs, total = db_manager.get_public_persona_cards(
            page=page,
            page_size=page_size,
            name=name,
            uploader_id=uploader_id,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return PersonaCardPaginatedResponse(
            items=[PersonaCardResponse(**pc.to_dict()) for pc in pcs],
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        log_exception(app_logger, "Get public persona cards error", exception=e)
        raise APIError("获取公开人设卡失败")


@api_router.get("/persona/{pc_id}", response_model=PersonaCardResponse)
async def get_persona_card(pc_id: str):
    """获取人设卡详情"""
    try:
        app_logger.info(f"Get persona card detail: pc_id={pc_id}")

        # 检查人设卡是否存在
        pc = db_manager.get_persona_card_by_id(pc_id)
        if not pc:
            raise NotFoundError("人设卡不存在")

        # 返回完整的人设卡信息（包含文件和metadata）
        pc_dict = pc.to_dict(include_files=True, include_metadata=True)
        return PersonaCardResponse(**pc_dict)

    except NotFoundError:
        raise
    except Exception as e:
        log_exception(app_logger, "Get persona card detail error", exception=e)
        raise APIError("获取人设卡详情失败")


@api_router.get("/persona/{pc_id}/starred", response_model=Dict[str, bool])
async def check_persona_starred(
    pc_id: str,
    current_user: dict = Depends(get_current_user)
):
    """检查人设卡是否已被当前用户Star"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Check persona starred: pc_id={pc_id}, user_id={user_id}")
        starred = db_manager.is_starred(user_id, pc_id, "persona")
        return {"starred": starred}
    except Exception as e:
        log_exception(app_logger, "Check persona starred error", exception=e)
        raise APIError("检查Star状态失败")


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
async def get_user_stars(
    current_user: dict = Depends(get_current_user),
    include_details: bool = False
):
    """获取用户Star的知识库和人设卡"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Get user stars: user_id={user_id}, include_details={include_details}")

        stars = db_manager.get_stars_by_user(user_id)
        result = []

        for star in stars:
            if star.target_type == "knowledge":
                kb = db_manager.get_knowledge_base_by_id(star.target_id)
                if kb and kb.is_public:
                    item = {
                        "id": star.id,
                        "type": "knowledge",
                        "target_id": star.target_id,
                        "name": kb.name,
                        "description": kb.description,
                        "star_count": kb.star_count,
                        "created_at": star.created_at.isoformat()
                    }
                    # 如果需要完整详情，调用to_dict
                    if include_details:
                        kb_dict = kb.to_dict(include_files=True, include_metadata=True)
                        item.update(kb_dict)
                    result.append(item)
            elif star.target_type == "persona":
                pc = db_manager.get_persona_card_by_id(star.target_id)
                if pc and pc.is_public:
                    item = {
                        "id": star.id,
                        "type": "persona",
                        "target_id": star.target_id,
                        "name": pc.name,
                        "description": pc.description,
                        "star_count": pc.star_count,
                        "created_at": star.created_at.isoformat()
                    }
                    # 如果需要完整详情，调用to_dict
                    if include_details:
                        pc_dict = pc.to_dict(include_files=True, include_metadata=True)
                        item.update(pc_dict)
                    result.append(item)

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
@api_router.get("/review/knowledge/pending", response_model=KnowledgeBasePaginatedResponse)
async def get_pending_knowledge_bases(
    page: int = Query(1, ge=1, description="页码，默认为1"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，默认为10，最大100"),
    name: Optional[str] = Query(None, description="按名称搜索"),
    uploader_id: Optional[str] = Query(None, description="按上传者ID筛选"),
    sort_by: str = Query("created_at", description="排序字段，可选：created_at, updated_at, star_count"),
    sort_order: str = Query("desc", description="排序方式，可选：asc, desc"),
    current_user: dict = Depends(get_current_user)
):
    """获取待审核的知识库（需要admin或moderator权限），支持分页、搜索、按上传者筛选和排序"""
    # 验证权限
    if current_user.get("role", "user") not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        kbs, total = db_manager.get_pending_knowledge_bases(
            page=page,
            page_size=page_size,
            name=name,
            uploader_id=uploader_id,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return KnowledgeBasePaginatedResponse(
            items=[KnowledgeBaseResponse(**kb.to_dict()) for kb in kbs],
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取待审核知识库失败: {str(e)}"
        )


@api_router.get("/review/persona/pending", response_model=PersonaCardPaginatedResponse)
async def get_pending_persona_cards(
    page: int = Query(1, ge=1, description="页码，默认为1"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，默认为10，最大100"),
    name: Optional[str] = Query(None, description="按名称搜索"),
    uploader_id: Optional[str] = Query(None, description="按上传者ID筛选"),
    sort_by: str = Query("created_at", description="排序字段，可选：created_at, updated_at, star_count"),
    sort_order: str = Query("desc", description="排序方式，可选：asc, desc"),
    current_user: dict = Depends(get_current_user)
):
    """获取待审核的人设卡（需要admin或moderator权限），支持分页、搜索、按上传者筛选和排序"""
    # 验证权限
    if current_user.get("role", "user") not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有审核权限"
        )

    try:
        pcs, total = db_manager.get_pending_persona_cards(
            page=page,
            page_size=page_size,
            name=name,
            uploader_id=uploader_id,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return PersonaCardPaginatedResponse(
            items=[PersonaCardResponse(**pc.to_dict()) for pc in pcs],
            total=total,
            page=page,
            page_size=page_size
        )
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

        updated_kb = db_manager.save_knowledge_base(kb.to_dict())
        if not updated_kb:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新知识库状态失败"
            )

        # 更新上传记录状态
        try:
            db_manager.update_upload_record_status(kb_id, "approved")
        except Exception as e:
            app_logger.warning(f"Failed to update upload record status: {str(e)}")

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
    reason: str = Body(..., embed=True),
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

        updated_kb = db_manager.save_knowledge_base(kb.to_dict())
        if not updated_kb:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新知识库状态失败"
            )

        # 更新上传记录状态
        try:
            db_manager.update_upload_record_status(kb_id, "rejected")
        except Exception as e:
            app_logger.warning(f"Failed to update upload record status: {str(e)}")

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

        updated_pc = db_manager.save_persona_card(pc.to_dict())
        if not updated_pc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新人设卡状态失败"
            )

        # 更新上传记录状态
        try:
            db_manager.update_upload_record_status(pc_id, "approved")
        except Exception as e:
            app_logger.warning(f"Failed to update upload record status: {str(e)}")

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
    reason: str = Body(..., embed=True),
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

        updated_pc = db_manager.save_persona_card(pc.to_dict())
        if not updated_pc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新人设卡状态失败"
            )

        # 更新上传记录状态
        try:
            db_manager.update_upload_record_status(pc_id, "rejected")
        except Exception as e:
            app_logger.warning(f"Failed to update upload record status: {str(e)}")

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
            created_messages = db_manager.bulk_create_messages(message_payloads)
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

        return {
            "message_ids": [msg.id for msg in created_messages],
            "status": "sent",
            "count": len(created_messages)
        }

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


@api_router.get("/messages/{message_id}", response_model=MessageResponse)
async def get_message_detail(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取消息详情"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Get message detail: message_id={message_id}, user_id={user_id}")

        # 检查消息是否存在
        message = db_manager.get_message_by_id(message_id)
        if not message:
            raise NotFoundError("消息不存在")

        # 验证权限：只有接收者可以查看消息详情
        recipient_id = str(message.recipient_id) if message.recipient_id else ""
        user_id_str = str(user_id) if user_id else ""
        
        if recipient_id != user_id_str:
            raise AuthorizationError("没有权限查看此消息")

        return MessageResponse(
            id=message.id,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id,
            title=message.title,
            content=message.content,
            summary=message.summary,
            message_type=message.message_type or "direct",
            broadcast_scope=message.broadcast_scope,
            is_read=message.is_read or False,
            created_at=message.created_at if message.created_at else datetime.now()
        )

    except (NotFoundError, AuthorizationError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get message detail error", exception=e)
        raise APIError("获取消息详情失败")


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

        # 验证用户ID
        if not user_id:
            raise AuthorizationError("用户ID无效")

        # 检查消息是否存在
        message = db_manager.get_message_by_id(message_id)
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


@api_router.delete("/messages/{message_id}", response_model=dict)
async def delete_message(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """删除消息（接收者可以删除，管理员可以删除公告）"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Delete message: message_id={message_id}, user_id={user_id}")

        # 验证用户ID
        if not user_id:
            raise AuthorizationError("用户ID无效")

        # 检查消息是否存在
        message = db_manager.get_message_by_id(message_id)
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
            deleted_count = db_manager.delete_broadcast_messages(message_id, user_id)
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

        return {
            "status": "success", 
            "message": "消息已删除",
            "deleted_count": deleted_count
        }

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


@api_router.put("/messages/{message_id}", response_model=dict)
async def update_message(
    message_id: str,
    update_data: MessageUpdate,
    current_user: dict = Depends(get_current_user)
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

        # 检查消息是否存在
        message = db_manager.get_message_by_id(message_id)
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

        return {
            "status": "success", 
            "message": "消息已更新",
            "updated_count": updated_count
        }

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


@api_router.get("/admin/broadcast-messages", response_model=Dict[str, Any])
async def get_broadcast_messages(
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """获取广播消息历史（仅限admin和moderator）"""
    # 验证权限：admin或moderator
    user_role = current_user.get("role", "user")
    is_admin_or_moderator = user_role in ["admin", "moderator"]
    if not is_admin_or_moderator:
        raise AuthorizationError("需要管理员或审核员权限")
    
    try:
        app_logger.info(f"Get broadcast messages: user_id={current_user.get('id')}, limit={limit}, offset={offset}")
        
        # 验证参数
        if limit <= 0 or limit > 100:
            raise ValidationError("limit必须在1-100之间")
        
        if offset < 0:
            raise ValidationError("offset不能为负数")
        
        # 获取广播消息
        messages = db_manager.get_broadcast_messages(limit=limit, offset=offset)
        
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
        
        return {
            "success": True,
            "data": result,
            "total": len(result),
            "limit": limit,
            "offset": offset
        }
        
    except (ValidationError, AuthorizationError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Get broadcast messages error", exception=e)
        raise APIError("获取广播消息历史失败")


# 管理员相关路由
@api_router.get("/admin/stats", response_model=Dict[str, Any])
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
            total_users = session.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
            
            # 知识库数量（包括待审核）
            total_knowledge = session.query(func.count(KnowledgeBase.id)).scalar() or 0
            
            # 人格数量（包括待审核）
            total_personas = session.query(func.count(PersonaCard.id)).scalar() or 0
            
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
        
        log_api_request(app_logger, "GET", "/admin/stats", current_user.get("id"), status_code=200)
        return {"success": True, "data": stats}
        
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get admin stats error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计数据失败: {str(e)}"
        )


@api_router.get("/admin/recent-users", response_model=Dict[str, Any])
async def get_recent_users(
    limit: int = 10,
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
        app_logger.info(f"Get recent users: user_id={current_user.get('id')}, limit={limit}, page={page}")
        
        # 限制limit范围
        if limit < 1 or limit > 100:
            limit = 10
        if page < 1:
            page = 1
        
        with db_manager.get_session() as session:
            from database_models import User
            from sqlalchemy import desc
            
            offset = (page - 1) * limit
            users = session.query(User).filter(
                User.is_active == True
            ).order_by(
                desc(User.created_at)
            ).offset(offset).limit(limit).all()
            
            user_list = []
            for user in users:
                role = "admin" if user.is_admin else ("moderator" if user.is_moderator else "user")
                user_list.append({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": role,
                    "createdAt": user.created_at.isoformat() if user.created_at else None
                })
        
        log_api_request(app_logger, "GET", "/admin/recent-users", current_user.get("id"), status_code=200)
        return {"success": True, "data": user_list}
        
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get recent users error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取最近用户失败: {str(e)}"
        )


# 用户管理API
@api_router.get("/admin/users", response_model=Dict[str, Any])
async def get_all_users(
    page: int = 1,
    limit: int = 20,
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
        app_logger.info(f"Get all users: user_id={current_user.get('id')}, page={page}, limit={limit}, search={search}, role={role}")
        
        # 限制参数范围
        if limit < 1 or limit > 100:
            limit = 20
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
                query = query.filter(User.is_moderator == True, User.is_admin == False)
            elif role == "user":
                query = query.filter(User.is_moderator == False, User.is_admin == False)
            
            # 获取总数
            total = query.count()
            
            # 分页
            offset = (page - 1) * limit
            users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
            
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
                
                role_str = "admin" if user.is_admin else ("moderator" if user.is_moderator else "user")
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
            
            total_pages = (total + limit - 1) // limit if total > 0 else 0
        
        log_api_request(app_logger, "GET", "/admin/users", current_user.get("id"), status_code=200)
        return {
            "success": True,
            "data": {
                "users": user_list,
                "total": total,
                "page": page,
                "limit": limit,
                "totalPages": total_pages
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get all users error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户列表失败: {str(e)}"
        )


@api_router.put("/admin/users/{user_id}/role", response_model=Dict[str, Any])
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
        app_logger.info(f"Update user role: user_id={user_id}, new_role={role_data.get('role')}, operator={current_user.get('id')}")
        
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
        
        log_api_request(app_logger, "PUT", f"/admin/users/{user_id}/role", current_user.get("id"), status_code=200)
        return {
            "success": True,
            "message": "用户角色更新成功",
            "data": {
                "id": user_id,
                "username": user.username,
                "role": new_role
            }
        }
        
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


@api_router.delete("/admin/users/{user_id}", response_model=Dict[str, Any])
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
        app_logger.info(f"Delete user: user_id={user_id}, operator={current_user.get('id')}")
        
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
        
        log_api_request(app_logger, "DELETE", f"/admin/users/{user_id}", current_user.get("id"), status_code=200)
        return {
            "success": True,
            "message": "用户删除成功"
        }
        
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


@api_router.post("/admin/users", response_model=Dict[str, Any])
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
        app_logger.info(f"Create user by admin: operator={current_user.get('id')}, username={user_data.get('username')}")
        
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
            user = session.query(User).filter(User.id == new_user.userID).first()
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
        
        log_api_request(app_logger, "POST", "/admin/users", current_user.get("id"), status_code=200)
        return {
            "success": True,
            "message": "用户创建成功",
            "data": {
                "id": new_user.userID,
                "username": new_user.username,
                "email": new_user.email,
                "role": role
            }
        }
        
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
@api_router.get("/admin/knowledge/all", response_model=Dict[str, Any])
async def get_all_knowledge_bases_admin(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
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
        app_logger.info(f"Get all knowledge bases (admin): user_id={current_user.get('id')}, page={page}, limit={limit}, status={status}, search={search}")
        
        # 限制参数范围
        if limit < 1 or limit > 100:
            limit = 20
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
                query = query.filter(KnowledgeBase.is_pending == False, KnowledgeBase.rejection_reason == None)
            elif status == "rejected":
                query = query.filter(KnowledgeBase.is_pending == False, KnowledgeBase.rejection_reason != None)
            
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
            offset = (page - 1) * limit
            knowledge_bases = query.order_by(KnowledgeBase.created_at.desc()).offset(offset).limit(limit).all()
            
            # 获取上传者信息
            uploader_ids = list(set([kb.uploader_id for kb in knowledge_bases]))
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
        
        log_api_request(app_logger, "GET", "/admin/knowledge/all", current_user.get("id"), status_code=200)
        return {
            "success": True,
            "data": {
                "knowledgeBases": kb_list,
                "total": total,
                "page": page,
                "limit": limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get all knowledge bases (admin) error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库列表失败: {str(e)}"
        )


@api_router.get("/admin/persona/all", response_model=Dict[str, Any])
async def get_all_personas_admin(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
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
        app_logger.info(f"Get all personas (admin): user_id={current_user.get('id')}, page={page}, limit={limit}, status={status}, search={search}")
        
        # 限制参数范围
        if limit < 1 or limit > 100:
            limit = 20
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
                query = query.filter(PersonaCard.is_pending == False, PersonaCard.rejection_reason == None)
            elif status == "rejected":
                query = query.filter(PersonaCard.is_pending == False, PersonaCard.rejection_reason != None)
            
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
            offset = (page - 1) * limit
            persona_cards = query.order_by(PersonaCard.created_at.desc()).offset(offset).limit(limit).all()
            
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
        
        log_api_request(app_logger, "GET", "/admin/persona/all", current_user.get("id"), status_code=200)
        return {
            "success": True,
            "data": {
                "personas": pc_list,
                "total": total,
                "page": page,
                "limit": limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get all personas (admin) error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取人设卡列表失败: {str(e)}"
        )


@api_router.post("/admin/knowledge/{kb_id}/revert", response_model=Dict[str, Any])
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
        app_logger.info(f"Revert knowledge base: kb_id={kb_id}, operator={current_user.get('id')}")
        
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
            app_logger.warning(f"Failed to update upload record status: {str(e)}")
        
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
        
        log_api_request(app_logger, "POST", f"/admin/knowledge/{kb_id}/revert", current_user.get("id"), status_code=200)
        return {
            "success": True,
            "message": "知识库已退回待审核"
        }
        
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


@api_router.post("/admin/persona/{pc_id}/revert", response_model=Dict[str, Any])
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
        app_logger.info(f"Revert persona card: pc_id={pc_id}, operator={current_user.get('id')}")
        
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
            app_logger.warning(f"Failed to update upload record status: {str(e)}")
        
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
        
        log_api_request(app_logger, "POST", f"/admin/persona/{pc_id}/revert", current_user.get("id"), status_code=200)
        return {
            "success": True,
            "message": "人设卡已退回待审核"
        }
        
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


@api_router.get("/admin/upload-history", response_model=Dict[str, Any])
async def get_upload_history(
    page: int = 1,
    limit: int = 20,
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
        app_logger.info(f"Get upload history: user_id={current_user.get('id')}, page={page}, limit={limit}")
        
        # 限制参数范围
        if limit < 1 or limit > 100:
            limit = 20
        if page < 1:
            page = 1
        
        # 获取上传记录
        upload_records = db_manager.get_all_upload_records(page=page, limit=limit)
        
        # 获取上传者信息
        uploader_ids = list(set([record.uploader_id for record in upload_records]))
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
        
        log_api_request(app_logger, "GET", "/admin/upload-history", current_user.get("id"), status_code=200)
        return {"success": True, "data": history_list}
        
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get upload history error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取上传历史失败: {str(e)}"
        )


@api_router.get("/admin/upload-stats", response_model=Dict[str, Any])
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
            total_knowledge = session.query(func.count(KnowledgeBase.id)).scalar() or 0
            total_personas = session.query(func.count(PersonaCard.id)).scalar() or 0
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
        
        log_api_request(app_logger, "GET", "/admin/upload-stats", current_user.get("id"), status_code=200)
        return {"success": True, "data": stats}
        
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Get upload stats error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取上传统计失败: {str(e)}"
        )


@api_router.post("/messages/batch-delete", response_model=dict)
async def delete_messages(
    message_ids: List[str] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """批量删除消息（仅接收者可以删除）"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(f"Batch delete messages: message_ids={message_ids}, user_id={user_id}")

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

        return {
            "status": "success",
            "message": f"成功删除 {deleted_count} 条消息",
            "deleted_count": deleted_count
        }

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


@api_router.delete("/admin/uploads/{upload_id}", response_model=Dict[str, Any])
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
        app_logger.info(f"Delete upload record: upload_id={upload_id}, user_id={current_user.get('id')}")
        
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
        
        log_api_request(app_logger, "DELETE", f"/admin/uploads/{upload_id}", current_user.get("id"), status_code=200)
        return {"success": True, "message": "上传记录已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Delete upload record error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除上传记录失败: {str(e)}"
        )


@api_router.post("/admin/uploads/{upload_id}/reprocess", response_model=Dict[str, Any])
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
        app_logger.info(f"Reprocess upload record: upload_id={upload_id}, user_id={current_user.get('id')}")
        
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
        success = db_manager.update_upload_record_status_by_id(upload_id, "pending")
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="重新处理失败"
            )
        
        log_api_request(app_logger, "POST", f"/admin/uploads/{upload_id}/reprocess", current_user.get("id"), status_code=200)
        return {"success": True, "message": "已提交重新处理，等待审核"}
        
    except HTTPException:
        raise
    except Exception as e:
        log_exception(app_logger, "Reprocess upload record error", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新处理失败: {str(e)}"
        )


# 导出路由器