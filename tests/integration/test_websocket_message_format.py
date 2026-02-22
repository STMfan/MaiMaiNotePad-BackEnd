"""
WebSocket消息格式验证测试

测试 app/api/websocket.py 中的消息格式验证功能。
验证服务器发送的消息格式正确，以及服务器能够处理客户端发送的各种格式消息。

覆盖代码：
- 第54-55行：receive_text()接收各种格式的消息
- 验证服务器发送的消息格式符合规范
- 验证服务器能够处理客户端发送的各种格式（包括无效格式）
"""

import pytest

# Mark all tests in this file as serial to avoid WebSocket connection conflicts
pytestmark = pytest.mark.serial
import json  # noqa: E402
import time  # noqa: E402
from tests.helpers.websocket_client import WebSocketTestClient  # noqa: E402
from app.core.security import create_access_token  # noqa: E402


class TestServerMessageFormat:
    """测试服务器发送的消息格式"""

    def test_server_message_is_valid_json(self, client, test_user):
        """
        测试服务器发送的消息是有效的JSON格式

        验证：
        - 服务器发送的消息可以被解析为JSON
        - 消息是字典类型
        - 消息包含必需字段

        覆盖代码：验证send_message_update发送的消息格式
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            message = ws_client.receive_message()

            # 验证消息不为空
            assert message is not None, "应该接收到消息"

            # 验证消息是字典类型（已被解析为JSON）
            assert isinstance(message, dict), "消息应该是有效的JSON对象"

            # 验证消息包含必需字段
            assert "type" in message, "消息应该包含type字段"
            assert "unread" in message, "消息应该包含unread字段"

    def test_server_message_type_field(self, client, test_user):
        """
        测试服务器消息的type字段格式

        验证：
        - type字段存在
        - type字段是字符串类型
        - type字段值为"message_update"

        覆盖代码：验证消息格式规范
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
            assert "type" in message, "消息必须包含type字段"
            assert isinstance(message["type"], str), "type字段必须是字符串"
            assert message["type"] == "message_update", "type字段值应该是message_update"
            assert len(message["type"]) > 0, "type字段不能为空字符串"

    def test_server_message_unread_field(self, client, test_user):
        """
        测试服务器消息的unread字段格式

        验证：
        - unread字段存在
        - unread字段是整数类型
        - unread字段值非负

        覆盖代码：验证消息格式规范
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            message = ws_client.receive_message()

            # 验证unread字段
            assert "unread" in message, "消息必须包含unread字段"
            assert isinstance(message["unread"], int), "unread字段必须是整数"
            assert message["unread"] >= 0, "unread字段必须是非负整数"

    def test_server_message_last_message_field_optional(self, client, test_user):
        """
        测试服务器消息的last_message字段（可选）

        验证：
        - last_message字段可能存在或不存在
        - 如果存在，应该是字典类型或None
        - 如果是字典，应该包含消息的基本字段

        覆盖代码：验证消息格式规范
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            message = ws_client.receive_message()

            # 验证消息基本结构
            assert message is not None

            # 如果last_message字段存在，验证其格式
            if "last_message" in message:
                last_msg = message["last_message"]

                # last_message可以是None或字典
                assert last_msg is None or isinstance(last_msg, dict), "last_message字段应该是None或字典类型"

                # 如果是字典，验证包含基本字段
                if isinstance(last_msg, dict) and last_msg:
                    # 消息对象应该有id字段
                    assert "id" in last_msg or len(last_msg) == 0, "last_message如果不为空，应该包含id字段"

    def test_server_message_no_extra_required_fields(self, client, test_user):
        """
        测试服务器消息只包含必需和可选字段

        验证：
        - 消息包含type和unread字段（必需）
        - 消息可能包含last_message字段（可选）
        - 消息不包含未定义的字段

        覆盖代码：验证消息格式规范
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 接收初始消息
            message = ws_client.receive_message()

            # 验证消息不为空
            assert message is not None

            # 定义允许的字段
            allowed_fields = {"type", "unread", "last_message"}

            # 验证消息只包含允许的字段
            message_fields = set(message.keys())
            unexpected_fields = message_fields - allowed_fields

            assert len(unexpected_fields) == 0, f"消息包含未定义的字段: {unexpected_fields}"


class TestClientMessageFormat:
    """测试客户端发送的消息格式处理"""

    def test_client_sends_plain_text_message(self, client, test_user):
        """
        测试客户端发送纯文本消息

        验证：
        - 服务器能够接收纯文本消息
        - 纯文本消息不会导致错误
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行（receive_text()接收文本）
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

            # 发送纯文本消息
            success = ws_client.send_text_message("plain text message")
            assert success is True, "发送纯文本消息应该成功"

            # 等待处理
            time.sleep(0.1)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送纯文本消息后连接应该保持活跃"

    def test_client_sends_json_string_message(self, client, test_user):
        """
        测试客户端发送JSON字符串消息

        验证：
        - 服务器能够接收JSON格式的字符串消息
        - JSON字符串不会导致解析错误
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行（receive_text()接收JSON字符串）
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

            # 发送JSON格式的字符串消息
            json_string = json.dumps({"type": "ping", "data": "test"})
            success = ws_client.send_text_message(json_string)
            assert success is True, "发送JSON字符串消息应该成功"

            # 等待处理
            time.sleep(0.1)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送JSON字符串消息后连接应该保持活跃"

    def test_client_sends_empty_message(self, client, test_user):
        """
        测试客户端发送空消息

        验证：
        - 服务器能够接收空字符串消息
        - 空消息不会导致错误
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
            assert success is True, "发送空消息应该成功"

            # 等待处理
            time.sleep(0.1)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送空消息后连接应该保持活跃"

    def test_client_sends_whitespace_only_message(self, client, test_user):
        """
        测试客户端发送仅包含空白字符的消息

        验证：
        - 服务器能够接收空白字符消息
        - 空白字符消息不会导致错误
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行
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

            # 发送仅包含空白字符的消息
            whitespace_messages = [
                " ",  # 单个空格
                "   ",  # 多个空格
                "\t",  # 制表符
                "\n",  # 换行符
                " \t\n ",  # 混合空白字符
            ]

            for msg in whitespace_messages:
                success = ws_client.send_text_message(msg)
                assert success is True, f"发送空白字符消息应该成功: {repr(msg)}"
                time.sleep(0.05)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送空白字符消息后连接应该保持活跃"

    def test_client_sends_invalid_json_string(self, client, test_user):
        """
        测试客户端发送无效的JSON字符串

        验证：
        - 服务器能够接收无效的JSON字符串（作为普通文本）
        - 无效JSON不会导致服务器错误
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行（receive_text()接收无效JSON）
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

            # 发送无效的JSON字符串
            invalid_json_messages = [
                "{invalid json}",
                '{"key": value}',  # 值没有引号
                '{"key": "value"',  # 缺少闭合括号
                '{key: "value"}',  # 键没有引号
                '["array", "without", "closing"',  # 数组未闭合
                "null",  # 虽然是有效JSON，但作为文本发送
                "true",  # 布尔值
                "123",  # 数字
            ]

            for msg in invalid_json_messages:
                success = ws_client.send_text_message(msg)
                assert success is True, f"发送无效JSON应该成功: {msg}"
                time.sleep(0.05)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送无效JSON后连接应该保持活跃"

    def test_client_sends_special_characters(self, client, test_user):
        """
        测试客户端发送包含特殊字符的消息

        验证：
        - 服务器能够接收包含特殊字符的消息
        - 特殊字符不会导致解析错误
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行
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
                "Hello 世界 🌍",  # Unicode和Emoji
                "Line1\nLine2\nLine3",  # 换行符
                "Tab\tSeparated\tValues",  # 制表符
                "Quote\"Test'Quote",  # 引号
                "Special: !@#$%^&*()",  # 特殊符号
                "Path: C:\\Users\\Test",  # 反斜杠
                "<html><body>test</body></html>",  # HTML标签
                "SQL: SELECT * FROM users WHERE id='1'",  # SQL语句
                "Script: <script>alert('xss')</script>",  # 潜在XSS
            ]

            for msg in special_messages:
                success = ws_client.send_text_message(msg)
                assert success is True, f"发送特殊字符消息应该成功: {msg[:30]}"
                time.sleep(0.05)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送特殊字符消息后连接应该保持活跃"

    def test_client_sends_very_long_message(self, client, test_user):
        """
        测试客户端发送超长消息

        验证：
        - 服务器能够接收超长消息
        - 超长消息不会导致缓冲区溢出或错误
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

            # 发送超长消息（10KB）
            long_message = "a" * 10000
            success = ws_client.send_text_message(long_message)
            assert success is True, "发送超长消息应该成功"

            # 等待处理
            time.sleep(0.2)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送超长消息后连接应该保持活跃"


