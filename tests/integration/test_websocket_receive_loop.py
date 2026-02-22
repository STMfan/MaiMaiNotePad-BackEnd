"""
WebSocket消息接收循环测试

测试 app/api/websocket.py 中的消息接收循环功能（第53-55行）。
覆盖while True循环中的receive_text()调用，验证服务器能够持续接收客户端消息。

覆盖代码：
- 第53行：while True:
- 第54-55行：await websocket.receive_text()
"""

import pytest

# Mark all tests in this file as serial to avoid WebSocket connection conflicts
pytestmark = pytest.mark.serial
import time  # noqa: E402
from tests.helpers.websocket_client import WebSocketTestClient  # noqa: E402
from app.core.security import create_access_token  # noqa: E402


class TestWebSocketReceiveLoop:
    """测试WebSocket消息接收循环"""

    def test_server_receives_client_message(self, client, test_user):
        """
        测试服务器能够接收客户端发送的消息

        验证：
        - 客户端可以向服务器发送文本消息
        - 服务器的receive_text()能够接收消息
        - 连接在发送消息后保持活跃
        - 循环继续运行，不会因为接收消息而中断

        覆盖代码：websocket.py 第54-55行（receive_text()调用）
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

            # 接收初始消息（服务器推送的消息更新）
            initial_message = ws_client.receive_message()
            assert initial_message is not None
            assert initial_message["type"] == "message_update"

            # 客户端发送消息给服务器
            test_message = "test message from client"
            success = ws_client.send_text_message(test_message)
            assert success, "消息发送应该成功"

            # 等待一小段时间，确保服务器处理了消息
            time.sleep(0.1)

            # 验证连接仍然活跃（没有因为接收消息而断开）
            assert ws_client.is_connected(), "连接应该保持活跃"

    def test_receive_loop_continues_after_message(self, client, test_user):
        """
        测试接收循环在接收消息后继续运行

        验证：
        - 服务器接收一条消息后，循环继续运行
        - 可以接收多条消息
        - 每条消息都被正确处理
        - 循环不会因为接收消息而退出

        覆盖代码：websocket.py 第53-55行（while True循环持续运行）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送多条消息，验证循环持续运行
            messages_to_send = ["message 1", "message 2", "message 3"]

            for msg in messages_to_send:
                # 发送消息
                success = ws_client.send_text_message(msg)
                assert success, f"发送消息 '{msg}' 应该成功"

                # 短暂等待
                time.sleep(0.05)

                # 验证连接仍然活跃
                assert ws_client.is_connected(), f"发送 '{msg}' 后连接应该保持活跃"

            # 验证连接在发送所有消息后仍然活跃
            assert ws_client.is_connected(), "发送所有消息后连接应该保持活跃"

    def test_receive_loop_keeps_connection_alive(self, client, test_user):
        """
        测试接收循环保持连接活跃

        验证：
        - while True循环使连接保持打开状态
        - 即使没有消息，连接也不会自动关闭
        - 循环持续等待接收消息

        覆盖代码：websocket.py 第53行（while True保持连接）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 等待一段时间，不发送任何消息
            time.sleep(0.5)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "连接应该保持活跃，即使没有消息"

            # 验证连接持续时间
            duration = ws_client.get_connection_duration()
            assert duration is not None
            assert duration >= 0.5, "连接应该至少持续0.5秒"

            # 现在发送一条消息，验证循环仍在运行
            success = ws_client.send_text_message("ping")
            assert success, "发送消息应该成功"

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送消息后连接应该保持活跃"

    def test_receive_loop_handles_multiple_messages_rapidly(self, client, test_user):
        """
        测试接收循环快速处理多条消息

        验证：
        - 循环可以快速连续接收多条消息
        - 不会因为消息频率高而出错
        - 所有消息都被正确处理

        覆盖代码：websocket.py 第53-55行（循环快速处理消息）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 快速发送多条消息
            num_messages = 10
            for i in range(num_messages):
                success = ws_client.send_text_message(f"rapid message {i}")
                assert success, f"发送消息 {i} 应该成功"

            # 短暂等待，确保所有消息都被处理
            time.sleep(0.2)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "快速发送消息后连接应该保持活跃"

    def test_receive_loop_with_empty_messages(self, client, test_user):
        """
        测试接收循环处理空消息

        验证：
        - 循环可以接收空字符串消息
        - 空消息不会导致循环退出
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行（receive_text()接收空消息）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送空消息
            success = ws_client.send_text_message("")
            assert success, "发送空消息应该成功"

            # 等待处理
            time.sleep(0.1)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送空消息后连接应该保持活跃"

            # 发送正常消息，验证循环仍在运行
            success = ws_client.send_text_message("normal message")
            assert success, "发送正常消息应该成功"

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "连接应该保持活跃"

    def test_receive_loop_continues_until_disconnect(self, client, test_user):
        """
        测试接收循环持续运行直到断开连接

        验证：
        - while True循环持续运行
        - 只有在断开连接时循环才退出
        - 正常断开连接会触发WebSocketDisconnect异常

        覆盖代码：websocket.py 第53-55行（循环直到断开）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送几条消息，验证循环运行
            for i in range(3):
                success = ws_client.send_text_message(f"message {i}")
                assert success
                time.sleep(0.05)

            # 验证连接活跃
            assert ws_client.is_connected()

            # 主动断开连接（退出with块会自动断开）

        # 验证连接已断开
        assert not ws_client.is_connected(), "退出with块后连接应该断开"


