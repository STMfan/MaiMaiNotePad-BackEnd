"""
测试错误处理模块

测试 app/error_handlers.py 中的错误处理功能
"""

import pytest
import json
from unittest.mock import Mock, patch, mock_open
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.error_handlers import (
    resolve_error_code,
    load_error_messages,
    resolve_display_message,
    ErrorHandlerMiddleware,
    APIError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    FileOperationError,
    DatabaseError,
    setup_exception_handlers,
)


class TestResolveErrorCode:
    """测试错误代码解析功能"""

    def test_resolve_by_detail_code(self):
        """测试通过 detail code 解析错误代码"""
        details = {"code": "PERSONA_FILE_COUNT_INVALID"}
        code = resolve_error_code(400, "Some message", details)
        assert code == "14020"

    def test_resolve_by_message(self):
        """测试通过消息解析错误代码"""
        code = resolve_error_code(400, "无效的JSON格式", None)
        assert code == "10001"

    def test_resolve_by_message_prefix_verification_code(self):
        """测试发送验证码失败消息前缀匹配"""
        code = resolve_error_code(400, "发送验证码失败: 网络错误", None)
        assert code == "10025"

    def test_resolve_by_message_prefix_reset_password(self):
        """测试发送重置密码验证码失败消息前缀匹配"""
        code = resolve_error_code(400, "发送重置密码验证码失败: 网络错误", None)
        assert code == "10026"

    def test_resolve_by_message_suffix_knowledge(self):
        """测试知识库相关消息后缀匹配"""
        code = resolve_error_code(400, "创建知识库失败", None)
        assert code == "13050"

    def test_resolve_by_message_suffix_persona(self):
        """测试人设卡相关消息后缀匹配"""
        code = resolve_error_code(400, "创建人设卡失败", None)
        assert code == "14050"

    def test_resolve_by_status_code(self):
        """测试通过状态码解析错误代码"""
        code = resolve_error_code(404, "Unknown error", None)
        assert code == "40004"

    def test_resolve_unknown_error(self):
        """测试未知错误返回默认代码"""
        code = resolve_error_code(599, "Unknown error", None)
        assert code == "99999"

    def test_resolve_with_non_dict_details(self):
        """测试 details 不是字典时的处理"""
        code = resolve_error_code(400, "Some message", "not a dict")
        assert code in ["10001", "40000", "99999"]  # 应该回退到其他匹配方式


class TestLoadErrorMessages:
    """测试错误消息加载功能"""

    def test_load_error_messages_success(self):
        """测试成功加载错误消息配置"""
        mock_data = {"10001": {"messages": {"zh-CN": "测试消息"}}}
        mock_file_content = json.dumps(mock_data)

        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            messages = load_error_messages()
            assert isinstance(messages, dict)

    def test_load_error_messages_file_not_found(self):
        """测试文件不存在时返回空字典"""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            messages = load_error_messages()
            assert messages == {}

    def test_load_error_messages_invalid_json(self):
        """测试无效 JSON 时返回空字典"""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            messages = load_error_messages()
            assert messages == {}

    def test_load_error_messages_non_dict_content(self):
        """测试非字典内容时返回空字典"""
        with patch("builtins.open", mock_open(read_data='["not", "a", "dict"]')):
            messages = load_error_messages()
            assert messages == {}


