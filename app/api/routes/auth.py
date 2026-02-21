"""认证路由模块 - 处理用户登录、注册、密码重置等认证相关的API端点"""
from fastapi import APIRouter, Depends, Form, Request
from typing import Dict, Any
import hashlib

from app.api.response_util import Success
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.email_service import EmailService
from app.models.schemas import (
    BaseResponse,
    LoginResponse,
    TokenResponse,
)
from app.core.logging import app_logger, log_exception, log_database_operation
from app.core.error_handlers import (
    APIError, ValidationError, AuthenticationError
)
from sqlalchemy.orm import Session

# 创建路由器
router = APIRouter()


# 认证相关路由（登录、注册、密码重置等）


@router.post(
    "/token",
    response_model=BaseResponse[LoginResponse]
)
async def login(
    request: Request,
    db: Session = Depends(get_db)
):
    """用户登录获取访问令牌，支持JSON和表单数据格式（带速率限制和账户锁定）"""
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

        auth_service = AuthService(db)
        result = auth_service.authenticate_user(username, password)

        if result:
            app_logger.info(
                f"Login successful: user_id={result['user']['id']}, role={result['user']['role']}")
            
            return Success(
                message="登录成功",
                data=result
            )

        # 登录失败（统一错误消息，防止用户枚举）
        app_logger.warning(f"Login failed: username_hash={username_hash}")
        raise AuthenticationError("用户名或密码错误")

    except AuthenticationError:
        raise
    except Exception as e:
        log_exception(app_logger, "Login error", exception=e)
        raise APIError("登录过程中发生错误")


@router.post(
    "/refresh",
    response_model=BaseResponse[TokenResponse]
)
async def refresh_token(
    request: Request,
    db: Session = Depends(get_db)
):
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

        auth_service = AuthService(db)
        result = auth_service.refresh_access_token(refresh_token)

        app_logger.info(f"Token refreshed: user_id={result.get('user_id', 'unknown')}")

        return Success(
            message="令牌刷新成功",
            data=result
        )

    except (AuthenticationError, ValidationError):
        raise
    except Exception as e:
        log_exception(app_logger, "Refresh token error", exception=e)
        raise APIError("刷新令牌过程中发生错误")


@router.post(
    "/send_verification_code",
    response_model=BaseResponse[None]
)
async def send_verification_code(
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """发送注册验证码"""
    try:
        # 统一转换为小写
        email = email.lower()
        app_logger.info(f"Send verification code: email={email}")

        # 1. 验证邮箱格式
        if "@" not in email:
            raise ValidationError("邮箱格式无效")

        auth_service = AuthService(db)
        
        # 2. 检查频率限制
        if not auth_service.check_email_rate_limit(email):
            raise APIError("请求发送验证码过于频繁，请稍后重试")

        # 3. 生成并发送验证码
        code_id = auth_service.send_verification_code(email)

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


@router.post(
    "/user/check_register",
    response_model=BaseResponse[None]
)
async def check_register(
    username: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """检查用户名和邮箱是否可以注册"""
    try:
        if not username or not email:
            raise ValidationError("有未填写的字段")

        email = email.lower()
        
        auth_service = AuthService(db)
        message = auth_service.check_register_legality(username, email)
        
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


@router.post(
    "/send_reset_password_code",
    response_model=BaseResponse[None]
)
async def send_reset_password_code(
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """发送重置密码验证码"""
    try:
        # 统一转换为小写
        email = email.lower()
        app_logger.info(f"Send reset password code: email={email}")

        # 1. 验证邮箱格式
        if "@" not in email:
            raise ValidationError("邮箱格式无效")

        auth_service = AuthService(db)
        
        # 2. 检查邮箱是否已注册
        user_service = UserService(db)
        user = user_service.get_user_by_email(email)
        if not user:
            raise ValidationError("该邮箱未注册")

        # 3. 检查频率限制
        if not auth_service.check_email_rate_limit(email):
            raise APIError("请求发送验证码过于频繁，请稍后重试")

        # 4. 生成并发送验证码
        code_id = auth_service.send_reset_password_code(email)

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


@router.post(
    "/reset_password",
    response_model=BaseResponse[None]
)
async def reset_password(
    email: str = Form(...),
    verification_code: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
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

        auth_service = AuthService(db)
        
        # 3. 验证邮箱验证码并重置密码
        if not auth_service.reset_password(email, verification_code, new_password):
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


@router.post(
    "/user/register",
    response_model=BaseResponse[None]
)
async def user_register(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    verification_code: str = Form(...),
    db: Session = Depends(get_db)
):
    """用户注册"""
    try:
        if not username or not password or not email or not verification_code:
            raise ValidationError("有未填写的字段")

        # 统一转换为小写
        email = email.lower()

        auth_service = AuthService(db)
        
        # 检查注册合法性
        message = auth_service.check_register_legality(username, email)
        if message != "ok":
            raise ValidationError(message)

        # 验证邮箱验证码
        if not auth_service.verify_email_code(email, verification_code):
            raise ValidationError("验证码错误或已失效")

        # 注册用户
        new_user = auth_service.register_user(username, password, email)
        if not new_user:
            raise APIError("注册失败，系统错误，请稍后重试")

        log_database_operation(
            app_logger,
            "create",
            "user",
            user_id=new_user.id,
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
