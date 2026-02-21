"""
WebSocket测试客户端消息收发功能单元测试

测试WebSocketTestClient的消息收发方法，包括：
- JSON消息收发
- 文本消息收发
- 二进制消息收发
- 消息超时处理
- 消息验证
- 消息历史和统计
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from tests.helpers.websocket_client import (
    WebSocketTestClient, 
    MessageType, 
    ConnectionState
)


class TestMessageReceiving:
    """测试消息接收功能"""
    
    def test_receive_json_message(self):
        """测试接收JSON消息"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_data = {"type": "test", "data": "hello"}
        mock_ws.receive_json.return_value = test_data
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.receive_message(message_type=MessageType.JSON)
        
        # 验证
        assert result == test_data
        assert len(client.get_received_messages()) == 1
        assert client.get_received_messages()[0]["type"] == "json"
        assert client.get_received_messages()[0]["data"] == test_data
    
    def test_receive_text_message(self):
        """测试接收文本消息"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_text = "Hello, WebSocket!"
        mock_ws.receive_text.return_value = test_text
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.receive_message(message_type=MessageType.TEXT)
        
        # 验证
        assert result == test_text
        assert len(client.get_received_messages()) == 1
        assert client.get_received_messages()[0]["type"] == "text"
    
    def test_receive_binary_message(self):
        """测试接收二进制消息"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_data = b"\x00\x01\x02\x03"
        mock_ws.receive_bytes.return_value = test_data
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.receive_message(message_type=MessageType.BINARY)
        
        # 验证
        assert result == test_data
        assert len(client.get_received_messages()) == 1
        assert client.get_received_messages()[0]["type"] == "binary"
    
    def test_receive_message_timeout(self):
        """测试消息接收超时"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        mock_ws.receive_json.side_effect = TimeoutError("Timeout")
        
        client = WebSocketTestClient(test_client, "test_token", message_timeout=1.0)
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.receive_message(timeout=0.5)
        
        # 验证
        assert result is None
    
    def test_receive_message_without_connection(self):
        """测试未连接时接收消息"""
        # 准备
        test_client = Mock()
        client = WebSocketTestClient(test_client, "test_token")
        
        # 执行和验证
        with pytest.raises(RuntimeError, match="WebSocket connection not established"):
            client.receive_message()
    
    def test_receive_message_invalid_json(self):
        """测试接收无效JSON消息"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        mock_ws.receive_json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行和验证
        with pytest.raises(ValueError, match="Invalid JSON message"):
            client.receive_message(message_type=MessageType.JSON)
    
    def test_receive_message_with_validation_success(self):
        """测试带验证的消息接收（成功）"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_data = {"type": "test", "data": "hello", "timestamp": 123456}
        mock_ws.receive_json.return_value = test_data
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.receive_message_with_validation(["type", "data"])
        
        # 验证
        assert result == test_data
    
    def test_receive_message_with_validation_missing_fields(self):
        """测试带验证的消息接收（缺少字段）"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_data = {"type": "test"}  # 缺少 "data" 字段
        mock_ws.receive_json.return_value = test_data
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.receive_message_with_validation(["type", "data"])
        
        # 验证
        assert result is None
    
    def test_receive_message_with_validation_timeout(self):
        """测试带验证的消息接收（超时）"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        mock_ws.receive_json.side_effect = TimeoutError("Timeout")
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.receive_message_with_validation(["type"], timeout=0.5)
        
        # 验证
        assert result is None
    
    def test_try_receive_message_with_message(self):
        """测试非阻塞接收（有消息）"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_data = {"type": "test"}
        mock_ws.receive_json.return_value = test_data
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.try_receive_message()
        
        # 验证
        assert result == test_data
    
    def test_try_receive_message_no_message(self):
        """测试非阻塞接收（无消息）"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        mock_ws.receive_json.side_effect = TimeoutError("Timeout")
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.try_receive_message()
        
        # 验证
        assert result is None


class TestMessageSending:
    """测试消息发送功能"""
    
    def test_send_json_message_dict(self):
        """测试发送JSON消息（字典）"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_data = {"type": "test", "data": "hello"}
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.send_message(test_data)
        
        # 验证
        assert result is True
        mock_ws.send_json.assert_called_once_with(test_data)
        assert len(client.get_sent_messages()) == 1
        assert client.get_sent_messages()[0]["type"] == "json"
    
    def test_send_text_message(self):
        """测试发送文本消息"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_text = "Hello, WebSocket!"
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.send_message(test_text)
        
        # 验证
        assert result is True
        mock_ws.send_text.assert_called_once_with(test_text)
        assert len(client.get_sent_messages()) == 1
        assert client.get_sent_messages()[0]["type"] == "text"
    
    def test_send_binary_message(self):
        """测试发送二进制消息"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_data = b"\x00\x01\x02\x03"
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.send_message(test_data)
        
        # 验证
        assert result is True
        mock_ws.send_bytes.assert_called_once_with(test_data)
        assert len(client.get_sent_messages()) == 1
        assert client.get_sent_messages()[0]["type"] == "binary"
    
    def test_send_message_without_connection(self):
        """测试未连接时发送消息"""
        # 准备
        test_client = Mock()
        client = WebSocketTestClient(test_client, "test_token")
        
        # 执行和验证
        with pytest.raises(RuntimeError, match="WebSocket connection not established"):
            client.send_message("test")
    
    def test_send_message_with_explicit_type(self):
        """测试使用显式消息类型发送"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行 - 发送文本但指定为JSON
        result = client.send_message('{"type": "test"}', message_type=MessageType.JSON)
        
        # 验证
        assert result is True
        mock_ws.send_json.assert_called_once()
    
    def test_send_json_message_convenience(self):
        """测试便捷JSON发送方法"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_data = {"type": "ping"}
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.send_json_message(test_data)
        
        # 验证
        assert result is True
        mock_ws.send_json.assert_called_once_with(test_data)
    
    def test_send_text_message_convenience(self):
        """测试便捷文本发送方法"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.send_text_message("Hello")
        
        # 验证
        assert result is True
        mock_ws.send_text.assert_called_once_with("Hello")
    
    def test_send_binary_message_convenience(self):
        """测试便捷二进制发送方法"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_data = b"\x00\x01"
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.send_binary_message(test_data)
        
        # 验证
        assert result is True
        mock_ws.send_bytes.assert_called_once_with(test_data)
    
    def test_send_message_error_handling(self):
        """测试发送消息错误处理"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        mock_ws.send_text.side_effect = Exception("Send failed")
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.send_message("test")
        
        # 验证
        assert result is False


class TestMessageHistory:
    """测试消息历史功能"""
    
    def test_get_sent_messages(self):
        """测试获取发送消息历史"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行 - 发送多条消息
        client.send_message("text1")
        client.send_message({"type": "json"})
        client.send_message(b"binary")
        
        # 验证
        sent = client.get_sent_messages()
        assert len(sent) == 3
        assert sent[0]["type"] == "text"
        assert sent[1]["type"] == "json"
        assert sent[2]["type"] == "binary"
    
    def test_get_received_messages(self):
        """测试获取接收消息历史"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        mock_ws.receive_json.side_effect = [
            {"msg": 1},
            {"msg": 2},
            {"msg": 3}
        ]
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行 - 接收多条消息
        client.receive_message()
        client.receive_message()
        client.receive_message()
        
        # 验证
        received = client.get_received_messages()
        assert len(received) == 3
        assert all(msg["type"] == "json" for msg in received)
    
    def test_clear_message_history(self):
        """测试清除消息历史"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        mock_ws.receive_json.return_value = {"test": "data"}
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行 - 发送和接收消息
        client.send_message("test")
        client.receive_message()
        
        assert len(client.get_sent_messages()) == 1
        assert len(client.get_received_messages()) == 1
        
        # 清除历史
        client.clear_message_history()
        
        # 验证
        assert len(client.get_sent_messages()) == 0
        assert len(client.get_received_messages()) == 0
    
    def test_get_message_statistics(self):
        """测试获取消息统计"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        mock_ws.receive_json.side_effect = [{"msg": 1}, {"msg": 2}]
        mock_ws.receive_text.return_value = "text"
        
        client = WebSocketTestClient(test_client, "test_token", message_timeout=3.0)
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行 - 发送和接收不同类型的消息
        client.send_message("text1")
        client.send_message("text2")
        client.send_message({"json": "data"})
        client.receive_message(message_type=MessageType.JSON)
        client.receive_message(message_type=MessageType.JSON)
        client.receive_message(message_type=MessageType.TEXT)
        
        # 验证
        stats = client.get_message_statistics()
        assert stats["sent_count"] == 3
        assert stats["received_count"] == 3
        assert stats["sent_by_type"]["text"] == 2
        assert stats["sent_by_type"]["json"] == 1
        assert stats["received_by_type"]["json"] == 2
        assert stats["received_by_type"]["text"] == 1
        assert stats["message_timeout"] == 3.0
        assert stats["queue_enabled"] is False
    
    def test_message_history_immutability(self):
        """测试消息历史的不可变性"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        client.send_message("test")
        sent1 = client.get_sent_messages()
        sent1.append({"fake": "message"})
        sent2 = client.get_sent_messages()
        
        # 验证 - 修改返回的列表不应影响内部状态
        assert len(sent2) == 1
        assert "fake" not in str(sent2)


