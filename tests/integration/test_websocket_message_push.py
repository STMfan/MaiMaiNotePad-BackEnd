"""
WebSocket初始消息推送测试

测试 app/api/websocket.py 中的初始消息推送功能。
覆盖连接建立后的消息推送逻辑（第46-55行）。
"""

import pytest

# Mark all tests in this file as serial to avoid WebSocket connection conflicts
pytestmark = pytest.mark.serial
from unittest.mock import patch, AsyncMock  # noqa: E402
from tests.helpers.websocket_client import WebSocketTestClient  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.utils.websocket import message_ws_manager  # noqa: E402


class TestWebSocketInitialMessagePush:
    """测试WebSocket连接建立后的初始消息推送"""

    def test_initial_message_push_on_connection(self, client, test_user):
        """
        测试连接建立后立即推送初始消息

        验证：
        - WebSocket连接建立后，服务器立即推送初始消息
        - 消息包含type字段，值为"message_update"
        - 消息包含unread字段，表示未读消息数
        - 如果有最新消息，包含last_message字段

        覆盖代码：websocket.py 第47-50行
        - 第47行：await message_ws_manager.connect(str(user_id), websocket)
        - 第50行：await message_ws_manager.send_message_update(str(user_id))
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 验证连接成功
            assert ws is not None
            assert ws_client.is_connected()

            # 接收初始消息
            message = ws_client.receive_message()

            # 验证消息不为空
            assert message is not None, "应该接收到初始消息"

            # 验证消息包含必需字段
            assert "type" in message, "消息应该包含type字段"
            assert "unread" in message, "消息应该包含unread字段"

            # 验证消息类型正确
            assert message["type"] == "message_update", "消息类型应该是message_update"

            # 验证unread字段是整数
            assert isinstance(message["unread"], int), "unread字段应该是整数"
            assert message["unread"] >= 0, "unread字段应该是非负整数"

    def test_initial_message_contains_unread_count(self, client, test_user):
        """
        测试初始消息包含正确的未读消息数

        验证：
        - 初始消息的unread字段反映用户的实际未读消息数
        - 对于新用户（无消息），unread应该为0

        覆盖代码：websocket.py 第50行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接并接收初始消息
        with ws_client.connect() as _:
            message = ws_client.receive_message()

            # 验证消息格式
            assert message is not None
            assert "unread" in message

            # 对于测试用户，未读消息数应该是0（假设没有预先创建消息）
            assert message["unread"] == 0, "新用户的未读消息数应该为0"

    def test_initial_message_format_structure(self, client, test_user):
        """
        测试初始消息的格式和结构

        验证：
        - 消息是有效的JSON对象
        - 消息包含所有必需字段
        - 消息字段类型正确

        覆盖代码：websocket.py 第50行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            message = ws_client.receive_message()

            # 验证消息是字典类型
            assert isinstance(message, dict), "消息应该是字典类型"

            # 验证必需字段存在
            required_fields = ["type", "unread"]
            for field in required_fields:
                assert field in message, f"消息应该包含{field}字段"

            # 验证字段类型
            assert isinstance(message["type"], str), "type字段应该是字符串"
            assert isinstance(message["unread"], int), "unread字段应该是整数"

            # 如果有last_message字段，验证其类型
            if "last_message" in message:
                assert isinstance(message["last_message"], dict), "last_message字段应该是字典"

    def test_send_message_update_called_after_connect(self, client, test_user):
        """
        测试连接建立后调用send_message_update

        验证：
        - 连接建立后，message_ws_manager.send_message_update被调用
        - send_message_update使用正确的user_id参数

        覆盖代码：websocket.py 第50行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # Mock send_message_update方法
        with patch.object(message_ws_manager, "send_message_update", new_callable=AsyncMock) as mock_send:
            # 创建WebSocket测试客户端
            ws_client = WebSocketTestClient(client, token)

            # 建立连接
            with ws_client.connect() as ws:
                # 验证连接成功
                assert ws is not None

                # 验证send_message_update被调用
                mock_send.assert_called_once()

                # 验证调用参数是正确的user_id
                call_args = mock_send.call_args
                assert call_args is not None
                assert call_args[0][0] == test_user.id, "应该使用正确的user_id调用send_message_update"

    def test_multiple_connections_receive_initial_message(self, client, test_user):
        """
        测试多个连接都能接收到初始消息

        验证：
        - 同一用户的多个WebSocket连接都能接收到初始消息
        - 每个连接独立接收消息

        覆盖代码：websocket.py 第47-50行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建第一个连接
        ws_client1 = WebSocketTestClient(client, token)
        with ws_client1.connect() as _:
            # 接收第一个连接的初始消息
            message1 = ws_client1.receive_message()
            assert message1 is not None
            assert message1["type"] == "message_update"

            # 创建第二个连接
            ws_client2 = WebSocketTestClient(client, token)
            with ws_client2.connect() as _:
                # 接收第二个连接的初始消息
                message2 = ws_client2.receive_message()
                assert message2 is not None
                assert message2["type"] == "message_update"

                # 验证两个消息都有效
                assert "unread" in message1
                assert "unread" in message2

    def test_initial_message_sent_before_receive_loop(self, client, factory):
        """
        测试初始消息在接收循环之前发送

        验证：
        - 初始消息在进入receive_text()循环之前就已发送
        - 客户端能立即接收到消息，无需发送任何数据

        覆盖代码：websocket.py 第50行（在第53-55行的循环之前）
        """
        # 创建测试用户
        test_user = factory.create_user()

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 不发送任何消息，直接接收
            # 如果初始消息在循环之前发送，应该能立即接收到
            message = ws_client.receive_message()

            # 验证能够接收到消息
            assert message is not None, "应该能立即接收到初始消息，无需发送数据"
            assert message["type"] == "message_update"
            assert "unread" in message


class TestWebSocketMessageUpdateContent:
    """测试消息更新的内容和数据"""

    def test_message_update_with_no_messages(self, client, test_user):
        """
        测试用户无消息时的消息更新

        验证：
        - 用户没有消息时，unread为0
        - 不包含last_message字段（或为None）

        覆盖代码：websocket.py 第50行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            message = ws_client.receive_message()

            # 验证消息内容
            assert message is not None
            assert message["type"] == "message_update"
            assert message["unread"] == 0, "无消息时unread应该为0"

            # last_message字段可能不存在或为None
            if "last_message" in message:
                # 如果存在，应该为None或空
                assert message["last_message"] is None or message["last_message"] == {}

    def test_message_update_type_field(self, client, test_user):
        """
        测试消息更新的type字段

        验证：
        - type字段始终为"message_update"
        - type字段是字符串类型

        覆盖代码：websocket.py 第50行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            message = ws_client.receive_message()

            # 验证type字段
            assert "type" in message
            assert isinstance(message["type"], str)
            assert message["type"] == "message_update", "type字段应该始终为message_update"

    def test_message_update_unread_field_type(self, client, factory):
        """
        测试消息更新的unread字段类型

        验证：
        - unread字段是整数类型
        - unread字段是非负数

        覆盖代码：websocket.py 第50行
        """
        # 创建测试用户
        test_user = factory.create_user()

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            message = ws_client.receive_message()

            # 验证unread字段
            assert "unread" in message
            assert isinstance(message["unread"], int), "unread应该是整数类型"
            assert message["unread"] >= 0, "unread应该是非负整数"


class TestWebSocketConnectionFlow:
    """测试WebSocket连接流程"""

    def test_connection_and_message_push_sequence(self, client, test_user):
        """
        测试连接和消息推送的顺序

        验证：
        - 连接建立（connect）在消息推送（send_message_update）之前
        - 消息推送在接收循环（receive_text）之前

        覆盖代码：websocket.py 第47-55行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 跟踪调用顺序
        call_sequence = []

        # Mock connect和send_message_update
        original_connect = message_ws_manager.connect
        original_send = message_ws_manager.send_message_update

        async def mock_connect(user_id, websocket):
            call_sequence.append("connect")
            return await original_connect(user_id, websocket)

        async def mock_send(user_id):
            call_sequence.append("send_message_update")
            return await original_send(user_id)

        with patch.object(message_ws_manager, "connect", side_effect=mock_connect):
            with patch.object(message_ws_manager, "send_message_update", side_effect=mock_send):
                # 创建WebSocket测试客户端
                ws_client = WebSocketTestClient(client, token)

                # 建立连接
                with ws_client.connect() as _:
                    # 接收初始消息
                    message = ws_client.receive_message()

                    # 验证消息接收成功
                    assert message is not None

                    # 验证调用顺序
                    assert len(call_sequence) >= 2, "应该调用connect和send_message_update"
                    assert call_sequence[0] == "connect", "connect应该首先被调用"
                    assert call_sequence[1] == "send_message_update", "send_message_update应该在connect之后被调用"

    def test_initial_message_received_immediately(self, client, test_user):
        """
        测试初始消息立即接收

        验证：
        - 连接建立后，客户端无需等待即可接收到初始消息
        - 客户端无需发送任何数据即可接收初始消息

        覆盖代码：websocket.py 第50行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 立即尝试接收消息（不发送任何数据）
            message = ws_client.receive_message()

            # 验证能够立即接收到消息
            assert message is not None, "应该能立即接收到初始消息"
            assert message["type"] == "message_update"
            assert "unread" in message
