from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Body, Query
from typing import Dict, Any
import os
import hashlib
from datetime import datetime

from api_routes.response_util import Success, Page
from error_handlers import (
    APIError, ValidationError, AuthenticationError,
    NotFoundError, DatabaseError
)
from database_models import sqlite_db_manager
from user_management import get_current_user, create_user
from avatar_utils import (
    validate_image_file, save_avatar_file,
    delete_avatar_file, ensure_avatar_dir
)

# 导入错误处理和日志记录模块
from logging_config import app_logger, log_exception, log_file_operation, log_database_operation

# 创建路由器
user_router = APIRouter()

# 使用SQLite数据库管理器
db_manager = sqlite_db_manager


@user_router.post("/token")
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
            app_logger.info(
                f"Login successful: user_id={user.userID}, role={user.role}")

            # 获取密码版本号
            password_version = 0
            if user._db_user:
                password_version = user._db_user.password_version or 0

            # 创建JWT访问令牌和刷新令牌
            access_token = create_user_token(
                user.userID, user.username, user.role, password_version)
            refresh_token = create_refresh_token(user.userID)

            # 返回token和用户信息
            return Success(
                message="登录成功",
                data={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "expires_in": 5184000,  # 1天
                    "user": {
                        "id": user.userID,
                        "username": user.username,
                        "email": user.email,
                        "role": user.role
                    }
                })

        # 登录失败（统一错误消息，防止用户枚举）
        app_logger.warning(f"Login failed: username_hash={username_hash}")
        raise AuthenticationError("用户名或密码错误")

    except AuthenticationError:
        raise
    except Exception as e:
        log_exception(app_logger, "Login error", exception=e)
        raise APIError("登录过程中发生错误")


@user_router.post("/refresh")
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
        access_token = create_user_token(
            user.userID, user.username, user.role, password_version)

        app_logger.info(f"Token refreshed: user_id={user.userID}")

        return Success(
            message="令牌刷新成功",
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 5184000  # 1天
            })

    except (AuthenticationError, ValidationError):
        raise
    except Exception as e:
        log_exception(app_logger, "Refresh token error", exception=e)
        raise APIError("刷新令牌过程中发生错误")


@user_router.post("/send_verification_code")
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
        email_content = f"[麦麦笔记本] 验证码为：{code} ，有效期为 2 分钟，请尽快使用哦o(*￣▽￣*)o！"
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

        return Success(
            message="验证码已发送"
        )

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


@user_router.post("/user/check_register")
async def check_register(
        username: str = Form(...),
        email: str = Form(...),
):
    try:
        if not username or not email:
            raise ValidationError("有未填写的字段")

        email = email.lower()
        message = db_manager.check_user_register_legality(username, email)
        if message != "ok":
            raise ValidationError(message)

        return Success(
            message="可以注册"
        )
    except ValidationError:
        raise
    except Exception as e:
        log_exception(app_logger, "Check user register legality error", exception=e)
        raise APIError("检查注册信息失败")


@user_router.post("/send_reset_password_code")
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
        email_content = f"[麦麦笔记本] 验证码为：{code} ，有效期为 2 分钟，请尽快使用哦o(*￣▽￣*)o！"
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

        return Success(message="重置密码验证码已发送")

    except Exception as e:
        log_exception(
            app_logger, "Send reset password code error", exception=e)
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


@user_router.post("/reset_password")
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

        return Success(
            message="密码重置成功"
        )

    except Exception as e:
        log_exception(app_logger, "Reset password error", exception=e)
        raise APIError("重置密码失败")


@user_router.post("/user/register")
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

        message = db_manager.check_user_register_legality(username, email)
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

        return Success(
            message="注册成功"
        )
    except ValidationError:
        raise
    except Exception as e:
        log_exception(app_logger, "Register user error", exception=e)
        raise APIError("注册用户失败")