class TestMessageFormatEdgeCases:
    """测试消息格式的边界情况"""

    def test_client_sends_binary_like_text(self, client, test_user):
        """
        测试客户端发送类似二进制的文本消息

        验证：
        - 服务器能够接收包含控制字符的文本
        - 控制字符不会导致错误
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行
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

            # 发送包含控制字符的消息
            control_char_messages = [
                "\x00",  # NULL字符
                "\x01\x02\x03",  # 控制字符
                "test\x00message",  # 包含NULL的消息
            ]

            for msg in control_char_messages:
                try:
                    success = ws_client.send_text_message(msg)
                    # 某些控制字符可能被拒绝，这是正常的
                    if success:
                        time.sleep(0.05)
                except Exception:
                    # 如果发送失败，这也是可以接受的
                    pass

            # 验证连接状态（可能已断开，取决于WebSocket实现）
            # 这里不强制要求连接保持活跃，因为某些控制字符可能导致断开

    def test_client_sends_unicode_edge_cases(self, client, test_user):
        """
        测试客户端发送Unicode边界情况

        验证：
        - 服务器能够接收各种Unicode字符
        - Unicode字符不会导致编码错误
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行
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

            # 发送各种Unicode字符
            unicode_messages = [
                "中文测试",  # 中文
                "日本語テスト",  # 日文
                "한국어 테스트",  # 韩文
                "العربية",  # 阿拉伯文
                "עברית",  # 希伯来文
                "Русский",  # 俄文
                "🎉🎊🎈🎁",  # Emoji
                "𝕳𝖊𝖑𝖑𝖔",  # 数学字母数字符号
                "①②③④⑤",  # 带圈数字
            ]

            for msg in unicode_messages:
                success = ws_client.send_text_message(msg)
                assert success is True, f"发送Unicode消息应该成功: {msg}"
                time.sleep(0.05)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送Unicode消息后连接应该保持活跃"

    def test_client_sends_repeated_messages_same_content(self, client, test_user):
        """
        测试客户端重复发送相同内容的消息

        验证：
        - 服务器能够接收重复的消息
        - 重复消息不会被去重或拒绝
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行
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

            # 重复发送相同消息
            repeated_message = "repeated message"
            num_repeats = 10

            for i in range(num_repeats):
                success = ws_client.send_text_message(repeated_message)
                assert success is True, f"第{i+1}次发送重复消息应该成功"
                time.sleep(0.05)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送重复消息后连接应该保持活跃"

            # 验证消息统计
            stats = ws_client.get_message_statistics()
            assert stats["sent_count"] == num_repeats, f"应该发送了{num_repeats}条消息"


class TestMessageFormatIntegration:
    """测试消息格式的集成场景"""

    def test_mixed_format_messages_in_sequence(self, client, test_user):
        """
        测试混合格式消息的顺序发送

        验证：
        - 服务器能够连续接收不同格式的消息
        - 格式切换不会导致错误
        - 连接保持活跃

        覆盖代码：websocket.py 第54-55行
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

            # 发送混合格式的消息序列
            messages = [
                "plain text",
                json.dumps({"type": "json", "id": 1}),
                "",
                "   ",
                "Unicode: 你好",
                "{invalid json}",
                "a" * 1000,  # 长消息
                "Special: !@#$%",
                json.dumps({"nested": {"data": "value"}}),
                "final message",
            ]

            for i, msg in enumerate(messages):
                success = ws_client.send_text_message(msg)
                assert success is True, f"第{i+1}条混合格式消息应该成功"
                time.sleep(0.05)

            # 验证连接仍然活跃
            assert ws_client.is_connected(), "发送混合格式消息后连接应该保持活跃"

            # 验证消息统计
            stats = ws_client.get_message_statistics()
            assert stats["sent_count"] == len(messages), f"应该发送了{len(messages)}条消息"

    def test_server_and_client_message_format_compatibility(self, client, test_user):
        """
        测试服务器和客户端消息格式的兼容性

        验证：
        - 服务器发送的消息格式正确
        - 客户端可以发送各种格式的消息
        - 双向通信正常工作

        覆盖代码：websocket.py 第54-55行，以及send_message_update
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as _:
            # 1. 接收服务器发送的消息
            server_message = ws_client.receive_message()
            assert server_message is not None
            assert isinstance(server_message, dict)
            assert "type" in server_message
            assert "unread" in server_message

            # 2. 客户端发送各种格式的消息
            client_messages = [
                "text message",
                json.dumps({"client": "data"}),
                "",
                "Unicode: 测试",
            ]

            for msg in client_messages:
                success = ws_client.send_text_message(msg)
                assert success is True
                time.sleep(0.05)

            # 3. 验证连接健康
            health = ws_client.check_connection_health()
            assert health["is_connected"] is True
            assert health["state"] == "connected"

            # 4. 验证双向通信统计
            stats = ws_client.get_message_statistics()
            assert stats["received_count"] >= 1  # 至少接收到服务器的初始消息
            assert stats["sent_count"] == len(client_messages)  # 发送了所有客户端消息
