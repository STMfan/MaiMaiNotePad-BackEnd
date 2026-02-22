"""
异常注入器模块

提供用于测试异常处理的工具类，支持注入各种类型的异常。
用于系统化地测试所有服务层的异常处理和错误路径。
"""

from typing import Optional, Any, Dict, Type
from contextlib import contextmanager
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class ExceptionType:
    """异常类型常量"""

    DATABASE = "database"
    VALIDATION = "validation"
    PERMISSION = "permission"
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    ENCODING = "encoding"


class ExceptionInjector:
    """
    异常注入器类

    用于在测试中注入各种类型的异常，以测试异常处理逻辑。
    支持临时注入和自动恢复，使用上下文管理器接口。

    Example:
        >>> injector = ExceptionInjector()
        >>> with injector.inject_database_error("query"):
        ...     # 在此上下文中，数据库查询会抛出异常
        ...     result = service.get_user_by_id("test_id")
        ...     assert result is None
    """

    def __init__(self):
        """初始化异常注入器"""
        self._active_patches: Dict[str, Any] = {}
        self._original_values: Dict[str, Any] = {}

    @contextmanager
    def inject_database_error(
        self,
        operation: str = "query",
        error_type: Type[Exception] = SQLAlchemyError,
        error_message: str = "Database operation failed",
    ):
        """
        注入数据库异常

        在指定的数据库操作中注入异常，用于测试数据库错误处理。

        Args:
            operation: 数据库操作类型，可选值：
                - "query": 查询操作
                - "commit": 提交操作
                - "add": 添加操作
                - "delete": 删除操作
                - "update": 更新操作
                - "refresh": 刷新操作
                - "flush": 刷新缓存操作
                - "rollback": 回滚操作
                - "scalar": 标量查询操作
                - "first": 获取第一条记录操作
                - "filter": 过滤操作
                - "count": 计数操作
                - "all": 所有操作
            error_type: 异常类型，默认为 SQLAlchemyError
            error_message: 异常消息

        Yields:
            None

        Example:
            >>> with injector.inject_database_error("query"):
            ...     result = user_service.get_user_by_id("test_id")
            ...     assert result is None
        """
        patches = []
        injectors = self._get_operation_injectors()

        try:
            if operation == "all":
                # 注入所有操作的异常
                for injector in injectors.values():
                    patch_obj = injector(error_type, error_message)
                    patches.append(patch_obj)
            elif operation in injectors:
                # 注入指定操作的异常
                patch_obj = injectors[operation](error_type, error_message)
                patches.append(patch_obj)

            yield

        finally:
            # 停止所有 patches
            for p in patches:
                p.stop()
            logger.debug("Database error injection cleaned up")

    def _inject_query_error(self, error_type: Type[Exception], error_message: str) -> Any:
        """注入查询操作异常"""
        query_patch = patch("sqlalchemy.orm.Session.query")
        mock_query = query_patch.start()
        mock_query.side_effect = error_type(error_message)
        logger.debug(f"Injected database error for query operation: {error_message}")
        return query_patch

    def _inject_commit_error(self, error_type: Type[Exception], error_message: str) -> Any:
        """注入提交操作异常"""
        commit_patch = patch("sqlalchemy.orm.Session.commit")
        mock_commit = commit_patch.start()
        mock_commit.side_effect = error_type(error_message)
        logger.debug(f"Injected database error for commit operation: {error_message}")
        return commit_patch

    def _inject_add_error(self, error_type: Type[Exception], error_message: str) -> Any:
        """注入添加操作异常"""
        add_patch = patch("sqlalchemy.orm.Session.add")
        mock_add = add_patch.start()
        mock_add.side_effect = error_type(error_message)
        logger.debug(f"Injected database error for add operation: {error_message}")
        return add_patch

    def _inject_delete_error(self, error_type: Type[Exception], error_message: str) -> Any:
        """注入删除操作异常"""
        delete_patch = patch("sqlalchemy.orm.Session.delete")
        mock_delete = delete_patch.start()
        mock_delete.side_effect = error_type(error_message)
        logger.debug(f"Injected database error for delete operation: {error_message}")
        return delete_patch

    def _inject_update_error(self, error_type: Type[Exception], error_message: str) -> Any:
        """注入更新操作异常"""
        execute_patch = patch("sqlalchemy.orm.Session.execute")
        mock_execute = execute_patch.start()
        mock_execute.side_effect = error_type(error_message)
        logger.debug(f"Injected database error for update operation: {error_message}")
        return execute_patch

    def _inject_refresh_error(self, error_type: Type[Exception], error_message: str) -> Any:
        """注入刷新操作异常"""
        refresh_patch = patch("sqlalchemy.orm.Session.refresh")
        mock_refresh = refresh_patch.start()
        mock_refresh.side_effect = error_type(error_message)
        logger.debug(f"Injected database error for refresh operation: {error_message}")
        return refresh_patch

    def _inject_flush_error(self, error_type: Type[Exception], error_message: str) -> Any:
        """注入刷新缓存操作异常"""
        flush_patch = patch("sqlalchemy.orm.Session.flush")
        mock_flush = flush_patch.start()
        mock_flush.side_effect = error_type(error_message)
        logger.debug(f"Injected database error for flush operation: {error_message}")
        return flush_patch

    def _inject_rollback_error(self, error_type: Type[Exception], error_message: str) -> Any:
        """注入回滚操作异常"""
        rollback_patch = patch("sqlalchemy.orm.Session.rollback")
        mock_rollback = rollback_patch.start()
        mock_rollback.side_effect = error_type(error_message)
        logger.debug(f"Injected database error for rollback operation: {error_message}")
        return rollback_patch

    def _inject_scalar_error(self, error_type: Type[Exception], error_message: str) -> Any:
        """注入标量查询操作异常"""
        scalar_patch = patch("sqlalchemy.orm.Query.scalar")
        mock_scalar = scalar_patch.start()
        mock_scalar.side_effect = error_type(error_message)
        logger.debug(f"Injected database error for scalar operation: {error_message}")
        return scalar_patch

    def _inject_first_error(self, error_type: Type[Exception], error_message: str) -> Any:
        """注入获取第一条记录操作异常"""
        first_patch = patch("sqlalchemy.orm.Query.first")
        mock_first = first_patch.start()
        mock_first.side_effect = error_type(error_message)
        logger.debug(f"Injected database error for first operation: {error_message}")
        return first_patch

    def _inject_filter_error(self, error_type: Type[Exception], error_message: str) -> Any:
        """注入过滤操作异常"""
        filter_patch = patch("sqlalchemy.orm.Query.filter")
        mock_filter = filter_patch.start()
        mock_filter.side_effect = error_type(error_message)
        logger.debug(f"Injected database error for filter operation: {error_message}")
        return filter_patch

    def _inject_count_error(self, error_type: Type[Exception], error_message: str) -> Any:
        """注入计数操作异常"""
        count_patch = patch("sqlalchemy.orm.Query.count")
        mock_count = count_patch.start()
        mock_count.side_effect = error_type(error_message)
        logger.debug(f"Injected database error for count operation: {error_message}")
        return count_patch

    def _get_operation_injectors(self) -> dict:
        """获取操作类型到注入方法的映射"""
        return {
            "query": self._inject_query_error,
            "commit": self._inject_commit_error,
            "add": self._inject_add_error,
            "delete": self._inject_delete_error,
            "update": self._inject_update_error,
            "refresh": self._inject_refresh_error,
            "flush": self._inject_flush_error,
            "rollback": self._inject_rollback_error,
            "scalar": self._inject_scalar_error,
            "first": self._inject_first_error,
            "filter": self._inject_filter_error,
            "count": self._inject_count_error,
        }

    @contextmanager
    def inject_integrity_error(self, constraint: str = "unique_constraint", error_message: Optional[str] = None):
        """
            注入数据库完整性约束错误

            用于测试唯一约束、外键约束等违反时的处理。

        Args:
            constraint: 约束类型（如 "unique_constraint", "foreign_key"）
            error_message: 自定义错误消息

        Yields:
            None

        Example:
            >>> with injector.inject_integrity_error("unique_constraint"):
            ...     result = user_service.create_user("duplicate", "test@example.com", "password")
            ...     assert result is None
        """
        if error_message is None:
            error_message = f"Integrity constraint violation: {constraint}"

        # 使用通用的 SQLAlchemyError 代替 IntegrityError
        # 因为 IntegrityError 需要特殊的初始化参数
        with self.inject_database_error(operation="commit", error_type=SQLAlchemyError, error_message=error_message):
            yield

    @contextmanager
    def inject_operational_error(self, error_message: str = "Database connection lost"):
        """
        注入数据库操作错误

        用于测试数据库连接丢失、超时等操作错误。

        Args:
            error_message: 错误消息

        Yields:
            None

        Example:
            >>> with injector.inject_operational_error():
            ...     result = user_service.get_all_users()
            ...     assert result == []
        """
        # OperationalError 需要特殊的初始化参数
        # 使用通用的 SQLAlchemyError 代替
        with self.inject_database_error(operation="query", error_type=SQLAlchemyError, error_message=error_message):
            yield

    @contextmanager
    def inject_validation_error(self, field: str, error_message: Optional[str] = None, error_type: str = "value_error"):
        """
        注入验证错误

        用于测试数据验证失败时的处理。支持多种验证错误场景。

        Args:
            field: 验证失败的字段名
            error_message: 自定义错误消息
            error_type: 错误类型，可选值：
                - "value_error": 值错误（默认）
                - "type_error": 类型错误
                - "required_error": 必填字段缺失
                - "format_error": 格式错误
                - "length_error": 长度错误
                - "range_error": 范围错误
                - "custom_validation": 自定义验证错误（使用 app.error_handlers.ValidationError）

        Yields:
            None

        Example:
            >>> # 测试值错误
            >>> with injector.inject_validation_error("email", error_type="value_error"):
            ...     result = user_service.create_user("test", "invalid-email", "password")
            ...     assert result is None

            >>> # 测试必填字段
            >>> with injector.inject_validation_error("username", error_type="required_error"):
            ...     result = user_service.create_user("", "test@example.com", "password")
            ...     assert result is None

            >>> # 测试自定义验证错误
            >>> with injector.inject_validation_error("role", error_type="custom_validation"):
            ...     result = admin_service.change_role(user_id, "invalid_role")
            ...     assert result is None
        """
        if error_message is None:
            error_message = self._get_default_error_message(field, error_type)

        patches = []

        try:
            if error_type == "custom_validation":
                patch_obj = self._inject_custom_validation_error(error_message)
            elif error_type == "type_error":
                patch_obj = self._inject_type_error(error_message)
            else:
                # 默认使用值错误（包括 required_error, format_error, length_error, range_error）
                patch_obj = self._inject_value_error(error_message)

            patches.append(patch_obj)
            logger.debug(f"Injected validation error (type: {error_type}) for field '{field}': {error_message}")
            yield

        finally:
            for p in patches:
                p.stop()
            logger.debug("Validation error injection cleaned up")

    def _get_default_error_message(self, field: str, error_type: str) -> str:
        """获取默认的错误消息"""
        error_messages = {
            "required_error": f"Field '{field}' is required",
            "type_error": f"Invalid type for field '{field}'",
            "format_error": f"Invalid format for field '{field}'",
            "length_error": f"Invalid length for field '{field}'",
            "range_error": f"Value out of range for field '{field}'",
        }
        return error_messages.get(error_type, f"Validation failed for field: {field}")

    def _inject_custom_validation_error(self, error_message: str) -> Any:
        """注入自定义验证错误"""
        try:
            from app.core.error_handlers import ValidationError as CustomValidationError

            validation_patch = patch("app.core.error_handlers.ValidationError")
            mock_validation = validation_patch.start()
            mock_validation.side_effect = CustomValidationError(error_message)
            return validation_patch

        except ImportError:
            logger.warning("Could not import custom ValidationError, using ValueError instead")
            validation_patch = patch("pydantic.BaseModel.model_validate")
            mock_validate = validation_patch.start()
            mock_validate.side_effect = ValueError(error_message)
            return validation_patch

    def _inject_type_error(self, error_message: str) -> Any:
        """注入类型错误"""
        validation_patch = patch("pydantic.BaseModel.model_validate")
        mock_validate = validation_patch.start()
        mock_validate.side_effect = TypeError(error_message)
        return validation_patch

    def _inject_value_error(self, error_message: str) -> Any:
        """注入值错误"""
        validation_patch = patch("pydantic.BaseModel.model_validate")
        mock_validate = validation_patch.start()
        mock_validate.side_effect = ValueError(error_message)
        return validation_patch

    @contextmanager
    def inject_permission_error(
        self,
        error_message: str = "Permission denied",
        permission_type: str = "password_verify",
        role: Optional[str] = None,
    ):
        """
        注入权限错误

        用于测试权限检查失败时的处理。支持多种权限场景。

        Args:
            error_message: 错误消息
            permission_type: 权限类型，可选值：
                - "password_verify": 密码验证失败（默认）
                - "role_check": 角色检查失败（需要指定 role）
                - "admin": 管理员权限检查失败
                - "moderator": 审核员权限检查失败
                - "super_admin": 超级管理员权限检查失败
                - "resource_access": 资源访问权限失败
                - "http_403": HTTP 403 权限不足异常
            role: 当 permission_type 为 "role_check" 时，指定要检查的角色

        Yields:
            None

        Example:
            >>> # 测试密码验证失败
            >>> with injector.inject_permission_error():
            ...     with pytest.raises(PermissionError):
            ...         user_service.promote_to_admin("user_id", "wrong_password")

            >>> # 测试管理员权限检查失败
            >>> with injector.inject_permission_error(permission_type="admin"):
            ...     response = client.get("/api/admin/users")
            ...     assert response.status_code == 403

            >>> # 测试角色检查失败
            >>> with injector.inject_permission_error(permission_type="role_check", role="admin"):
            ...     result = service.check_user_role(user_id, "admin")
            ...     assert result is False

            >>> # 测试资源访问权限失败
            >>> with injector.inject_permission_error(permission_type="resource_access"):
            ...     result = service.can_access_resource(user_id, resource_id)
            ...     assert result is False
        """
        patches = []

        try:
            if permission_type == "password_verify":
                # Mock 密码验证失败
                permission_patch = patch("app.core.security.verify_password")
                mock_verify = permission_patch.start()
                mock_verify.return_value = False
                patches.append(permission_patch)
                logger.debug(f"Injected password verification failure: {error_message}")

            elif permission_type == "admin":
                # Mock 管理员权限检查失败
                # 方法1: Mock get_admin_user 依赖
                from fastapi import HTTPException, status

                admin_patch = patch("app.api.deps.get_admin_user")
                mock_admin = admin_patch.start()
                mock_admin.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_message)
                patches.append(admin_patch)

                # 方法2: Mock 用户的 is_admin 属性
                user_patch = patch("app.api.deps.get_current_user")
                mock_user = user_patch.start()
                mock_user.return_value = {
                    "id": "test_user_id",
                    "username": "test_user",
                    "email": "test@example.com",
                    "role": "user",
                    "is_admin": False,
                    "is_moderator": False,
                    "is_super_admin": False,
                }
                patches.append(user_patch)
                logger.debug(f"Injected admin permission failure: {error_message}")

            elif permission_type == "moderator":
                # Mock 审核员权限检查失败
                from fastapi import HTTPException, status

                moderator_patch = patch("app.api.deps.get_moderator_user")
                mock_moderator = moderator_patch.start()
                mock_moderator.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_message)
                patches.append(moderator_patch)

                # Mock 用户的 is_moderator 属性
                user_patch = patch("app.api.deps.get_current_user")
                mock_user = user_patch.start()
                mock_user.return_value = {
                    "id": "test_user_id",
                    "username": "test_user",
                    "email": "test@example.com",
                    "role": "user",
                    "is_admin": False,
                    "is_moderator": False,
                    "is_super_admin": False,
                }
                patches.append(user_patch)
                logger.debug(f"Injected moderator permission failure: {error_message}")

            elif permission_type == "super_admin":
                # Mock 超级管理员权限检查失败
                user_patch = patch("app.api.deps.get_current_user")
                mock_user = user_patch.start()
                mock_user.return_value = {
                    "id": "test_user_id",
                    "username": "test_user",
                    "email": "test@example.com",
                    "role": "admin",
                    "is_admin": True,
                    "is_moderator": True,
                    "is_super_admin": False,  # 不是超级管理员
                }
                patches.append(user_patch)
                logger.debug(f"Injected super_admin permission failure: {error_message}")

            elif permission_type == "role_check":
                # Mock 角色检查失败
                if role:
                    # Mock 用户角色不匹配
                    user_patch = patch("app.api.deps.get_current_user")
                    mock_user = user_patch.start()
                    mock_user.return_value = {
                        "id": "test_user_id",
                        "username": "test_user",
                        "email": "test@example.com",
                        "role": "user",  # 普通用户
                        "is_admin": False,
                        "is_moderator": False,
                        "is_super_admin": False,
                    }
                    patches.append(user_patch)
                    logger.debug(f"Injected role check failure for role '{role}': {error_message}")
                else:
                    logger.warning("role_check permission type requires 'role' parameter")

            elif permission_type == "resource_access":
                # Mock 资源访问权限失败
                # 这是一个通用的权限检查失败，可以用于各种资源访问场景
                # 使用一个通用的 mock 来模拟权限检查返回 False
                # 注意：这个 mock 需要在实际使用时根据具体的权限检查方法进行调整

                # 方法1: Mock HTTPException 抛出 403 错误
                from fastapi import HTTPException, status

                access_patch = patch("app.api.deps.get_current_user")
                mock_access = access_patch.start()
                mock_access.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_message)
                patches.append(access_patch)
                logger.debug(f"Injected resource access permission failure: {error_message}")

            elif permission_type == "http_403":
                # Mock HTTP 403 权限不足异常
                from fastapi import HTTPException, status

                http_patch = patch("app.api.deps.get_current_user")
                mock_http = http_patch.start()
                mock_http.side_effect = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_message)
                patches.append(http_patch)
                logger.debug(f"Injected HTTP 403 permission error: {error_message}")

            else:
                # 默认：使用密码验证失败
                logger.warning(f"Unknown permission_type '{permission_type}', using default 'password_verify'")
                permission_patch = patch("app.core.security.verify_password")
                mock_verify = permission_patch.start()
                mock_verify.return_value = False
                patches.append(permission_patch)

            yield

        finally:
            for p in patches:
                p.stop()
            logger.debug("Permission error injection cleaned up")

    @contextmanager
    def inject_network_error(self, error_type: str = "timeout", error_message: Optional[str] = None):
        """
        注入网络错误

        用于测试网络操作失败时的处理。

        Args:
            error_type: 错误类型，可选值：
                - "timeout": 超时错误
                - "connection": 连接错误
                - "dns": DNS解析错误
            error_message: 自定义错误消息

        Yields:
            None

        Example:
            >>> with injector.inject_network_error("timeout"):
            ...     result = email_service.send_email("test@example.com", "subject", "body")
            ...     assert result is False
        """
        if error_message is None:
            error_message = f"Network {error_type} error"

        try:
            if error_type == "timeout":
                exception = TimeoutError(error_message)
            elif error_type == "connection":
                exception = ConnectionError(error_message)
            elif error_type == "dns":
                exception = OSError(error_message)
            else:
                exception = Exception(error_message)

            # Mock 网络相关的操作
            network_patch = patch("httpx.AsyncClient.post")
            mock_post = network_patch.start()
            mock_post.side_effect = exception

            logger.debug(f"Injected network error ({error_type}): {error_message}")
            yield

        finally:
            network_patch.stop()
            logger.debug("Network error injection cleaned up")

    @contextmanager
    def inject_file_system_error(self, operation: str = "read", error_message: str = "File system operation failed"):
        """
        注入文件系统错误

        用于测试文件操作失败时的处理。

        Args:
            operation: 文件操作类型，可选值：
                - "read": 读取操作
                - "write": 写入操作
                - "delete": 删除操作
                - "exists": 存在性检查
            error_message: 错误消息

        Yields:
            None

        Example:
            >>> with injector.inject_file_system_error("write"):
            ...     result = file_service.save_file("test.txt", b"content")
            ...     assert result is False
        """
        patches = []

        try:
            if operation == "read":
                read_patch = patch("builtins.open")
                mock_open = read_patch.start()
                mock_open.side_effect = IOError(error_message)
                patches.append(read_patch)

            elif operation == "write":
                write_patch = patch("builtins.open")
                mock_open = write_patch.start()
                mock_open.side_effect = IOError(error_message)
                patches.append(write_patch)

            elif operation == "delete":
                delete_patch = patch("os.remove")
                mock_remove = delete_patch.start()
                mock_remove.side_effect = OSError(error_message)
                patches.append(delete_patch)

            elif operation == "exists":
                exists_patch = patch("os.path.exists")
                mock_exists = exists_patch.start()
                mock_exists.return_value = False
                patches.append(exists_patch)

            logger.debug(f"Injected file system error for {operation} operation: {error_message}")
            yield

        finally:
            for p in patches:
                p.stop()
            logger.debug("File system error injection cleaned up")

    @contextmanager
    def inject_encoding_error(self, error_message: str = "Encoding/decoding failed"):
        """
        注入编码/解码错误

        用于测试字符编码问题的处理。

        Args:
            error_message: 错误消息

        Yields:
            None

        Example:
            >>> with injector.inject_encoding_error():
            ...     result = process_text("invalid_utf8")
            ...     assert result is None
        """
        try:
            # Mock encode/decode 方法
            encode_patch = patch("builtins.str.encode")
            mock_encode = encode_patch.start()
            mock_encode.side_effect = UnicodeEncodeError("utf-8", "", 0, 1, error_message)

            logger.debug(f"Injected encoding error: {error_message}")
            yield

        finally:
            encode_patch.stop()
            logger.debug("Encoding error injection cleaned up")

    @contextmanager
    def inject_custom_error(self, target: str, exception: Exception, method: str = "side_effect"):
        """
        注入自定义错误

        提供灵活的方式注入任意异常到任意目标。

        Args:
            target: 要 mock 的目标（完整路径，如 'app.services.user_service.UserService.get_user_by_id'）
            exception: 要抛出的异常实例
            method: 注入方法，可选值：
                - "side_effect": 调用时抛出异常
                - "return_value": 返回异常对象（不抛出）

        Yields:
            None

        Example:
            >>> custom_error = ValueError("Custom error message")
            >>> with injector.inject_custom_error('app.services.user_service.UserService.get_user_by_id', custom_error):
            ...     result = user_service.get_user_by_id("test_id")
            ...     assert result is None
        """
        try:
            custom_patch = patch(target)
            mock_target = custom_patch.start()

            if method == "side_effect":
                mock_target.side_effect = exception
            elif method == "return_value":
                mock_target.return_value = exception
            else:
                raise ValueError(f"Unknown injection method: {method}")

            logger.debug(f"Injected custom error to {target}: {exception}")
            yield

        finally:
            custom_patch.stop()
            logger.debug(f"Custom error injection cleaned up for {target}")

    def restore_normal_behavior(self) -> None:
        """
        恢复正常行为

        停止所有活动的 patches，恢复原始行为。
        通常不需要手动调用，因为上下文管理器会自动清理。

        Example:
            >>> injector.restore_normal_behavior()
        """
        for name, patch_obj in self._active_patches.items():
            try:
                patch_obj.stop()
                logger.debug(f"Stopped patch: {name}")
            except Exception as e:
                logger.warning(f"Error stopping patch {name}: {e}")

        self._active_patches.clear()
        self._original_values.clear()
        logger.info("All patches stopped, normal behavior restored")

    @contextmanager
    def inject_multiple_errors(self, error_configs: list[Dict[str, Any]]):
        """
        同时注入多个错误

        用于测试复杂的错误场景，其中多个操作可能同时失败。

        Args:
            error_configs: 错误配置列表，每个配置是一个字典，包含：
                - type: 错误类型（database, validation, permission, network, file_system, encoding, custom）
                - **kwargs: 传递给相应注入方法的参数

        Yields:
            None

        Example:
            >>> configs = [
            ...     {"type": "database", "operation": "query"},
            ...     {"type": "network", "error_type": "timeout"}
            ... ]
            >>> with injector.inject_multiple_errors(configs):
            ...     # 测试代码
            ...     pass
        """
        contexts = []

        try:
            for config in error_configs:
                error_type = config.pop("type")

                if error_type == "database":
                    ctx = self.inject_database_error(**config)
                elif error_type == "validation":
                    ctx = self.inject_validation_error(**config)
                elif error_type == "permission":
                    ctx = self.inject_permission_error(**config)
                elif error_type == "network":
                    ctx = self.inject_network_error(**config)
                elif error_type == "file_system":
                    ctx = self.inject_file_system_error(**config)
                elif error_type == "encoding":
                    ctx = self.inject_encoding_error(**config)
                elif error_type == "custom":
                    ctx = self.inject_custom_error(**config)
                else:
                    raise ValueError(f"Unknown error type: {error_type}")

                contexts.append(ctx)
                ctx.__enter__()

            logger.debug(f"Injected {len(contexts)} errors simultaneously")
            yield

        finally:
            for ctx in reversed(contexts):
                try:
                    ctx.__exit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error cleaning up context: {e}")
            logger.debug("Multiple error injection cleaned up")

    def create_mock_with_error(self, error: Exception, call_count: int = 1) -> MagicMock:
        """
        创建一个会在指定次数后抛出错误的 mock

        用于测试重试逻辑或间歇性错误。

        Args:
            error: 要抛出的异常
            call_count: 在第几次调用时抛出异常（从1开始）

        Returns:
            MagicMock: 配置好的 mock 对象

        Example:
            >>> mock = injector.create_mock_with_error(ValueError("Error"), call_count=2)
            >>> mock()  # 第一次调用正常
            >>> mock()  # 第二次调用抛出异常
        """
        mock = MagicMock()

        def side_effect(*args, **kwargs):
            if mock.call_count >= call_count:
                raise error
            return None

        mock.side_effect = side_effect
        logger.debug(f"Created mock that will raise {error} on call {call_count}")
        return mock

    def create_intermittent_error_mock(
        self, error: Exception, success_count: int = 1, failure_count: int = 1
    ) -> MagicMock:
        """
        创建一个间歇性失败的 mock

        模拟不稳定的服务或网络连接。

        Args:
            error: 要抛出的异常
            success_count: 成功调用次数
            failure_count: 失败调用次数

        Returns:
            MagicMock: 配置好的 mock 对象

        Example:
            >>> mock = injector.create_intermittent_error_mock(
            ...     ConnectionError("Network error"),
            ...     success_count=2,
            ...     failure_count=1
            ... )
            >>> mock()  # 成功
            >>> mock()  # 成功
            >>> mock()  # 失败
            >>> mock()  # 成功
        """
        mock = MagicMock()
        call_counter = [0]

        def side_effect(*args, **kwargs):
            call_counter[0] += 1
            cycle_position = (call_counter[0] - 1) % (success_count + failure_count)

            if cycle_position >= success_count:
                raise error
            return None

        mock.side_effect = side_effect
        logger.debug(f"Created intermittent error mock: {success_count} success, {failure_count} failure")
        return mock


# 便捷函数，用于快速创建注入器实例
def create_injector() -> ExceptionInjector:
    """
    创建异常注入器实例

    Returns:
        ExceptionInjector: 新的注入器实例

    Example:
        >>> injector = create_injector()
        >>> with injector.inject_database_error("query"):
        ...     # 测试代码
        ...     pass
    """
    return ExceptionInjector()