class TestResolveDisplayMessage:
    """测试显示消息解析功能"""

    def test_resolve_with_zh_cn_message(self):
        """测试解析中文消息（zh-CN）"""
        with patch("app.core.error_handlers.ERROR_MESSAGES", {"10001": {"messages": {"zh-CN": "中文消息"}}}):
            message = resolve_display_message("10001", "fallback")
            assert message == "中文消息"

    def test_resolve_with_zh_cn_underscore_message(self):
        """测试解析中文消息（zh_CN）"""
        with patch("app.core.error_handlers.ERROR_MESSAGES", {"10001": {"messages": {"zh_CN": "中文消息"}}}):
            message = resolve_display_message("10001", "fallback")
            assert message == "中文消息"

    def test_resolve_with_default_message(self):
        """测试使用默认消息"""
        with patch("app.core.error_handlers.ERROR_MESSAGES", {"10001": {"defaultMessage": "默认消息"}}):
            message = resolve_display_message("10001", "fallback")
            assert message == "默认消息"

    def test_resolve_with_fallback(self):
        """测试使用回退消息"""
        with patch("app.core.error_handlers.ERROR_MESSAGES", {}):
            message = resolve_display_message("99999", "fallback message")
            assert message == "fallback message"

    def test_resolve_with_empty_zh_cn_message(self):
        """测试空的中文消息时使用回退"""
        with patch("app.core.error_handlers.ERROR_MESSAGES", {"10001": {"messages": {"zh-CN": ""}}}):
            message = resolve_display_message("10001", "fallback")
            assert message == "fallback"


class TestErrorHandlerMiddleware:
    """测试错误处理中间件"""

    @pytest.mark.asyncio
    async def test_successful_request(self):
        """测试成功的请求处理"""
        # 创建 mock 应用和请求
        mock_app = Mock(spec=ASGIApp)
        middleware = ErrorHandlerMiddleware(mock_app)

        # 创建 mock 请求
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "test-agent"

        # 创建 mock 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}

        # Mock call_next
        async def mock_call_next(request):
            return mock_response

        # 执行中间件
        response = await middleware.dispatch(mock_request, mock_call_next)

        # 验证响应
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    @pytest.mark.asyncio
    async def test_http_exception_handling(self):
        """测试 HTTP 异常处理"""
        mock_app = Mock(spec=ASGIApp)
        middleware = ErrorHandlerMiddleware(mock_app)

        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "test-agent"

        # Mock call_next 抛出 HTTPException
        async def mock_call_next(request):
            raise HTTPException(status_code=404, detail="Not found")

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_unhandled_exception(self):
        """测试未处理的异常"""
        mock_app = Mock(spec=ASGIApp)
        middleware = ErrorHandlerMiddleware(mock_app)

        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "test-agent"

        # Mock call_next 抛出普通异常
        async def mock_call_next(request):
            raise ValueError("Unexpected error")

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_request_without_client(self):
        """测试没有客户端信息的请求"""
        mock_app = Mock(spec=ASGIApp)
        middleware = ErrorHandlerMiddleware(mock_app)

        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.client = None
        mock_request.headers.get.return_value = "test-agent"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}

        async def mock_call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200


class TestAPIError:
    """测试 APIError 异常类"""

    def test_api_error_creation(self):
        """测试创建 APIError"""
        error = APIError("Test error", status_code=400, error_type="TEST_ERROR")
        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.error_type == "TEST_ERROR"
        assert error.details == {}

    def test_api_error_with_details(self):
        """测试带详情的 APIError"""
        details = {"field": "username", "reason": "invalid"}
        error = APIError("Test error", details=details)
        assert error.details == details


class TestValidationError:
    """测试 ValidationError 异常类"""

    def test_validation_error_creation(self):
        """测试创建 ValidationError"""
        error = ValidationError("Validation failed")
        assert error.message == "Validation failed"
        assert error.status_code == 422
        assert error.error_type == "VALIDATION_ERROR"

    def test_validation_error_with_details(self):
        """测试带详情的 ValidationError"""
        details = {"field": "email", "reason": "invalid format"}
        error = ValidationError("Invalid email", details=details)
        assert error.details == details


class TestAuthenticationError:
    """测试 AuthenticationError 异常类"""

    def test_authentication_error_default(self):
        """测试默认 AuthenticationError"""
        error = AuthenticationError()
        assert error.message == "Authentication failed"
        assert error.status_code == 401
        assert error.error_type == "AUTHENTICATION_ERROR"

    def test_authentication_error_custom_message(self):
        """测试自定义消息的 AuthenticationError"""
        error = AuthenticationError("Invalid token")
        assert error.message == "Invalid token"


