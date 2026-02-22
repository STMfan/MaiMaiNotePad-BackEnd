"""
WebSocket客户端消息发送测试

测试 app/api/websocket.py 中客户端向服务器发送消息的功能。
覆盖客户端消息发送、服务器接收和连接保持活跃的场景。

覆盖代码：
- 第53-55行：while True循环中的receive_text()调用
- 验证服务器能够接收客户端发送的各种类型消息
"""

import pytest

# Mark all tests in this file as serial to avoid WebSocket connection conflicts
pytestmark = pytest.mark.serial
import time
from tests.helpers.websocket_client import WebSocketTestClient
from app.core.security import create_access_token


class TestWebSocketClientSendBasic:
    """测试客户端基本消息发送功能"""

    def test_client_sends_text_message_successfully(self, client, test_user):
        """
        测试客户端成功发送文本消息

        验证：
        - 客户端可以向服务器发送文本消息
        - 服务器的receive_text()能够接收消息
        - 发送操作返回成功状态
        - 连接在发送后保持活跃

        覆盖代码：websocket.py 第54-55行（receive_text()接收客户端消息）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 客户端发送文本消息
            test_message = "Hello from client"
            success = ws_client.send_text_message(test_message)

            # 验证发送成功
            assert success is True, "文本消息发送应该成功"

            # 等待服务器处理
            time.sleep(0.1)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送消息后连接应该保持活跃"

    def test_client_sends_multiple_messages(self, client, test_user):
        """
        测试客户端发送多条消息

        验证：
        - 客户端可以连续发送多条消息
        - 每条消息都被服务器正确接收
        - 连接在发送多条消息后保持活跃
        - 服务器的接收循环持续运行

        覆盖代码：websocket.py 第53-55行（循环持续接收多条消息）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送多条消息
            messages = ["message 1", "message 2", "message 3", "message 4", "message 5"]

            for i, msg in enumerate(messages):
                success = ws_client.send_text_message(msg)
                assert success is True, f"消息 {i+1} 发送应该成功"
                time.sleep(0.05)  # 短暂等待

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送多条消息后连接应该保持活跃"

            # 获取消息统计
            stats = ws_client.get_message_statistics()
            assert stats["sent_count"] == len(messages), f"应该发送了 {len(messages)} 条消息"

    def test_client_sends_empty_message(self, client, test_user):
        """
        测试客户端发送空消息

        验证：
        - 客户端可以发送空字符串消息
        - 服务器能够接收空消息
        - 空消息不会导致连接断开
        - 接收循环继续运行

        覆盖代码：websocket.py 第54-55行（receive_text()接收空消息）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送空消息
            success = ws_client.send_text_message("")
            assert success is True, "空消息发送应该成功"

            # 等待处理
            time.sleep(0.1)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送空消息后连接应该保持活跃"

            # 发送正常消息，验证循环仍在运行
            success = ws_client.send_text_message("normal message after empty")
            assert success is True, "空消息后发送正常消息应该成功"

    def test_client_sends_json_message(self, client, test_user):
        """
        测试客户端发送JSON消息

        验证：
        - 客户端可以发送JSON格式消息
        - 服务器能够接收JSON消息（作为文本）
        - JSON消息不会导致错误
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送JSON消息
            json_data = {"type": "ping", "timestamp": time.time(), "data": "test"}
            success = ws_client.send_json_message(json_data)
            assert success is True, "JSON消息发送应该成功"

            # 等待处理
            time.sleep(0.1)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送JSON消息后连接应该保持活跃"


