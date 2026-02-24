"""
WebSocket测试客户端连接管理单元测试

测试WebSocketTestClient的连接管理功能：
- 连接状态跟踪
- 连接超时处理
- 连接重试机制
- 连接健康检查
"""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from tests.helpers.websocket_client import ConnectionState, WebSocketTestClient


class TestConnectionState:
    """测试连接状态跟踪"""

    def test_initial_state_is_disconnected(self):
        """测试初始状态为已断开"""
        mock_client = Mock()
        client = WebSocketTestClient(mock_client, "test_token")

        assert client.get_connection_state() == ConnectionState.DISCONNECTED
        assert not client.is_connected()

    def test_state_changes_during_connection(self):
        """测试连接过程中状态变化"""
        mock_test_client = Mock()
        mock_ws = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_ws)
        mock_context.__exit__ = Mock(return_value=None)
        mock_test_client.websocket_connect = Mock(return_value=mock_context)

        client = WebSocketTestClient(mock_test_client, "test_token")

        # 连接前
        assert client.get_connection_state() == ConnectionState.DISCONNECTED

        # 连接中
        with client.connect() as _:
            assert client.get_connection_state() == ConnectionState.CONNECTED
            assert client.is_connected()

        # 连接后
        assert client.get_connection_state() == ConnectionState.DISCONNECTED
        assert not client.is_connected()

    def test_state_is_error_on_connection_failure(self):
        """测试连接失败时状态为错误"""
        mock_test_client = Mock()
        mock_test_client.websocket_connect.side_effect = Exception("Connection failed")

        client = WebSocketTestClient(mock_test_client, "test_token")

        with pytest.raises(Exception, match="Connection failed"):
            with client.connect():
                pass

        assert client.get_connection_state() == ConnectionState.DISCONNECTED
        assert not client.is_connected()


class TestConnectionTimeout:
    """测试连接超时处理"""

    def test_custom_timeout_configuration(self):
        """测试自定义超时配置"""
        mock_client = Mock()
        client = WebSocketTestClient(mock_client, "test_token", connection_timeout=10.0)

        health = client.check_connection_health()
        assert health["connection_timeout"] == 10.0

    def test_default_timeout_is_5_seconds(self):
        """测试默认超时为5秒"""
        mock_client = Mock()
        client = WebSocketTestClient(mock_client, "test_token")

        health = client.check_connection_health()
        assert health["connection_timeout"] == 5.0


class TestConnectionRetry:
    """测试连接重试机制"""

    def test_connect_with_retry_success_on_first_attempt(self):
        """测试首次尝试连接成功"""
        mock_test_client = Mock()
        mock_ws = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_ws)
        mock_test_client.websocket_connect = Mock(return_value=mock_context)

        client = WebSocketTestClient(mock_test_client, "test_token", max_retries=3)

        result = client.connect_with_retry()

        assert result is True
        assert client.is_connected()
        assert client.get_connection_state() == ConnectionState.CONNECTED
        health = client.check_connection_health()
        assert health["retry_count"] == 0

    def test_connect_with_retry_success_on_second_attempt(self):
        """测试第二次尝试连接成功"""
        mock_test_client = Mock()
        mock_ws = MagicMock()

        # 第一次失败，第二次成功
        mock_test_client.websocket_connect.side_effect = [
            Exception("First attempt failed"),
            MagicMock(__enter__=Mock(return_value=mock_ws)),
        ]

        client = WebSocketTestClient(mock_test_client, "test_token", max_retries=3)

        with patch("time.sleep"):  # 跳过等待时间
            result = client.connect_with_retry()

        assert result is True
        assert client.is_connected()

    def test_connect_with_retry_fails_after_max_retries(self):
        """测试达到最大重试次数后失败"""
        mock_test_client = Mock()
        mock_test_client.websocket_connect.side_effect = Exception("Connection failed")

        client = WebSocketTestClient(mock_test_client, "test_token", max_retries=3)

        with patch("time.sleep"):  # 跳过等待时间
            result = client.connect_with_retry()

        assert result is False
        assert not client.is_connected()
        assert client.get_connection_state() == ConnectionState.DISCONNECTED
        health = client.check_connection_health()
        assert health["retry_count"] == 3
        assert health["last_error"] is not None

    def test_retry_count_resets_on_successful_connection(self):
        """测试成功连接后重试计数重置"""
        mock_test_client = Mock()
        mock_ws = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_ws)
        mock_context.__exit__ = Mock(return_value=None)
        mock_test_client.websocket_connect = Mock(return_value=mock_context)

        client = WebSocketTestClient(mock_test_client, "test_token", max_retries=3)

        # 模拟之前有重试
        client._retry_count = 2

        with client.connect():
            pass

        health = client.check_connection_health()
        assert health["retry_count"] == 0

    def test_exponential_backoff_in_retry(self):
        """测试重试时的指数退避"""
        mock_test_client = Mock()
        mock_test_client.websocket_connect.side_effect = Exception("Connection failed")

        client = WebSocketTestClient(mock_test_client, "test_token", max_retries=3)

        with patch("time.sleep") as mock_sleep:
            client.connect_with_retry()

            # 验证等待时间：2^1=2, 2^2=4
            calls = mock_sleep.call_args_list
            assert len(calls) == 2  # 3次尝试，2次等待
            assert calls[0][0][0] == 2  # 第一次等待2秒
            assert calls[1][0][0] == 4  # 第二次等待4秒