class TestAuthorizationError:
    """测试 AuthorizationError 异常类"""

    def test_authorization_error_default(self):
        """测试默认 AuthorizationError"""
        error = AuthorizationError()
        assert error.message == "Access denied"
        assert error.status_code == 403
        assert error.error_type == "AUTHORIZATION_ERROR"

    def test_authorization_error_custom_message(self):
        """测试自定义消息的 AuthorizationError"""
        error = AuthorizationError("Insufficient permissions")
        assert error.message == "Insufficient permissions"


class TestNotFoundError:
    """测试 NotFoundError 异常类"""

    def test_not_found_error_default(self):
        """测试默认 NotFoundError"""
        error = NotFoundError()
        assert error.message == "Resource not found"
        assert error.status_code == 404
        assert error.error_type == "NOT_FOUND_ERROR"

    def test_not_found_error_custom_message(self):
        """测试自定义消息的 NotFoundError"""
        error = NotFoundError("User not found")
        assert error.message == "User not found"


class TestConflictError:
    """测试 ConflictError 异常类"""

    def test_conflict_error_default(self):
        """测试默认 ConflictError"""
        error = ConflictError()
        assert error.message == "Resource conflict"
        assert error.status_code == 409
        assert error.error_type == "CONFLICT_ERROR"

    def test_conflict_error_custom_message(self):
        """测试自定义消息的 ConflictError"""
        error = ConflictError("Username already exists")
        assert error.message == "Username already exists"


class TestRateLimitError:
    """测试 RateLimitError 异常类"""

    def test_rate_limit_error_default(self):
        """测试默认 RateLimitError"""
        error = RateLimitError()
        assert error.message == "Rate limit exceeded"
        assert error.status_code == 429
        assert error.error_type == "RATE_LIMIT_ERROR"

    def test_rate_limit_error_custom_message(self):
        """测试自定义消息的 RateLimitError"""
        error = RateLimitError("Too many requests")
        assert error.message == "Too many requests"


class TestFileOperationError:
    """测试 FileOperationError 异常类"""

    def test_file_operation_error(self):
        """测试 FileOperationError"""
        error = FileOperationError("File upload failed")
        assert error.message == "File upload failed"
        assert error.status_code == 400
        assert error.error_type == "FILE_OPERATION_ERROR"

    def test_file_operation_error_with_details(self):
        """测试带详情的 FileOperationError"""
        details = {"filename": "test.txt", "reason": "too large"}
        error = FileOperationError("File too large", details=details)
        assert error.details == details


class TestDatabaseError:
    """测试 DatabaseError 异常类"""

    def test_database_error(self):
        """测试 DatabaseError"""
        error = DatabaseError("Database connection failed")
        assert error.message == "Database connection failed"
        assert error.status_code == 500
        assert error.error_type == "DATABASE_ERROR"

    def test_database_error_with_details(self):
        """测试带详情的 DatabaseError"""
        details = {"query": "SELECT * FROM users", "error": "timeout"}
        error = DatabaseError("Query timeout", details=details)
        assert error.details == details


class TestSetupExceptionHandlers:
    """测试异常处理器设置"""

    @pytest.mark.asyncio
    async def test_api_error_handler(self):
        """测试 APIError 处理器"""
        from fastapi import FastAPI

        app = FastAPI()
        setup_exception_handlers(app)

        # 创建 mock 请求
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test"

        # 创建 APIError
        error = APIError("Test error", status_code=400)

        # 获取处理器
        handler = app.exception_handlers.get(APIError)
        assert handler is not None

        # 调用处理器
        response = await handler(mock_request, error)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_validation_error_handler(self):
        """测试 ValidationError 处理器"""
        from fastapi import FastAPI

        app = FastAPI()
        setup_exception_handlers(app)

        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/test"

        error = ValidationError("Validation failed", details={"field": "email"})

        handler = app.exception_handlers.get(ValidationError)
        assert handler is not None

        response = await handler(mock_request, error)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