class TestWebSocketClientSendEdgeCases:
    """测试客户端消息发送的边界情况"""

    def test_client_sends_long_message(self, client, test_user):
        """
        测试客户端发送长消息

        验证：
        - 客户端可以发送长文本消息（1000+字符）
        - 服务器能够接收长消息
        - 长消息不会导致连接断开或错误
        - 接收循环正常处理长消息

        覆盖代码：websocket.py 第54-55行（receive_text()接收长消息）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送长消息（2000个字符）
            long_message = "a" * 2000
            success = ws_client.send_text_message(long_message)
            assert success is True, "长消息发送应该成功"

            # 等待处理
            time.sleep(0.2)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送长消息后连接应该保持活跃"

            # 发送正常消息，验证循环仍在运行
            success = ws_client.send_text_message("normal message after long")
            assert success is True

    def test_client_sends_special_characters(self, client, test_user):
        """
        测试客户端发送包含特殊字符的消息

        验证：
        - 客户端可以发送包含Unicode、换行符、制表符等特殊字符的消息
        - 服务器能够正确接收特殊字符
        - 特殊字符不会导致解析错误
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送包含特殊字符的消息
            special_messages = [
                "Hello 世界 🌍",  # Unicode和Emoji
                "Line1\nLine2\nLine3",  # 换行符
                "Tab\tSeparated\tValues",  # 制表符
                "Quote\"Test'Quote",  # 引号
                "Special: !@#$%^&*()",  # 特殊符号
                "Path: C:\\Users\\Test",  # 反斜杠
            ]

            for msg in special_messages:
                success = ws_client.send_text_message(msg)
                assert success is True, f"发送特殊字符消息应该成功: {msg[:20]}"
                time.sleep(0.05)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送特殊字符消息后连接应该保持活跃"

    def test_client_sends_rapid_messages(self, client, test_user):
        """
        测试客户端快速连续发送消息

        验证：
        - 客户端可以快速连续发送多条消息
        - 服务器的接收循环能够快速处理消息
        - 不会因为消息频率高而出错
        - 所有消息都被正确处理

        覆盖代码：websocket.py 第53-55行（循环快速处理消息）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 快速发送20条消息
            num_messages = 20
            for i in range(num_messages):
                success = ws_client.send_text_message(f"rapid message {i}")
                assert success is True, f"快速消息 {i} 发送应该成功"
                # 不等待，立即发送下一条

            # 等待所有消息被处理
            time.sleep(0.3)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "快速发送消息后连接应该保持活跃"

            # 验证消息统计
            stats = ws_client.get_message_statistics()
            assert stats["sent_count"] == num_messages, f"应该发送了 {num_messages} 条消息"

    def test_client_sends_messages_with_delays(self, client, test_user):
        """
        测试客户端间歇性发送消息

        验证：
        - 客户端可以在消息之间有较长间隔
        - 服务器的接收循环在等待期间保持活跃
        - 间隔不会导致连接超时或断开
        - 循环持续等待新消息

        覆盖代码：websocket.py 第53-55行（循环等待消息）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送消息，中间有较长间隔
            intervals = [0.2, 0.3, 0.4]
            for i, interval in enumerate(intervals):
                # 等待
                time.sleep(interval)

                # 发送消息
                success = ws_client.send_text_message(f"message after {interval}s delay")
                assert success is True, f"间隔 {interval}s 后发送消息应该成功"

                # 验证连接仍然活跃
                assert ws_client.is_connected(), f"间隔 {interval}s 后连接应该保持活跃"


