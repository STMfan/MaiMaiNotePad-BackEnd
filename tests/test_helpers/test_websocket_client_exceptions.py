"""
WebSocket测试客户端异常模拟功能的单元测试

测试WebSocketTestClient类的各种异常模拟方法。
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from tests.helpers.websocket_client import (
    WebSocketTestClient,
    ConnectionState,
    MessageType
)
from fastapi.testclient import TestClient


class TestWebSocketExceptionSimulation:
    """测试WebSocket异常模拟功能"""
    
    @pytest.fixture
    def mock_test_client(self):
        """创建模拟的TestClient"""
        return Mock(spec=TestClient)
    
    @pytest.fixture
    def ws_client(self, mock_test_client):
        """创建WebSocket测试客户端"""
        return WebSocketTestClient(mock_test_client, "test_token")
    
    def test_simulate_connection_timeout_success(self, ws_client, mock_test_client):
        """测试成功模拟连接超时"""
        # 模拟连接失败
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = TimeoutError("Connection timeout")
        mock_test_client.websocket_connect.return_value = mock_context
        
        # 执行超时模拟
        result = ws_client.simulate_connection_timeout(timeout=0.1)
        
        # 验证
        assert result is True  # 成功模拟超时
        assert ws_client.get_connection_state() == ConnectionState.ERROR
        assert ws_client._last_error is not None
    
    def test_simulate_connection_timeout_no_timeout(self, ws_client, mock_test_client):
        """测试连接成功时超时模拟返回False"""
        # 模拟连接成功
        mock_ws = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_ws
        mock_test_client.websocket_connect.return_value = mock_context
        
        # 执行超时模拟
        result = ws_client.simulate_connection_timeout(timeout=0.1)
        
        # 验证：连接成功，没有超时
        assert result is False
        assert ws_client.get_connection_state() == ConnectionState.CONNECTED
    
    def test_simulate_send_failure_network_error(self, ws_client):
        """测试模拟网络错误导致的发送失败"""
        # 设置连接状态
        ws_client.websocket = Mock()
        ws_client._state = ConnectionState.CONNECTED
        
        # 执行发送失败模拟
        with pytest.raises(ConnectionError, match="Network connection lost"):
            ws_client.simulate_send_failure("network")
        
        # 验证连接已关闭
        assert ws_client.websocket is None
        assert ws_client.get_connection_state() == ConnectionState.ERROR
    
    def test_simulate_send_failure_encoding_error(self, ws_client):
        """测试模拟编码错误导致的发送失败"""
        # 设置连接状态
        ws_client.websocket = Mock()
        ws_client._state = ConnectionState.CONNECTED
        
        # 执行发送失败模拟
        with pytest.raises(ValueError, match="Failed to encode message"):
            ws_client.simulate_send_failure("encoding")
    
    def test_simulate_send_failure_timeout(self, ws_client):
        """测试模拟超时导致的发送失败"""
        # 设置连接状态
        ws_client.websocket = Mock()
        ws_client._state = ConnectionState.CONNECTED
        
        # 执行发送失败模拟
        with pytest.raises(TimeoutError, match="Message send timeout"):
            ws_client.simulate_send_failure("timeout")
    
    def test_simulate_send_failure_no_connection(self, ws_client):
        """测试未连接时模拟发送失败抛出异常"""
        # 未建立连接
        ws_client.websocket = None
        
        # 执行发送失败模拟
        with pytest.raises(RuntimeError, match="WebSocket connection not established"):
            ws_client.simulate_send_failure("network")
    
    def test_simulate_send_failure_invalid_type(self, ws_client):
        """测试无效的错误类型"""
        # 设置连接状态
        ws_client.websocket = Mock()
        ws_client._state = ConnectionState.CONNECTED
        
        # 执行发送失败模拟
        with pytest.raises(ValueError, match="Unknown error type"):
            ws_client.simulate_send_failure("invalid_type")
    
    def test_simulate_receive_failure_timeout(self, ws_client):
        """测试模拟接收超时"""
        # 设置连接状态
        ws_client.websocket = Mock()
        ws_client._state = ConnectionState.CONNECTED
        
        # 执行接收失败模拟
        with pytest.raises(TimeoutError, match="Message receive timeout"):
            ws_client.simulate_receive_failure("timeout")
    
    def test_simulate_receive_failure_network_error(self, ws_client):
        """测试模拟网络错误导致的接收失败"""
        # 设置连接状态
        ws_client.websocket = Mock()
        ws_client._state = ConnectionState.CONNECTED
        
        # 执行接收失败模拟
        with pytest.raises(ConnectionError, match="Network connection lost during receive"):
            ws_client.simulate_receive_failure("network")
        
        # 验证连接已关闭
        assert ws_client.websocket is None
        assert ws_client.get_connection_state() == ConnectionState.ERROR
    
    def test_simulate_receive_failure_decode_error(self, ws_client):
        """测试模拟解码错误"""
        # 设置连接状态
        ws_client.websocket = Mock()
        ws_client._state = ConnectionState.CONNECTED
        
        # 执行接收失败模拟
        with pytest.raises(Exception):  # JSONDecodeError
            ws_client.simulate_receive_failure("decode")
    
    def test_simulate_receive_failure_empty_message(self, ws_client):
        """测试模拟空消息错误"""
        # 设置连接状态
        ws_client.websocket = Mock()
        ws_client._state = ConnectionState.CONNECTED
        
        # 执行接收失败模拟
        with pytest.raises(ValueError, match="Received empty message"):
            ws_client.simulate_receive_failure("empty")
    
    def test_simulate_receive_failure_no_connection(self, ws_client):
        """测试未连接时模拟接收失败抛出异常"""
        # 未建立连接
        ws_client.websocket = None
        
        # 执行接收失败模拟
        with pytest.raises(RuntimeError, match="WebSocket connection not established"):
            ws_client.simulate_receive_failure("timeout")
    
    def test_simulate_receive_failure_invalid_type(self, ws_client):
        """测试无效的错误类型"""
        # 设置连接状态
        ws_client.websocket = Mock()
        ws_client._state = ConnectionState.CONNECTED
        
        # 执行接收失败模拟
        with pytest.raises(ValueError, match="Unknown error type"):
            ws_client.simulate_receive_failure("invalid_type")
    
    def test_simulate_auth_failure_invalid_token(self, ws_client, mock_test_client):
        """测试模拟无效token认证失败"""
        # 模拟连接失败
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = Exception("Invalid token")
        mock_test_client.websocket_connect.return_value = mock_context
        
        # 执行认证失败模拟
        result = ws_client.simulate_auth_failure("invalid_token")
        
        # 验证
        assert result["success"] is True
        assert result["error_type"] == "invalid_token"
        assert result["error_message"] is not None
        assert ws_client.get_connection_state() == ConnectionState.DISCONNECTED
    
    def test_simulate_auth_failure_expired_token(self, ws_client, mock_test_client):
        """测试模拟过期token认证失败"""
        # 模拟连接失败
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = Exception("Token expired")
        mock_test_client.websocket_connect.return_value = mock_context
        
        # 执行认证失败模拟
        result = ws_client.simulate_auth_failure("expired_token")
        
        # 验证
        assert result["success"] is True
        assert result["error_type"] == "expired_token"
    
    def test_simulate_auth_failure_no_user_id(self, ws_client, mock_test_client):
        """测试模拟缺少user_id的token认证失败"""
        # 模拟连接失败，返回1008关闭代码
        error = Exception("Missing user_id - 1008")
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = error
        mock_test_client.websocket_connect.return_value = mock_context
        
        # 执行认证失败模拟
        result = ws_client.simulate_auth_failure("no_user_id")
        
        # 验证
        assert result["success"] is True
        assert result["error_type"] == "no_user_id"
        assert result["close_code"] == 1008 or "1008" in result["error_message"]
    
    def test_simulate_auth_failure_malformed_token(self, ws_client, mock_test_client):
        """测试模拟格式错误的token认证失败"""
        # 模拟连接失败
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = Exception("Malformed token")
        mock_test_client.websocket_connect.return_value = mock_context
        
        # 执行认证失败模拟
        result = ws_client.simulate_auth_failure("malformed")
        
        # 验证
        assert result["success"] is True
        assert result["error_type"] == "malformed"
    
    def test_simulate_auth_failure_unexpected_success(self, ws_client, mock_test_client):
        """测试认证意外成功的情况"""
        # 模拟连接成功
        mock_ws = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_ws
        mock_context.__exit__.return_value = None
        mock_test_client.websocket_connect.return_value = mock_context
        
        # 执行认证失败模拟
        result = ws_client.simulate_auth_failure("invalid_token")
        
        # 验证：认证成功，模拟失败
        assert result["success"] is False
        assert "succeeded unexpectedly" in result["error_message"]
    
    def test_simulate_auth_failure_invalid_type(self, ws_client):
        """测试无效的失败类型"""
        # 执行认证失败模拟
        with pytest.raises(ValueError, match="Unknown failure type"):
            ws_client.simulate_auth_failure("invalid_type")
    
    def test_simulate_auth_failure_restores_token(self, ws_client, mock_test_client):
        """测试认证失败模拟后恢复原始token"""
        # 保存原始token
        original_token = ws_client.token
        original_url = ws_client._url
        
        # 模拟连接失败
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = Exception("Auth failed")
        mock_test_client.websocket_connect.return_value = mock_context
        
        # 执行认证失败模拟
        ws_client.simulate_auth_failure("invalid_token")
        
        # 验证token已恢复
        assert ws_client.token == original_token
        assert ws_client._url == original_url
    
    def test_simulate_server_close_normal(self, ws_client):
        """测试模拟正常服务器关闭"""
        # 设置连接状态
        mock_ws = Mock()
        ws_client.websocket = mock_ws
        ws_client._state = ConnectionState.CONNECTED
        
        # 执行服务器关闭模拟
        ws_client.simulate_server_close(1000, "Normal closure")
        
        # 验证
        mock_ws.close.assert_called_once_with(code=1000, reason="Normal closure")
        assert ws_client.websocket is None
        assert ws_client.get_connection_state() == ConnectionState.DISCONNECTED
    
    def test_simulate_server_close_policy_violation(self, ws_client):
        """测试模拟策略违规关闭"""
        # 设置连接状态
        mock_ws = Mock()
        ws_client.websocket = mock_ws
        ws_client._state = ConnectionState.CONNECTED
        
        # 执行服务器关闭模拟
        ws_client.simulate_server_close(1008, "Policy violation")
        
        # 验证
        mock_ws.close.assert_called_once_with(code=1008, reason="Policy violation")
        assert ws_client.get_connection_state() == ConnectionState.DISCONNECTED
    
    def test_simulate_server_close_no_connection(self, ws_client):
        """测试未连接时模拟服务器关闭抛出异常"""
        # 未建立连接
        ws_client.websocket = None
        
        # 执行服务器关闭模拟
        with pytest.raises(RuntimeError, match="WebSocket connection not established"):
            ws_client.simulate_server_close(1000, "Normal closure")
    
    def test_simulate_server_close_with_error(self, ws_client):
        """测试关闭时发生错误的情况"""
        # 设置连接状态
        mock_ws = Mock()
        mock_ws.close.side_effect = Exception("Close error")
        ws_client.websocket = mock_ws
        ws_client._state = ConnectionState.CONNECTED
        
        # 执行服务器关闭模拟（不应抛出异常）
        ws_client.simulate_server_close(1000, "Normal closure")
        
        # 验证连接仍被清理
        assert ws_client.websocket is None
        assert ws_client.get_connection_state() == ConnectionState.DISCONNECTED
    
    def test_simulate_intermittent_connection_success(self, ws_client, mock_test_client):
        """测试成功模拟间歇性连接"""
        # 模拟连接成功
        mock_ws = Mock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_ws
        mock_context.__exit__.return_value = None
        mock_test_client.websocket_connect.return_value = mock_context
        
        # 执行间歇性连接模拟
        result = ws_client.simulate_intermittent_connection(
            disconnect_after=0.1,
            reconnect_delay=0.1
        )
        
        # 验证
        assert result["initial_connected"] is True
        assert result["disconnected"] is True
        assert result["total_duration"] > 0
    
    def test_simulate_intermittent_connection_initial_failure(self, ws_client, mock_test_client):
        """测试初始连接失败的间歇性连接"""
        # 模拟连接失败
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = Exception("Connection failed")
        mock_test_client.websocket_connect.return_value = mock_context
        
        # 执行间歇性连接模拟
        result = ws_client.simulate_intermittent_connection(
            disconnect_after=0.1,
            reconnect_delay=0.1
        )
        
        # 验证
        assert result["initial_connected"] is False
        assert result["total_duration"] > 0
    
    def test_get_exception_simulation_capabilities(self, ws_client):
        """测试获取异常模拟能力"""
        capabilities = ws_client.get_exception_simulation_capabilities()
        
        # 验证返回的能力列表
        assert "connection_timeout" in capabilities
        assert "send_failure" in capabilities
        assert "receive_failure" in capabilities
        assert "auth_failure" in capabilities
        assert "server_close" in capabilities
        assert "intermittent_connection" in capabilities
        
        # 验证具体的错误类型
        assert "network" in capabilities["send_failure"]
        assert "encoding" in capabilities["send_failure"]
        assert "timeout" in capabilities["send_failure"]
        
        assert "timeout" in capabilities["receive_failure"]
        assert "network" in capabilities["receive_failure"]
        assert "decode" in capabilities["receive_failure"]
        assert "empty" in capabilities["receive_failure"]
        
        assert "invalid_token" in capabilities["auth_failure"]
        assert "expired_token" in capabilities["auth_failure"]
        assert "no_user_id" in capabilities["auth_failure"]
        assert "malformed" in capabilities["auth_failure"]
    
    def test_exception_simulation_state_consistency(self, ws_client):
        """测试异常模拟后状态一致性"""
        # 设置连接状态
        mock_ws = Mock()
        ws_client.websocket = mock_ws
        ws_client._state = ConnectionState.CONNECTED
        
        # 模拟网络错误
        with pytest.raises(ConnectionError):
            ws_client.simulate_send_failure("network")
        
        # 验证状态一致性
        assert ws_client.websocket is None
        assert ws_client.get_connection_state() == ConnectionState.ERROR
        assert not ws_client.is_connected()
    
    def test_multiple_exception_simulations(self, ws_client, mock_test_client):
        """测试连续多次异常模拟"""
        # 第一次：模拟认证失败
        mock_context1 = MagicMock()
        mock_context1.__enter__.side_effect = Exception("Auth failed")
        mock_test_client.websocket_connect.return_value = mock_context1
        result1 = ws_client.simulate_auth_failure("invalid_token")
        assert result1["success"] is True
        
        # 第二次：模拟连接超时
        mock_context2 = MagicMock()
        mock_context2.__enter__.side_effect = TimeoutError("Timeout")
        mock_test_client.websocket_connect.return_value = mock_context2
        result2 = ws_client.simulate_connection_timeout(0.1)
        assert result2 is True
        
        # 验证状态已重置
        assert ws_client.get_connection_state() == ConnectionState.ERROR


class TestWebSocketExceptionSimulationEdgeCases:
    """测试异常模拟的边界情况"""
    
    @pytest.fixture
    def mock_test_client(self):
        """创建模拟的TestClient"""
        return Mock(spec=TestClient)
    
    @pytest.fixture
    def ws_client(self, mock_test_client):
        """创建WebSocket测试客户端"""
        return WebSocketTestClient(mock_test_client, "test_token")
    
    def test_simulate_send_failure_all_types(self, ws_client):
        """测试所有类型的发送失败模拟"""
        error_types = ["network", "encoding", "timeout"]
        
        for error_type in error_types:
            # 重新设置连接状态
            ws_client.websocket = Mock()
            ws_client._state = ConnectionState.CONNECTED
            
            # 执行模拟
            with pytest.raises(Exception):
                ws_client.simulate_send_failure(error_type)
    
    def test_simulate_receive_failure_all_types(self, ws_client):
        """测试所有类型的接收失败模拟"""
        error_types = ["timeout", "network", "decode", "empty"]
        
        for error_type in error_types:
            # 重新设置连接状态
            ws_client.websocket = Mock()
            ws_client._state = ConnectionState.CONNECTED
            
            # 执行模拟
            with pytest.raises(Exception):
                ws_client.simulate_receive_failure(error_type)
    
    def test_simulate_auth_failure_all_types(self, ws_client, mock_test_client):
        """测试所有类型的认证失败模拟"""
        failure_types = ["invalid_token", "expired_token", "no_user_id", "malformed"]
        
        for failure_type in failure_types:
            # 模拟连接失败
            mock_context = MagicMock()
            mock_context.__enter__.side_effect = Exception(f"{failure_type} error")
            mock_test_client.websocket_connect.return_value = mock_context
            
            # 执行模拟
            result = ws_client.simulate_auth_failure(failure_type)
            
            # 验证
            assert result["success"] is True
            assert result["error_type"] == failure_type
    
    def test_simulate_server_close_various_codes(self, ws_client):
        """测试各种关闭代码的服务器关闭模拟"""
        close_codes = [1000, 1001, 1002, 1003, 1006, 1008, 1011]
        
        for code in close_codes:
            # 重新设置连接状态
            mock_ws = Mock()
            ws_client.websocket = mock_ws
            ws_client._state = ConnectionState.CONNECTED
            
            # 执行模拟
            ws_client.simulate_server_close(code, f"Close code {code}")
            
            # 验证
            mock_ws.close.assert_called_with(code=code, reason=f"Close code {code}")
            assert ws_client.get_connection_state() == ConnectionState.DISCONNECTED
