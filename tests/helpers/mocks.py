"""
Mock 辅助函数
提供常用的 Mock 对象和上下文管理器
"""

from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch


class MockHelpers:
    """Mock 辅助函数集合"""

    @staticmethod
    @contextmanager
    def mock_email_service():
        """Mock 邮件服务"""
        with patch("app.services.email_service.EmailService.send_email") as mock:
            mock.return_value = True
            yield mock

    @staticmethod
    @contextmanager
    def mock_file_system():
        """Mock 文件系统操作"""
        with (
            patch("os.path.exists") as mock_exists,
            patch("os.makedirs") as mock_makedirs,
            patch("shutil.rmtree") as mock_rmtree,
        ):

            mock_exists.return_value = True
            yield {"exists": mock_exists, "makedirs": mock_makedirs, "rmtree": mock_rmtree}

    @staticmethod
    @contextmanager
    def mock_datetime_now(fixed_datetime):
        """Mock datetime.now() 返回固定时间"""
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            yield mock_datetime

    @staticmethod
    def create_mock_user(user_id: str = "test_user_id", username: str = "testuser", **kwargs):
        """创建 Mock 用户对象"""
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.username = username
        mock_user.email = kwargs.get("email", f"{username}@example.com")
        mock_user.is_active = kwargs.get("is_active", True)
        mock_user.is_admin = kwargs.get("is_admin", False)
        mock_user.is_moderator = kwargs.get("is_moderator", False)
        return mock_user

    @staticmethod
    def create_mock_db_session():
        """创建 Mock 数据库会话"""
        mock_session = MagicMock()
        mock_session.query.return_value = mock_session
        mock_session.filter.return_value = mock_session
        mock_session.first.return_value = None
        mock_session.all.return_value = []
        return mock_session
