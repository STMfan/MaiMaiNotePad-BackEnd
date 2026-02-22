"""
WebSocket测试客户端集成测试

验证WebSocketTestClient与实际WebSocket端点的集成。
"""

import pytest

# Mark all tests in this file as serial to avoid WebSocket connection conflicts
pytestmark = pytest.mark.serial
from tests.helpers.websocket_client import WebSocketTestClient  # noqa: E402
from app.core.security import create_access_token  # noqa: E402


def test_websocket_client_with_valid_token(client, test_user):
    """测试使用有效token建立WebSocket连接"""
    # 创建有效的JWT token
    token = create_access_token({"sub": test_user.id})

    # 创建WebSocket测试客户端
    ws_client = WebSocketTestClient(client, token)

    # 建立连接并接收初始消息
    with ws_client.connect() as _:
        # 应该能够接收到初始的消息更新
        message = ws_client.receive_message()

        # 验证消息格式
        assert "type" in message
        assert message["type"] == "message_update"
        assert "unread" in message


def test_websocket_client_send_message(client, test_user):
    """测试通过WebSocket客户端发送消息"""
    token = create_access_token({"sub": test_user.id})
    ws_client = WebSocketTestClient(client, token)

    with ws_client.connect() as ws:
        # 接收初始消息
        initial_message = ws_client.receive_message()
        assert initial_message["type"] == "message_update"

        # 发送测试消息（保持连接活跃）
        ws_client.send_message("ping")

        # 连接应该保持活跃
        assert ws is not None


def test_websocket_client_disconnect(client, test_user):
    """测试主动断开WebSocket连接"""
    token = create_access_token({"sub": test_user.id})
    ws_client = WebSocketTestClient(client, token)

    with ws_client.connect() as _:
        # 接收初始消息
        message = ws_client.receive_message()
        assert message["type"] == "message_update"

        # 主动断开连接
        ws_client.disconnect()

        # 验证连接已断开
        assert ws_client.websocket is None