class TestConnectionHealth:
    """测试连接健康检查"""

    def test_health_check_when_disconnected(self):
        """测试断开连接时的健康检查"""
        mock_client = Mock()
        client = WebSocketTestClient(mock_client, "test_token")

        health = client.check_connection_health()

        assert health["state"] == "disconnected"
        assert health["is_connected"] is False
        assert health["duration"] is None
        assert health["retry_count"] == 0
        assert health["last_error"] is None

    def test_health_check_when_connected(self):
        """测试已连接时的健康检查"""
        mock_test_client = Mock()
        mock_ws = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_ws)
        mock_context.__exit__ = Mock(return_value=None)
        mock_test_client.websocket_connect = Mock(return_value=mock_context)

        client = WebSocketTestClient(mock_test_client, "test_token")

        with client.connect():
            time.sleep(0.1)  # 等待一小段时间
            health = client.check_connection_health()

            assert health["state"] == "connected"
            assert health["is_connected"] is True
            assert health["duration"] is not None
            assert health["duration"] > 0

    def test_health_check_includes_error_info(self):
        """测试健康检查包含错误信息"""
        mock_test_client = Mock()
        mock_test_client.websocket_connect.side_effect = Exception("Test error")

        client = WebSocketTestClient(mock_test_client, "test_token", max_retries=2)

        with patch("time.sleep"):
            client.connect_with_retry()

        health = client.check_connection_health()

        assert health["last_error"] == "Test error"
        assert health["retry_count"] == 2

    def test_connection_duration_tracking(self):
        """测试连接持续时间跟踪"""
        mock_test_client = Mock()
        mock_ws = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_ws)
        mock_context.__exit__ = Mock(return_value=None)
        mock_test_client.websocket_connect = Mock(return_value=mock_context)

        client = WebSocketTestClient(mock_test_client, "test_token")

        with client.connect():
            # 连接后立即检查
            duration1 = client.get_connection_duration()
            assert duration1 is not None
            assert duration1 >= 0

            # 等待一段时间后再检查
            time.sleep(0.1)
            duration2 = client.get_connection_duration()
            assert duration2 > duration1

        # 断开后应该返回None
        assert client.get_connection_duration() is None


class TestConnectionStateReset:
    """测试连接状态重置"""

    def test_reset_clears_error_state(self):
        """测试重置清除错误状态"""
        mock_test_client = Mock()
        mock_test_client.websocket_connect.side_effect = Exception("Test error")

        client = WebSocketTestClient(mock_test_client, "test_token", max_retries=1)

        with patch("time.sleep"):
            client.connect_with_retry()

        # 验证有错误
        health = client.check_connection_health()
        assert health["last_error"] is not None
        assert health["retry_count"] == 1

        # 重置状态
        client.reset_connection_state()

        # 验证错误已清除
        health = client.check_connection_health()
        assert health["last_error"] is None
        assert health["retry_count"] == 0

    def test_reset_does_not_disconnect_active_connection(self):
        """测试重置不会断开活动连接"""
        mock_test_client = Mock()
        mock_ws = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_ws)
        mock_context.__exit__ = Mock(return_value=None)
        mock_test_client.websocket_connect = Mock(return_value=mock_context)

        client = WebSocketTestClient(mock_test_client, "test_token")

        with client.connect():
            # 在连接状态下重置
            client.reset_connection_state()

            # 应该仍然保持连接
            assert client.is_connected()
            assert client.get_connection_state() == ConnectionState.CONNECTED


class TestDisconnectWithStateTracking:
    """测试带状态跟踪的断开连接"""

    def test_disconnect_updates_state(self):
        """测试断开连接更新状态"""
        mock_test_client = Mock()
        mock_ws = MagicMock()

        client = WebSocketTestClient(mock_test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        client._connection_start_time = time.time()

        client.disconnect()

        assert client.get_connection_state() == ConnectionState.DISCONNECTED
        assert not client.is_connected()
        assert client.get_connection_duration() is None

    def test_disconnect_handles_errors_gracefully(self):
        """测试断开连接优雅处理错误"""
        mock_test_client = Mock()
        mock_ws = MagicMock()
        mock_ws.close.side_effect = Exception("Close error")

        client = WebSocketTestClient(mock_test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED

        # 不应该抛出异常
        client.disconnect()

        # 状态应该更新
        assert client.get_connection_state() == ConnectionState.DISCONNECTED
        assert client.websocket is None


class TestNetworkErrorSimulation:
    """测试网络错误模拟"""

    def test_simulate_network_error_sets_error_state(self):
        """测试模拟网络错误设置错误状态"""
        mock_test_client = Mock()
        mock_ws = MagicMock()

        client = WebSocketTestClient(mock_test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        client._connection_start_time = time.time()

        client.simulate_network_error()

        assert client.get_connection_state() == ConnectionState.ERROR
        assert not client.is_connected()
        assert client.websocket is None

    def test_simulate_network_error_uses_abnormal_closure_code(self):
        """测试模拟网络错误使用异常关闭代码"""
        mock_test_client = Mock()
        mock_ws = MagicMock()

        client = WebSocketTestClient(mock_test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED

        client.simulate_network_error()

        # 验证使用了1006代码（异常关闭）
        mock_ws.close.assert_called_once_with(code=1006)
