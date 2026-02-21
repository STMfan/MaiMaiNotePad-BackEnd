"""
错误处理中间件
提供统一的异常处理和错误响应
"""

import logging
import traceback
import uuid
import json
import os
from typing import Dict, Any, Optional, Union
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from datetime import datetime
from app.core.logging import app_logger, log_exception
from app.core.messages import get_message


DEFAULT_ERROR_CODE_BY_STATUS: Dict[int, str] = {
    400: "40000",
    401: "40001",
    403: "40003",
    404: "40004",
    409: "40009",
    422: "40022",
    429: "40029",
    500: "50000",
}


ERROR_CODE_BY_MESSAGE: Dict[str, str] = {
    "无效的JSON格式": "10001",
    "不支持的Content-Type": "10002",
    "请提供用户名和密码": "10003",
    "请提供刷新令牌": "10004",
    "邮箱格式无效": "10005",
    "有未填写的字段": "10006",
    "该邮箱未注册": "10007",
    "密码长度不能少于6位": "10008",
    "验证码错误或已失效": "10009",
    "新密码与确认密码不匹配": "10010",
    "新密码不能与当前密码相同": "10011",
    "登录过程中发生错误": "10012",
    "刷新令牌过程中发生错误": "10013",
    "请求发送验证码过于频繁，请稍后重试": "10014",
    "邮件发送失败: SMTP连接被意外关闭，请检查邮件服务器配置和网络连接": "10015",
    "邮件发送失败: 邮箱认证失败，请检查邮箱账号和授权码": "10016",
    "邮件发送失败: 连接超时，请检查网络连接和邮件服务器地址": "10017",
    "检查注册信息失败": "10018",
    "重置密码失败，请检查邮箱是否正确": "10019",
    "重置密码失败": "10020",
    "注册失败，系统错误，请稍后重试": "10021",
    "注册用户失败": "10022",
    "获取用户信息失败": "10023",
    "修改密码失败": "10024",
    "上传头像失败": "10100",
    "删除头像失败": "10101",
    "获取用户头像失败": "10102",
    "获取收藏记录失败": "10200",
    "获取上传历史失败": "10201",
    "获取上传统计失败": "10202",
    "获取个人数据概览失败": "10203",
    "获取个人数据趋势失败": "10204",
    "角色必须是 user、moderator 或 admin": "12000",
    "不能修改自己的角色": "12001",
    "只有超级管理员可以修改管理员或超级管理员的角色": "12002",
    "只有超级管理员可以任命管理员": "12003",
    "不能删除最后一个管理员": "12004",
    "禁言时长无效": "12005",
    "不能对自己进行禁言操作": "12006",
    "管理员不能对其它管理员或超级管理员进行禁言操作": "12007",
    "不能删除自己": "12008",
    "管理员不能删除其它管理员或超级管理员账号": "12009",
    "不能封禁自己": "12010",
    "管理员不能封禁其它管理员或超级管理员账号": "12011",
    "封禁时长无效": "12012",
    "管理员不能解封其它管理员或超级管理员账号": "12013",
    "用户名不能为空": "12014",
    "邮箱不能为空": "12015",
    "密码不能为空": "12016",
    "只有超级管理员可以创建管理员账号": "12017",
    "密码长度至少8位": "12018",
    "密码必须包含字母和数字": "12019",
    "该知识库已经是待审核状态": "13010",
    "不能退回已拒绝的知识库": "13011",
    "该人设卡已经是待审核状态": "14010",
    "不能退回已拒绝的人设卡": "14011",
    "消息ID列表不能为空": "15010",
    "消息标题不能为空": "15001",
    "消息内容不能为空": "15002",
    "只有公告类型消息可以使用广播功能": "15003",
    "接收者ID不能为空": "15004",
    "没有有效的接收者": "15005",
    "page和page_size必须大于0，page_size最多100条": "15006",
    "至少需要提供标题、内容或简介之一": "15007",
    "page_size必须在1-100之间": "15008",
    "page必须大于等于1": "15009",
    "目标类型必须是 knowledge 或 persona": "16001",
    "评论内容不能为空": "16002",
    "评论内容不能超过500字": "16003",
    "目标ID不能为空": "16004",
    "父级评论不存在": "16005",
    "action 必须是 like、dislike 或 clear": "16006",
    "名称和描述不能为空": "13001",
    "至少需要上传一个文件": "13002",
    "您已经创建过同名的知识库": "13003",
    "没有提供要更新的字段": "13004",
    "知识库不存在": "13005",
    "人设卡不存在": "14001",
    "至少需要上传一个文件": "14002",
    "上传人设卡失败": "14003",
    "获取公开人设卡失败": "14004",
    "获取人设卡详情失败": "14005",
    "检查Star状态失败": "14006",
    "获取用户人设卡失败": "14007",
    "修改人设卡失败": "14008",
    "取消Star人设卡失败": "14009",
    "删除人设卡失败": "14012",
    "添加文件失败": "14013",
    "删除文件失败": "14014",
    "下载文件失败": "14015",
    "上传知识库失败": "13006",
    "获取公开知识库失败": "13007",
    "获取知识库失败": "13008",
    "获取用户知识库失败": "13009",
    "取消Star知识库失败": "13012",
    "修改知识库失败": "13013",
    "添加文件失败": "13014",
    "删除文件失败": "13015",
    "下载文件失败": "13016",
    "删除知识库失败": "13017",
    "获取评论失败": "16010",
    "发表评论失败": "16011",
    "操作失败": "16012",
    "删除评论失败": "16013",
    "撤销删除评论失败": "16014",
    "发送消息失败": "15020",
    "获取消息详情失败": "15021",
    "获取消息列表失败": "15022",
    "按类型获取消息列表失败": "15023",
    "标记消息已读失败": "15024",
    "删除消息失败": "15025",
    "更新消息失败": "15026",
    "获取广播消息历史失败": "15027",
    "批量删除消息失败": "15028",
}