class TestMessageQueue:
    """测试消息队列功能"""
    
    def test_message_queue_disabled_by_default(self):
        """测试消息队列默认禁用"""
        # 准备
        test_client = Mock()
        client = WebSocketTestClient(test_client, "test_token")
        
        # 验证
        stats = client.get_message_statistics()
        assert stats["queue_enabled"] is False
    
    def test_message_queue_enabled(self):
        """测试启用消息队列"""
        # 准备
        test_client = Mock()
        client = WebSocketTestClient(test_client, "test_token", enable_message_queue=True)
        
        # 验证
        stats = client.get_message_statistics()
        assert stats["queue_enabled"] is True


class TestMessageTimeout:
    """测试消息超时功能"""
    
    def test_default_message_timeout(self):
        """测试默认消息超时"""
        # 准备
        test_client = Mock()
        client = WebSocketTestClient(test_client, "test_token")
        
        # 验证
        stats = client.get_message_statistics()
        assert stats["message_timeout"] == 5.0
    
    def test_custom_message_timeout(self):
        """测试自定义消息超时"""
        # 准备
        test_client = Mock()
        client = WebSocketTestClient(test_client, "test_token", message_timeout=10.0)
        
        # 验证
        stats = client.get_message_statistics()
        assert stats["message_timeout"] == 10.0
    
    def test_receive_with_custom_timeout(self):
        """测试使用自定义超时接收消息"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_data = {"test": "data"}
        mock_ws.receive_json.return_value = test_data
        
        client = WebSocketTestClient(test_client, "test_token", message_timeout=5.0)
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行 - 使用自定义超时
        result = client.receive_message(timeout=2.0)
        
        # 验证
        assert result == test_data
        # Note: The current implementation doesn't pass timeout to receive_json
        # This is a known limitation - timeout is handled at a higher level
        mock_ws.receive_json.assert_called_once()


class TestEdgeCases:
    """测试边界情况"""
    
    def test_send_empty_string(self):
        """测试发送空字符串"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.send_message("")
        
        # 验证
        assert result is True
        mock_ws.send_text.assert_called_once_with("")
    
    def test_send_empty_dict(self):
        """测试发送空字典"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.send_message({})
        
        # 验证
        assert result is True
        mock_ws.send_json.assert_called_once_with({})
    
    def test_send_empty_bytes(self):
        """测试发送空字节"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.send_message(b"")
        
        # 验证
        assert result is True
        mock_ws.send_bytes.assert_called_once_with(b"")
    
    def test_receive_validation_with_empty_fields_list(self):
        """测试使用空字段列表验证"""
        # 准备
        test_client = Mock()
        mock_ws = Mock()
        test_data = {"any": "data"}
        mock_ws.receive_json.return_value = test_data
        
        client = WebSocketTestClient(test_client, "test_token")
        client.websocket = mock_ws
        client._state = ConnectionState.CONNECTED
        
        # 执行
        result = client.receive_message_with_validation([])
        
        # 验证 - 空字段列表应该总是通过验证
        assert result == test_data