@user_router.get("/users/me", response_model=dict)
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

        return Success(
            message="用户信息获取成功",
            data={
                "id": user_id,
                "username": current_user.get("username", ""),
                "email": current_user.get("email", ""),
                "role": current_user.get("role", "user"),
                "avatar_url": avatar_url,
                "avatar_updated_at": avatar_updated_at
            }
        )
    except Exception as e:
        log_exception(app_logger, "Get user info error", exception=e)
        raise APIError("获取用户信息失败")


@user_router.put("/users/me/password", response_model=dict)
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
            app_logger.warning(
                f"Password change failed: wrong current password, user_id={user_id}")
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

        return Success(
            message="密码修改成功，请重新登录"
        )

    except (ValidationError, AuthenticationError, NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Change password error", exception=e)
        raise APIError("修改密码失败")


@user_router.post("/users/me/avatar", response_model=dict)
async def upload_avatar(
        avatar: UploadFile = File(...),
        current_user: dict = Depends(get_current_user)
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
        file_path, thumbnail_path = save_avatar_file(
            user_id, content, file_ext)

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
            file_path,
            user_id=user_id,
            success=True
        )

        app_logger.info(
            f"头像上传成功: user_id={user_id}, path={file_path}")

        return Success(
            message="头像上传成功",
            data={
                "avatar_url": f"/{file_path}",
                "avatar_updated_at": user.avatar_updated_at.isoformat()
            }
        )

    except (ValidationError, NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Upload avatar error", exception=e)
        raise APIError("上传头像失败")


@user_router.delete("/users/me/avatar", response_model=dict)
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

        return Success(
            message="头像已删除，已恢复为默认头像"
        )

    except (NotFoundError, DatabaseError):
        raise
    except Exception as e:
        log_exception(app_logger, "Delete avatar error", exception=e)
        raise APIError("删除头像失败")


@user_router.get("/users/{user_id}/avatar")
async def get_user_avatar(user_id: str, size: int = 200):
    """获取用户头像（如果不存在则生成首字母头像）"""
    try:
        from fastapi.responses import Response
        from avatar_utils import generate_initial_avatar
        from static_routes import static_file_security
        import os

        user = db_manager.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")

        if user.avatar_path and os.path.exists(user.avatar_path):
            avatar_path = user.avatar_path
            prefix = "uploads/avatars/"
            if avatar_path.startswith(prefix):
                avatar_path = avatar_path[len(prefix):]
            return static_file_security.serve_avatar(avatar_path)

        username = user.username or "?"
        avatar_bytes = generate_initial_avatar(username, size)

        ensure_avatar_dir()
        file_path, thumbnail_path = save_avatar_file(
            user_id, avatar_bytes, ".jpg")

        user.avatar_path = file_path
        user.avatar_updated_at = datetime.now()
        user_data = user.to_dict()
        if not db_manager.save_user(user_data):
            delete_avatar_file(file_path)
            raise DatabaseError("保存头像信息失败")

        log_file_operation(
            app_logger,
            "upload",
            file_path,
            user_id=user_id,
            success=True
        )

        app_logger.info(
            f"默认首字母头像生成并保存成功: user_id={user_id}, path={file_path}")

        return Response(
            content=avatar_bytes,
            media_type="image/png"
        )

    except NotFoundError:
        raise
    except Exception as e:
        log_exception(app_logger, "Get user avatar error", exception=e)
        raise APIError("获取用户头像失败")


# 用户Star记录相关路由
@user_router.get("/user/stars", response_model=Dict[str, Any])
async def get_user_stars(
        current_user: dict = Depends(get_current_user),
        include_details: bool = False,
        page: int = Query(1, description="页码，从1开始"),
        page_size: int = Query(20, description="每页条数，最大50"),
        sort_by: str = Query("created_at", description="排序字段: created_at / star_count"),
        sort_order: str = Query("desc", description="排序方向: asc / desc"),
        type: str = Query("all", description="收藏类型: knowledge / persona")
):
    """获取用户Star的知识库和人设卡"""
    user_id = current_user.get("id", "")
    try:
        app_logger.info(
            f"Get user stars: user_id={user_id}, include_details={include_details}, "
            f"page={page}, page_size={page_size}, sort_by={sort_by}, sort_order={sort_order}, type={type}")

        # 限制page_size的最大值
        page_size = min(page_size, 50)

        # 获取用户的所有Star记录
        stars = db_manager.get_stars_by_user(user_id)

        # 根据类型过滤
        if type != "all":
            stars = [star for star in stars if star.target_type == type]

        # 排序处理
        reverse_order = (sort_order == "desc")
        if sort_by == "star_count":
            # 按Star数量排序需要获取目标对象的信息
            star_items = []
            for star in stars:
                if star.target_type == "knowledge":
                    kb = db_manager.get_knowledge_base_by_id(star.target_id)
                    if kb and kb.is_public:
                        star_items.append((star, kb.star_count))
                elif star.target_type == "persona":
                    pc = db_manager.get_persona_card_by_id(star.target_id)
                    if pc and pc.is_public:
                        star_items.append((star, pc.star_count))

            # 按Star数量排序
            star_items.sort(key=lambda x: x[1], reverse=reverse_order)
            stars = [item[0] for item in star_items]
        else:
            # 默认按创建时间排序
            stars.sort(key=lambda x: x.created_at, reverse=reverse_order)

        # 构建结果列表
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
                        kb_dict = kb.to_dict(include_files=True)
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
                        pc_dict = pc.to_dict(include_files=True)
                        item.update(pc_dict)
                    result.append(item)

        # 计算总数和分页
        total = len(result)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_items = result[start_idx:end_idx]

        # 记录数据库操作成功
        log_database_operation(
            app_logger,
            "read",
            "star",
            user_id=user_id,
            success=True
        )

        app_logger.info(f"Returning {len(page_items)} items out of {total} total items")

        return Page(
            data=page_items,
            page=page,
            page_size=page_size,
            total=total,
            message="获取收藏记录成功"
        )
    except DatabaseError:
        raise
    except HTTPException:
        # 参数错误，直接抛出
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
        raise APIError("获取收藏记录失败")


# 用户上传历史和统计接口
@user_router.get("/me/upload-history", response_model=Dict[str, Any])
async def get_my_upload_history(
        page: int = Query(1, description="页码，从1开始"),
        page_size: int = Query(20, description="每页条数，最大100"),
        current_user: dict = Depends(get_current_user)
):
    """获取当前用户的个人上传历史记录（分页）"""
    try:
        user_id = current_user.get("id", "")
        app_logger.info(f"Get user upload history: user_id={user_id}, page={page}, page_size={page_size}")

        # 限制参数范围
        if page_size < 1 or page_size > 100:
            page_size = 20
        if page < 1:
            page = 1

        # 获取用户的上传记录
        upload_records = db_manager.get_upload_records_by_uploader(
            user_id, page=page, limit=page_size)

        # 构建返回数据
        history_list = []
        for record in upload_records:
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

            # 构建记录信息
            history_list.append({
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
                "uploadedAt": record.created_at.isoformat() if record.created_at else None
            })

        # 获取总数量
        total_count = db_manager.get_upload_records_count_by_uploader(user_id)

        log_database_operation(
            app_logger,
            "read",
            "upload_record",
            user_id=user_id,
            success=True
        )

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
            app_logger,
            "read",
            "upload_record",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("获取上传历史失败")


@user_router.get("/me/upload-stats", response_model=Dict[str, Any])
async def get_my_upload_stats(current_user: dict = Depends(get_current_user)):
    """获取当前用户的个人上传统计"""
    try:
        user_id = current_user.get("id", "")
        app_logger.info(f"Get user upload stats: user_id={user_id}")

        # 获取用户的统计信息
        stats = db_manager.get_upload_stats_by_uploader(user_id)

        log_database_operation(
            app_logger,
            "read",
            "upload_stats",
            user_id=user_id,
            success=True
        )

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
            }
        )

    except Exception as e:
        log_exception(app_logger, "Get user upload stats error", exception=e)
        log_database_operation(
            app_logger,
            "read",
            "upload_stats",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        raise APIError("获取上传统计失败")