ERROR_CODE_BY_DETAIL_KEY: Dict[str, str] = {
    "PERSONA_FILE_COUNT_INVALID": "14020",
    "PERSONA_FILE_NAME_INVALID": "14021",
    "PERSONA_FILE_TYPE_INVALID": "14022",
    "PERSONA_FILE_SIZE_EXCEEDED": "14023",
    "PERSONA_FILE_CONTENT_SIZE_EXCEEDED": "14024",
    "PERSONA_TOML_VERSION_MISSING": "14025",
    "PERSONA_TOML_PARSE_ERROR": "14026",
}


def resolve_error_code(status_code: int, message: str, details: Optional[Dict[str, Any]] = None) -> str:
    detail_code = None
    if isinstance(details, dict):
        raw_code = details.get("code")
        if isinstance(raw_code, str):
            detail_code = raw_code
    if detail_code and detail_code in ERROR_CODE_BY_DETAIL_KEY:
        return ERROR_CODE_BY_DETAIL_KEY[detail_code]
    if message in ERROR_CODE_BY_MESSAGE:
        return ERROR_CODE_BY_MESSAGE[message]
    if message.startswith("发送验证码失败"):
        return "10025"
    if message.startswith("发送重置密码验证码失败"):
        return "10026"
    if message.endswith("知识库失败"):
        return "13050"
    if message.endswith("人设卡失败"):
        return "14050"
    return DEFAULT_ERROR_CODE_BY_STATUS.get(status_code, "99999")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ERROR_MESSAGES_FILE = os.path.join(BASE_DIR, "error_messages.json")


def load_error_messages() -> Dict[str, Any]:
    try:
        with open(ERROR_MESSAGES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as e:
        app_logger.warning(f"加载错误消息配置失败: {str(e)}")
    return {}


ERROR_MESSAGES: Dict[str, Any] = load_error_messages()


def resolve_display_message(code: str, fallback_message: str) -> str:
    config = ERROR_MESSAGES.get(code)
    if isinstance(config, dict):
        messages = config.get("messages")
        if isinstance(messages, dict):
            message_zh = messages.get("zh-CN") or messages.get("zh_CN")
            if isinstance(message_zh, str) and message_zh:
                return message_zh
        default_message = config.get("defaultMessage")
        if isinstance(default_message, str) and default_message:
            return default_message
    return fallback_message


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """错误处理中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # 生成请求ID
        request_id = str(uuid.uuid4())
        
        # 记录请求开始时间
        start_time = datetime.now()
        
        # 获取请求信息
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # 尝试获取用户信息
        user_id = None
        try:
            # 这里可以根据实际的认证机制获取用户ID
            # 例如从JWT token中解析
            auth_header = request.headers.get("authorization")
            if auth_header:
                # 这里可以解析token获取用户ID
                # 暂时留空，后续可以根据具体认证机制实现
                pass
        except Exception as e:
            app_logger.warning(f"获取用户信息失败: {str(e)}")
        
        # 记录请求开始
        app_logger.info(
            f"请求开始: {method} {path} - ID={request_id} - IP={client_ip} - User-Agent={user_agent}"
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 记录请求完成
            app_logger.info(
                f"请求完成: {method} {path} - ID={request_id} - Status={response.status_code} - Time={processing_time:.2f}ms"
            )
            
            # 添加请求ID到响应头
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except HTTPException as http_exc:
            # 处理HTTP异常
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 记录HTTP异常
            app_logger.warning(
                f"HTTP 异常: {method} {path} - ID={request_id} - Status={http_exc.status_code} - Time={processing_time:.2f}ms - Detail={http_exc.detail}"
            )
            
            # 返回错误响应
            return self._create_error_response(
                status_code=http_exc.status_code,
                error_type="HTTP_EXCEPTION",
                message=http_exc.detail,
                request_id=request_id,
                path=path
            )
            
        except Exception as exc:
            # 处理其他异常
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 记录未捕获的异常
            log_exception(
                app_logger,
                f"未捕获的异常 {method} {path}",
                exception=exc,
                reraise=False
            )
            
            # 返回服务器错误响应
            return self._create_error_response(
                status_code=500,
                error_type="INTERNAL_SERVER_ERROR",
                message="服务器内部错误",
                request_id=request_id,
                path=path,
                include_details=False  # 不向客户端暴露详细错误信息
            )
    
    def _create_error_response(
        self,
        status_code: int,
        error_type: str,
        message: str,
        request_id: str,
        path: str,
        include_details: bool = True
    ) -> JSONResponse:
        """创建错误响应"""
        code = resolve_error_code(status_code, message, None)
        display_message = resolve_display_message(code, message)
        error_response = {
            "success": False,
            "error": {
                "code": code,
                "type": error_type,
                "message": display_message,
                "request_id": request_id,
                "path": path,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # 在开发环境中可以包含更多错误详情
        if include_details and app_logger.level <= logging.DEBUG:
            error_response["error"]["debug_info"] = {
                "stack_trace": traceback.format_exc()
            }
        
        return JSONResponse(
            status_code=status_code,
            content=error_response
        )


class APIError(Exception):
    """自定义API错误类"""
    
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_type: str = "API_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIError):
    """数据验证错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_type="VALIDATION_ERROR",
            details=details
        )


