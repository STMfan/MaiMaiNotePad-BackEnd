"""
测试WebSocket测试客户端辅助类

验证WebSocketTestClient类的基本功能。
"""

import pytest
from tests.helpers.websocket_client import WebSocketTestClient
from fastapi.testclient import TestClient


def test_websocket_client_initialization(client):
    """测试WebSocket客户端初始化"""
    token = "test_token_123"
    ws_client = WebSocketTestClient(client, token)

    assert ws_client.test_client == client
    assert ws_client.token == token
    assert ws_client.websocket is None
    assert ws_client._url == f"/api/ws/{token}"


def test_websocket_client_receive_without_connection():
    """测试在未建立连接时接收消息应该抛出异常"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    ws_client = WebSocketTestClient(client, "test_token")

    with pytest.raises(RuntimeError, match="WebSocket connection not established"):
        ws_client.receive_message()


def test_websocket_client_send_without_connection():
    """测试在未建立连接时发送消息应该抛出异常"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    ws_client = WebSocketTestClient(client, "test_token")

    with pytest.raises(RuntimeError, match="WebSocket connection not established"):
        ws_client.send_message("test")