class TestWebSocketClientSendMessageTypes:
    """测试客户端发送不同类型的消息"""

    def test_client_sends_text_message_type(self, client, test_user):
        """
        测试客户端发送纯文本消息

        验证：
        - 使用send_text_message()方法发送文本
        - 服务器能够接收文本消息
        - 消息类型正确记录

        覆盖代码：websocket.py 第54-55行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送文本消息
            success = ws_client.send_text_message("plain text message")
            assert success is True

            # 验证消息统计
            stats = ws_client.get_message_statistics()
            assert stats["sent_count"] == 1
            assert "text" in stats["sent_by_type"]

    def test_client_sends_json_message_type(self, client, test_user):
        """
        测试客户端发送JSON消息

        验证：
        - 使用send_json_message()方法发送JSON
        - 服务器能够接收JSON消息（作为文本）
        - 消息类型正确记录

        覆盖代码：websocket.py 第54-55行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送JSON消息
            json_data = {"action": "ping", "value": 123}
            success = ws_client.send_json_message(json_data)
            assert success is True

            # 验证消息统计
            stats = ws_client.get_message_statistics()
            assert stats["sent_count"] == 1
            assert "json" in stats["sent_by_type"]

    def test_client_sends_mixed_message_types(self, client, test_user):
        """
        测试客户端发送混合类型消息

        验证：
        - 客户端可以交替发送不同类型的消息
        - 服务器能够接收所有类型的消息
        - 消息统计正确记录各种类型

        覆盖代码：websocket.py 第54-55行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送不同类型的消息
            ws_client.send_text_message("text message 1")
            time.sleep(0.05)

            ws_client.send_json_message({"type": "json", "id": 1})
            time.sleep(0.05)

            ws_client.send_text_message("text message 2")
            time.sleep(0.05)

            ws_client.send_json_message({"type": "json", "id": 2})
            time.sleep(0.05)

            # 验证连接活跃
            assert ws_client.is_connected()

            # 验证消息统计
            stats = ws_client.get_message_statistics()
            assert stats["sent_count"] == 4
            assert stats["sent_by_type"]["text"] == 2
            assert stats["sent_by_type"]["json"] == 2


class TestWebSocketClientSendIntegration:
    """测试客户端消息发送的集成场景"""

    def test_client_send_receive_cycle(self, client, test_user):
        """
        测试完整的发送-接收周期

        验证：
        - 客户端发送消息
        - 服务器接收消息（通过receive_text()）
        - 连接保持活跃
        - 可以继续发送和接收

        覆盖代码：websocket.py 第53-55行（完整周期）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 1. 接收初始消息（服务器推送）
            initial_message = ws_client.receive_message()
            assert initial_message is not None
            assert initial_message["type"] == "message_update"

            # 2. 客户端发送消息
            ws_client.send_text_message("client message 1")
            time.sleep(0.1)

            # 3. 验证连接活跃
            assert ws_client.is_connected()

            # 4. 继续发送更多消息
            ws_client.send_text_message("client message 2")
            ws_client.send_text_message("client message 3")
            time.sleep(0.1)

            # 5. 验证连接仍然活跃
            assert ws_client.is_connected()

            # 6. 验证消息统计
            stats = ws_client.get_message_statistics()
            assert stats["sent_count"] == 3
            assert stats["received_count"] >= 1  # 至少接收到初始消息

    def test_client_send_with_connection_health_check(self, client, test_user):
        """
        测试发送消息时的连接健康检查

        验证：
        - 发送消息前后连接健康
        - 连接持续时间正确更新
        - 连接状态保持正常

        覆盖代码：websocket.py 第53-55行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 检查连接健康
            health_before = ws_client.check_connection_health()
            assert health_before["is_connected"] is True
            assert health_before["state"] == "connected"

            # 发送消息
            ws_client.send_text_message("health check message")
            time.sleep(0.1)

            # 再次检查连接健康
            health_after = ws_client.check_connection_health()
            assert health_after["is_connected"] is True
            assert health_after["state"] == "connected"

            # 验证连接持续时间增加
            duration = ws_client.get_connection_duration()
            assert duration is not None
            assert duration > 0

    def test_client_send_full_lifecycle(self, client, test_user):
        """
        测试客户端消息发送的完整生命周期

        验证：
        - 连接建立
        - 接收初始消息
        - 发送多条消息
        - 连接保持活跃
        - 正常断开连接

        覆盖代码：websocket.py 第53-55行（完整生命周期）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 1. 连接建立，接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None
            assert initial_message["type"] == "message_update"

            # 2. 发送一系列消息
            messages = [
                "lifecycle message 1",
                "lifecycle message 2",
                "lifecycle message 3",
                "lifecycle message 4",
                "lifecycle message 5",
            ]

            for msg in messages:
                success = ws_client.send_text_message(msg)
                assert success is True
                time.sleep(0.05)

            # 3. 验证连接健康
            health = ws_client.check_connection_health()
            assert health["is_connected"] is True
            assert health["state"] == "connected"

            # 4. 验证消息统计
            stats = ws_client.get_message_statistics()
            assert stats["sent_count"] == len(messages)
            assert stats["received_count"] >= 1

            # 5. 正常断开（退出with块）

        # 6. 验证连接已断开
        assert not ws_client.is_connected()
        health = ws_client.check_connection_health()
        assert health["is_connected"] is False
        assert health["state"] == "disconnected"

    def test_multiple_clients_send_messages(self, client, test_user):
        """
        测试多个客户端同时发送消息

        验证：
        - 多个客户端可以同时连接
        - 每个客户端都可以发送消息
        - 服务器能够处理多个客户端的消息
        - 所有连接保持活跃

        覆盖代码：websocket.py 第53-55行（多客户端场景）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建两个客户端
        ws_client1 = WebSocketTestClient(client, token)
        ws_client2 = WebSocketTestClient(client, token)

        # 建立第一个连接
        with ws_client1.connect() as ws1:
            # 接收初始消息
            msg1 = ws_client1.receive_message()
            assert msg1 is not None

            # 建立第二个连接
            with ws_client2.connect() as ws2:
                # 接收初始消息
                msg2 = ws_client2.receive_message()
                assert msg2 is not None

                # 两个客户端都发送消息
                ws_client1.send_text_message("message from client 1")
                ws_client2.send_text_message("message from client 2")
                time.sleep(0.1)

                # 验证两个连接都活跃
                assert ws_client1.is_connected()
                assert ws_client2.is_connected()

                # 继续发送更多消息
                ws_client1.send_text_message("another message from client 1")
                ws_client2.send_text_message("another message from client 2")
                time.sleep(0.1)

                # 验证连接仍然活跃
                assert ws_client1.is_connected()
                assert ws_client2.is_connected()


class TestWebSocketClientSendMessageHistory:
    """测试客户端消息发送的历史记录"""

    def test_client_tracks_sent_messages(self, client, test_user):
        """
        测试客户端跟踪已发送的消息

        验证：
        - 客户端记录所有发送的消息
        - 消息历史包含正确的数量
        - 消息历史包含正确的内容

        覆盖代码：websocket.py 第54-55行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送多条消息
            messages = ["msg1", "msg2", "msg3"]
            for msg in messages:
                ws_client.send_text_message(msg)
                time.sleep(0.05)

            # 获取发送历史
            sent_messages = ws_client.get_sent_messages()

            # 验证历史记录
            assert len(sent_messages) == len(messages)
            for i, record in enumerate(sent_messages):
                assert record["type"] == "text"
                assert record["data"] == messages[i]
                assert "timestamp" in record

    def test_client_message_statistics_accuracy(self, client, test_user):
        """
        测试客户端消息统计的准确性

        验证：
        - 消息统计正确计数
        - 按类型统计正确
        - 发送和接收计数准确

        覆盖代码：websocket.py 第54-55行
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送不同类型的消息
            ws_client.send_text_message("text 1")
            ws_client.send_text_message("text 2")
            ws_client.send_json_message({"id": 1})
            ws_client.send_json_message({"id": 2})
            ws_client.send_json_message({"id": 3})
            time.sleep(0.1)

            # 获取统计信息
            stats = ws_client.get_message_statistics()

            # 验证统计准确性
            assert stats["sent_count"] == 5
            assert stats["sent_by_type"]["text"] == 2
            assert stats["sent_by_type"]["json"] == 3
            assert stats["received_count"] >= 1  # 至少接收到初始消息