class AuthenticationError(APIError):
    """认证错误"""
    
    def __init__(self, message: str = None):
        if message is None:
            message = get_message("authentication_failed")
        super().__init__(
            message=message,
            status_code=401,
            error_type="AUTHENTICATION_ERROR"
        )


class AuthorizationError(APIError):
    """授权错误"""
    
    def __init__(self, message: str = None):
        if message is None:
            message = get_message("access_denied")
        super().__init__(
            message=message,
            status_code=403,
            error_type="AUTHORIZATION_ERROR"
        )


class NotFoundError(APIError):
    """资源未找到错误"""
    
    def __init__(self, message: str = None):
        if message is None:
            message = get_message("resource_not_found")
        super().__init__(
            message=message,
            status_code=404,
            error_type="NOT_FOUND_ERROR"
        )


class ConflictError(APIError):
    """资源冲突错误"""
    
    def __init__(self, message: str = None):
        if message is None:
            message = get_message("resource_conflict")
        super().__init__(
            message=message,
            status_code=409,
            error_type="CONFLICT_ERROR"
        )


class RateLimitError(APIError):
    """请求频率限制错误"""
    
    def __init__(self, message: str = None):
        if message is None:
            message = get_message("rate_limit_exceeded")
        super().__init__(
            message=message,
            status_code=429,
            error_type="RATE_LIMIT_ERROR"
        )


class FileOperationError(APIError):
    """文件操作错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_type="FILE_OPERATION_ERROR",
            details=details
        )


class DatabaseError(APIError):
    """数据库操作错误"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_type="DATABASE_ERROR",
            details=details
        )


def setup_exception_handlers(app):
    """设置FastAPI异常处理器"""
    
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        """处理自定义API错误"""
        request_id = str(uuid.uuid4())
        
        # 记录错误
        app_logger.warning(
            f"API 错误: {request.method} {request.url.path} - ID={request_id} - Type={exc.error_type} - Message={exc.message}"
        )
        code = resolve_error_code(exc.status_code, exc.message, exc.details)
        display_message = resolve_display_message(code, exc.message)
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": code,
                    "type": exc.error_type,
                    "message": display_message,
                    "details": exc.details,
                    "request_id": request_id,
                    "path": request.url.path,
                    "timestamp": datetime.now().isoformat()
                }
            }
        )
    
    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        """处理数据验证错误"""
        request_id = str(uuid.uuid4())
        
        # 记录错误
        app_logger.warning(
            f"数据验证错误: {request.method} {request.url.path} - ID={request_id} - Message={exc.message}"
        )
        code = resolve_error_code(exc.status_code, exc.message, exc.details)
        display_message = resolve_display_message(code, exc.message)
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": code,
                    "type": exc.error_type,
                    "message": display_message,
                    "details": exc.details,
                    "request_id": request_id,
                    "path": request.url.path,
                    "timestamp": datetime.now().isoformat()
                }
            }
        )