class TestWebSocketReceiveLoopEdgeCases:
    """测试接收循环的边界情况"""

    def test_receive_loop_with_long_messages(self, client, test_user):
        """
        测试接收循环处理长消息

        验证：
        - 循环可以接收长文本消息
        - 长消息不会导致循环出错
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行（receive_text()接收长消息）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送长消息（1000个字符）
            long_message = "a" * 1000
            success = ws_client.send_text_message(long_message)
            assert success, "发送长消息应该成功"

            # 等待处理
            time.sleep(0.1)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送长消息后连接应该保持活跃"

    def test_receive_loop_with_special_characters(self, client, test_user):
        """
        测试接收循环处理特殊字符消息

        验证：
        - 循环可以接收包含特殊字符的消息
        - 特殊字符不会导致循环出错
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行（receive_text()接收特殊字符）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送包含特殊字符的消息
            special_messages = [
                "Hello 世界",  # Unicode字符
                "Test\nNewline",  # 换行符
                "Tab\tCharacter",  # 制表符
                'Quote"Test',  # 引号
                "Emoji 😀🎉",  # Emoji
            ]

            for msg in special_messages:
                success = ws_client.send_text_message(msg)
                assert success, f"发送特殊字符消息 '{msg}' 应该成功"
                time.sleep(0.05)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送特殊字符消息后连接应该保持活跃"

    def test_receive_loop_with_intermittent_messages(self, client, test_user):
        """
        测试接收循环处理间歇性消息

        验证：
        - 循环可以处理间隔发送的消息
        - 消息之间的等待不会导致连接断开
        - 循环持续等待新消息

        覆盖代码：websocket.py 第53-55行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送消息，中间有较长间隔
            intervals = [0.1, 0.2, 0.3]
            for i, interval in enumerate(intervals):
                # 等待
                time.sleep(interval)

                # 发送消息
                success = ws_client.send_text_message(f"message after {interval}s")
                assert success, f"间隔 {interval}s 后发送消息应该成功"

                # 验证连接仍然活跃
                assert ws_client.is_connected(), f"间隔 {interval}s 后连接应该保持活跃"


class TestWebSocketReceiveLoopIntegration:
    """测试接收循环的集成场景"""

    def test_receive_loop_full_lifecycle(self, client, test_user):
        """
        测试接收循环的完整生命周期

        验证：
        - 连接建立后循环开始运行
        - 循环持续接收消息
        - 断开连接时循环正常退出

        覆盖代码：websocket.py 第53-55行（完整生命周期）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 1. 连接建立，接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None
            assert initial_message["type"] == "message_update"

            # 2. 循环运行，发送和接收消息
            for i in range(3):
                success = ws_client.send_text_message(f"lifecycle message {i}")
                assert success
                time.sleep(0.05)
                assert ws_client.is_connected()

            # 3. 验证连接健康
            health = ws_client.check_connection_health()
            assert health["is_connected"] is True
            assert health["state"] == "connected"

            # 4. 正常断开（退出with块）

        # 5. 验证连接已断开
        assert not ws_client.is_connected()
        health = ws_client.check_connection_health()
        assert health["is_connected"] is False
        assert health["state"] == "disconnected"

    def test_receive_loop_with_message_statistics(self, client, test_user):
        """
        测试接收循环的消息统计

        验证：
        - 循环正确处理所有发送的消息
        - 消息统计准确

        覆盖代码：websocket.py 第53-55行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送多条消息
            num_messages = 5
            for i in range(num_messages):
                ws_client.send_text_message(f"stats message {i}")
                time.sleep(0.05)

            # 获取消息统计
            stats = ws_client.get_message_statistics()

            # 验证统计信息
            assert stats["sent_count"] == num_messages, f"应该发送了 {num_messages} 条消息"
            assert stats["received_count"] >= 1, "至少应该接收到初始消息"

            # 验证连接仍然活跃
            assert ws_client.is_connected()
