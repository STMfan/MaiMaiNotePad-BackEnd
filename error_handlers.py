"""
错误处理中间件
提供统一的异常处理和错误响应
"""

import logging
import traceback
import uuid
from typing import Dict, Any, Optional, Union
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from datetime import datetime
from logging_config import app_logger, log_exception


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
            app_logger.warning(f"Failed to get user info: {str(e)}")
        
        # 记录请求开始
        app_logger.info(
            f"Request started: {method} {path} - ID={request_id} - IP={client_ip} - User-Agent={user_agent}"
        )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 记录请求完成
            app_logger.info(
                f"Request completed: {method} {path} - ID={request_id} - Status={response.status_code} - Time={processing_time:.2f}ms"
            )
            
            # 添加请求ID到响应头
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except HTTPException as http_exc:
            # 处理HTTP异常
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 记录HTTP异常
            app_logger.warning(
                f"HTTP Exception: {method} {path} - ID={request_id} - Status={http_exc.status_code} - Time={processing_time:.2f}ms - Detail={http_exc.detail}"
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
                f"Unhandled exception in {method} {path}",
                exception=exc,
                reraise=False
            )
            
            # 返回服务器错误响应
            return self._create_error_response(
                status_code=500,
                error_type="INTERNAL_SERVER_ERROR",
                message="Internal server error",
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
        error_response = {
            "success": False,
            "error": {
                "type": error_type,
                "message": message,
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
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            error_type="AUTHENTICATION_ERROR"
        )


class AuthorizationError(APIError):
    """授权错误"""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            status_code=403,
            error_type="AUTHORIZATION_ERROR"
        )


class NotFoundError(APIError):
    """资源未找到错误"""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            status_code=404,
            error_type="NOT_FOUND_ERROR"
        )


class ConflictError(APIError):
    """资源冲突错误"""
    
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(
            message=message,
            status_code=409,
            error_type="CONFLICT_ERROR"
        )


class RateLimitError(APIError):
    """请求频率限制错误"""
    
    def __init__(self, message: str = "Rate limit exceeded"):
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
            f"API Error: {request.method} {request.url.path} - ID={request_id} - Type={exc.error_type} - Message={exc.message}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "type": exc.error_type,
                    "message": exc.message,
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
            f"Validation Error: {request.method} {request.url.path} - ID={request_id} - Message={exc.message}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "type": exc.error_type,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": request_id,
                    "path": request.url.path,
                    "timestamp": datetime.now().isoformat()
                }
            }
        )