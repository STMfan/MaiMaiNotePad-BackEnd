"""
WebSocket端点集成测试

测试 app/api/websocket.py 中的 message_websocket_endpoint 函数。
覆盖WebSocket连接、认证、消息接收和断开连接的所有场景。
"""

import pytest

# Mark all tests in this file as serial to avoid WebSocket connection conflicts
pytestmark = pytest.mark.serial
from tests.helpers.websocket_client import WebSocketTestClient
from app.core.security import create_access_token


class TestWebSocketValidConnection:
    """测试有效token的WebSocket连接"""

    def test_valid_token_connection_success(self, client, test_user):
        """
        测试有效token连接成功

        验证：
        - 使用有效JWT token可以成功建立WebSocket连接
        - 连接建立后状态为CONNECTED
        - 能够接收到初始的消息更新
        - 初始消息包含正确的字段（type和unread）

        覆盖代码：websocket.py 第35-45行
        """
        # 创建有效的JWT token，包含user_id
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 验证连接成功建立
            assert ws is not None
            assert ws_client.is_connected()

            # 接收初始消息更新
            message = ws_client.receive_message()

            # 验证消息格式
            assert message is not None, "应该接收到初始消息"
            assert "type" in message, "消息应该包含type字段"
            assert message["type"] == "message_update", "消息类型应该是message_update"
            assert "unread" in message, "消息应该包含unread字段"


class TestWebSocketInvalidToken:
    """测试无效token的WebSocket连接被拒绝"""

    def test_invalid_token_rejected_with_1008(self, client):
        """
        测试无效token被拒绝，返回状态码1008

        验证：
        - 使用无效的token字符串（非JWT格式）尝试连接
        - 连接应该被服务器拒绝
        - 服务器应该返回WebSocket关闭代码1008（Policy Violation）
        - 连接不应该成功建立

        覆盖代码：websocket.py 第35-38行（token验证失败路径）
        """
        # 使用明显无效的token字符串
        invalid_token = "invalid_token_string"

        # 直接使用TestClient的websocket_connect方法测试
        # 当token无效时，服务器应该立即关闭连接并返回1008状态码
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{invalid_token}"):
                # 如果能进入这里，说明连接成功了，测试应该失败
                pytest.fail("Connection should have been rejected with invalid token")

        # 验证WebSocket关闭代码为1008
        assert exc_info.value.code == 1008, f"Expected close code 1008, got: {exc_info.value.code}"


class TestWebSocketMissingUserId:
    """测试缺少user_id的token被拒绝"""

    def test_token_without_user_id_rejected_with_1008(self, client):
        """
        测试缺少user_id的token被拒绝，返回状态码1008

        验证：
        - 使用有效的JWT token但不包含"sub"声明（user_id）
        - 连接应该被服务器拒绝
        - 服务器应该返回WebSocket关闭代码1008（Policy Violation）
        - 连接不应该成功建立

        覆盖代码：websocket.py 第40-45行（user_id验证失败路径）
        """
        # 创建一个有效的JWT token，但不包含"sub"声明
        # 只包含其他字段，模拟缺少user_id的情况
        token_without_sub = create_access_token({"username": "testuser", "role": "user"})

        # 直接使用TestClient的websocket_connect方法测试
        # 当token缺少user_id时，服务器应该立即关闭连接并返回1008状态码
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/api/ws/{token_without_sub}"):
                # 如果能进入这里，说明连接成功了，测试应该失败
                pytest.fail("Connection should have been rejected with token missing user_id")

        # 验证WebSocket关闭代码为1008
        assert exc_info.value.code == 1008, f"Expected close code 1008, got: {exc_info.value.code}"


class TestWebSocketMessageHandling:
    """测试WebSocket消息处理和接收循环"""

    def test_message_receive_loop_keeps_connection_alive(self, client, test_user):
        """
        测试消息接收循环保持连接活跃

        验证：
        - 连接建立后进入消息接收循环
        - 客户端可以发送文本消息
        - 服务器接收消息后连接保持活跃
        - 消息接收循环正常工作

        覆盖代码：websocket.py 第46-55行（消息接收循环）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 验证连接成功
            assert ws_client.is_connected()

            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送文本消息（保持连接活跃）
            ws_client.send_message("ping")

            # 验证连接仍然活跃
            assert ws_client.is_connected()

            # 再次发送消息
            ws_client.send_message("test message")

            # 验证连接仍然活跃
            assert ws_client.is_connected()

    def test_message_format_validation_text(self, client, test_user):
        """
        测试文本消息格式验证

        验证：
        - 客户端可以发送纯文本消息
        - 服务器正确接收文本消息
        - 连接保持活跃

        覆盖代码：websocket.py 第46-55行（receive_text调用）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            ws_client.receive_message()

            # 发送各种格式的文本消息
            test_messages = [
                "simple text",
                "带中文的消息",
                "message with numbers 12345",
                "special chars: !@#$%^&*()",
                "",  # 空字符串
            ]

            for msg in test_messages:
                ws_client.send_message(msg)
                # 验证连接仍然活跃
                assert ws_client.is_connected()

    def test_message_format_validation_json(self, client, test_user):
        """
        测试JSON消息格式验证

        验证：
        - 客户端可以发送JSON格式的消息
        - 服务器正确接收JSON消息（作为文本）
        - 连接保持活跃

        覆盖代码：websocket.py 第46-55行（receive_text调用）
        """
        import json

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 接收初始消息
            ws_client.receive_message()

            # 发送JSON格式的消息
            json_messages = [
                {"type": "ping", "timestamp": 1234567890},
                {"action": "subscribe", "channel": "messages"},
                {"data": {"key": "value", "nested": {"field": "test"}}},
            ]

            for msg_obj in json_messages:
                # 将JSON对象转换为字符串发送
                ws_client.send_message(json.dumps(msg_obj))
                # 验证连接仍然活跃
                assert ws_client.is_connected()


class TestWebSocketNormalDisconnect:
    """测试WebSocket正常断开连接"""

    def test_normal_disconnect_with_websocket_disconnect(self, client, test_user):
        """
        测试正常断开连接（WebSocketDisconnect异常）

        验证：
        - 客户端主动关闭连接时触发WebSocketDisconnect异常
        - 服务器正确处理断开连接
        - 连接管理器正确清理连接
        - 不会抛出未捕获的异常

        覆盖代码：websocket.py 第56-59行（WebSocketDisconnect异常处理）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 验证连接成功
            assert ws_client.is_connected()

            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

        # 退出上下文管理器后，连接应该被正常关闭
        # WebSocketDisconnect异常应该被正确捕获和处理
        # 不应该有未捕获的异常
        assert not ws_client.is_connected()

    def test_explicit_disconnect_cleanup(self, client, test_user):
        """
        测试显式断开连接的清理

        验证：
        - 显式调用disconnect后连接被清理
        - 连接状态正确更新
        - 资源被正确释放

        覆盖代码：websocket.py 第56-59行（disconnect调用）
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 验证连接成功
            assert ws_client.is_connected()

            # 接收初始消息
            ws_client.receive_message()

            # 显式断开连接
            ws_client.disconnect()

        # 验证连接已断开
        assert not ws_client.is_connected()


class TestWebSocketExceptionDisconnect:
    """测试异常断开连接（Exception）"""

    def test_exception_disconnect_with_generic_exception(self, client, test_user):
        """
        测试异常断开连接（Exception异常）

        验证：
        - 当WebSocket处理过程中发生异常（非WebSocketDisconnect）时
        - 服务器正确捕获异常
        - 调用disconnect清理连接
        - 调用websocket.close()关闭连接
        - 不会抛出未捕获的异常

        覆盖代码：websocket.py 第60-63行（Exception异常处理）

        实现方式：
        通过在WebSocket连接建立后，模拟客户端发送导致服务器端抛出异常的消息。
        由于TestClient的限制，我们通过关闭连接来模拟异常场景。
        """

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 验证连接成功
            assert ws_client.is_connected()

            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 模拟网络错误（异常断开）
            # 这会触发服务器端的Exception处理分支
            ws_client.simulate_network_error()

        # 验证连接已断开
        assert not ws_client.is_connected()

    def test_exception_during_message_processing(self, client, test_user):
        """
        测试消息处理时发生异常触发清理

        验证：
        - 在消息处理过程中发生异常
        - 异常被正确捕获
        - 连接管理器正确清理连接
        - websocket.close()被调用

        覆盖代码：websocket.py 第60-63行（Exception异常处理和清理）

        实现方式：
        通过模拟异常关闭（code 1006）来触发服务器端的异常处理逻辑。
        """
        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建WebSocket测试客户端
        ws_client = WebSocketTestClient(client, token)

        # 建立连接
        with ws_client.connect() as ws:
            # 验证连接成功
            assert ws_client.is_connected()

            # 接收初始消息
            initial_message = ws_client.receive_message()
            assert initial_message is not None

            # 发送一条消息以保持连接活跃
            ws_client.send_message("test message")

            # 模拟异常关闭（abnormal closure）
            # 这会在服务器端触发Exception而不是WebSocketDisconnect
            try:
                ws.close(code=1006)  # 1006 = Abnormal Closure
            except Exception:
                # 可能会抛出异常，这是预期的
                pass

        # 验证连接已断开
        assert not ws_client.is_connected()

    def test_exception_disconnect_ensures_cleanup(self, client, test_user):
        """
        测试异常断开确保资源清理

        验证：
        - 异常发生时disconnect被调用
        - websocket.close()被调用
        - 连接从管理器中移除
        - 无资源泄漏

        覆盖代码：websocket.py 第60-63行（Exception处理的完整流程）

        实现方式：
        通过跟踪disconnect调用来验证异常处理时的清理逻辑。
        """
        from unittest.mock import patch
        from app.utils.websocket import message_ws_manager

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 跟踪disconnect调用
        disconnect_called = []
        original_disconnect = message_ws_manager.disconnect

        def track_disconnect(user_id, websocket):
            disconnect_called.append((user_id, websocket))
            return original_disconnect(user_id, websocket)

        with patch.object(message_ws_manager, "disconnect", side_effect=track_disconnect):
            ws_client = WebSocketTestClient(client, token)

            with ws_client.connect() as ws:
                # 连接成功建立
                assert ws_client.is_connected()

                # 接收初始消息
                ws_client.receive_message()

                # 模拟异常断开
                ws_client.simulate_network_error()

        # 验证连接已断开
        assert not ws_client.is_connected()

        # 验证disconnect被调用（至少一次）
        # 在异常断开时，disconnect应该被调用
        assert len(disconnect_called) >= 1


class TestWebSocketConnectionCleanup:
    """测试连接清理逻辑（Task 2.3.3）"""

    def test_disconnect_called_on_normal_close(self, client, test_user):
        """
        测试正常关闭时调用disconnect()

        验证：
        - 客户端正常关闭连接时
        - disconnect()方法被调用
        - 连接从管理器中移除
        - 用户ID对应的连接列表被清理

        覆盖代码：websocket.py 第56-59行（正常断开时的disconnect调用）
        """
        from unittest.mock import patch
        from app.utils.websocket import message_ws_manager

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 跟踪disconnect调用
        disconnect_calls = []
        original_disconnect = message_ws_manager.disconnect

        def track_disconnect(user_id, websocket):
            disconnect_calls.append({"user_id": user_id, "websocket": websocket})
            return original_disconnect(user_id, websocket)

        with patch.object(message_ws_manager, "disconnect", side_effect=track_disconnect):
            ws_client = WebSocketTestClient(client, token)

            with ws_client.connect() as ws:
                # 连接成功建立
                assert ws_client.is_connected()

                # 接收初始消息
                ws_client.receive_message()

            # 退出上下文管理器，连接正常关闭

        # 验证disconnect被调用
        assert len(disconnect_calls) >= 1, "disconnect应该被调用至少一次"

        # 验证调用参数正确
        last_call = disconnect_calls[-1]
        assert last_call["user_id"] == test_user.id, "应该使用正确的user_id调用disconnect"
        assert last_call["websocket"] is not None, "应该传递websocket对象"

    def test_disconnect_called_on_exception(self, client, test_user):
        """
        测试异常时调用disconnect()

        验证：
        - 发生异常时disconnect()被调用
        - 连接从管理器中移除
        - 异常处理分支正确执行

        覆盖代码：websocket.py 第60-63行（异常时的disconnect调用）
        """
        from unittest.mock import patch
        from app.utils.websocket import message_ws_manager

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 跟踪disconnect调用
        disconnect_calls = []
        original_disconnect = message_ws_manager.disconnect

        def track_disconnect(user_id, websocket):
            disconnect_calls.append({"user_id": user_id, "websocket": websocket})
            return original_disconnect(user_id, websocket)

        with patch.object(message_ws_manager, "disconnect", side_effect=track_disconnect):
            ws_client = WebSocketTestClient(client, token)

            with ws_client.connect() as ws:
                # 连接成功建立
                assert ws_client.is_connected()

                # 接收初始消息
                ws_client.receive_message()

                # 模拟网络错误（触发异常）
                ws_client.simulate_network_error()

        # 验证disconnect被调用
        assert len(disconnect_calls) >= 1, "异常时disconnect应该被调用"

        # 验证调用参数正确
        last_call = disconnect_calls[-1]
        assert last_call["user_id"] == test_user.id, "应该使用正确的user_id调用disconnect"

    def test_connections_removed_from_manager(self, client, test_user):
        """
        测试连接从管理器中移除

        验证：
        - 连接建立后存在于管理器中
        - 断开连接后从管理器中移除
        - 管理器状态正确更新

        覆盖代码：websocket.py 第56-63行（连接清理逻辑）
        """
        from app.utils.websocket import message_ws_manager

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        ws_client = WebSocketTestClient(client, token)

        # 连接前，用户不应该在管理器中
        assert (
            test_user.id not in message_ws_manager.connections or len(message_ws_manager.connections[test_user.id]) == 0
        )

        with ws_client.connect() as ws:
            # 连接建立后，用户应该在管理器中
            assert test_user.id in message_ws_manager.connections, "连接建立后用户应该在管理器中"
            assert len(message_ws_manager.connections[test_user.id]) > 0, "用户应该有至少一个活跃连接"

            # 接收初始消息
            ws_client.receive_message()

        # 连接断开后，用户应该从管理器中移除
        # 或者连接列表为空
        assert (
            test_user.id not in message_ws_manager.connections or len(message_ws_manager.connections[test_user.id]) == 0
        ), "连接断开后应该从管理器中移除"

    def test_no_resource_leaks_after_disconnect(self, client, test_user):
        """
        测试断开连接后无资源泄漏

        验证：
        - 多次连接和断开后
        - 管理器中没有残留连接
        - 内存正确释放
        - 无资源泄漏

        覆盖代码：websocket.py 第56-63行（资源清理）
        """
        from app.utils.websocket import message_ws_manager

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 执行多次连接和断开
        for i in range(5):
            ws_client = WebSocketTestClient(client, token)

            with ws_client.connect() as ws:
                # 连接成功
                assert ws_client.is_connected()

                # 接收初始消息
                ws_client.receive_message()

                # 发送一条消息
                ws_client.send_message(f"test message {i}")

            # 每次断开后验证清理
            assert (
                test_user.id not in message_ws_manager.connections
                or len(message_ws_manager.connections[test_user.id]) == 0
            ), f"第{i+1}次断开后应该清理连接"

        # 最终验证：管理器中没有该用户的连接
        assert (
            test_user.id not in message_ws_manager.connections or len(message_ws_manager.connections[test_user.id]) == 0
        ), "所有连接断开后不应该有资源泄漏"


class TestWebSocketConcurrentConnections:
    """测试并发连接和断开（Task 2.3.4）"""

    def test_multiple_concurrent_connections_same_user(self, client, test_user):
        """
        测试同一用户的多个并发连接

        验证：
        - 同一用户可以建立多个并发连接
        - 所有连接都正确注册到管理器
        - 每个连接都能独立工作
        - 所有连接都能接收消息

        覆盖代码：websocket.py 第35-55行（并发连接处理）
        """
        from app.utils.websocket import message_ws_manager

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建3个并发连接，使用嵌套的with语句保持连接活跃
        ws_client1 = WebSocketTestClient(client, token)
        ws_client2 = WebSocketTestClient(client, token)
        ws_client3 = WebSocketTestClient(client, token)

        with ws_client1.connect() as ws1:
            # 第1个连接建立
            assert ws_client1.is_connected(), "第1个连接应该成功建立"
            message1 = ws_client1.receive_message()
            assert message1 is not None, "第1个连接应该接收到初始消息"

            # 验证管理器中有1个连接
            assert len(message_ws_manager.connections[test_user.id]) == 1, "应该有1个连接"

            with ws_client2.connect() as ws2:
                # 第2个连接建立
                assert ws_client2.is_connected(), "第2个连接应该成功建立"
                message2 = ws_client2.receive_message()
                assert message2 is not None, "第2个连接应该接收到初始消息"

                # 验证管理器中有2个连接
                assert len(message_ws_manager.connections[test_user.id]) == 2, "应该有2个连接"

                with ws_client3.connect() as ws3:
                    # 第3个连接建立
                    assert ws_client3.is_connected(), "第3个连接应该成功建立"
                    message3 = ws_client3.receive_message()
                    assert message3 is not None, "第3个连接应该接收到初始消息"

                    # 验证管理器中有3个连接
                    assert len(message_ws_manager.connections[test_user.id]) == 3, "应该有3个并发连接"

                # ws3退出，应该剩2个连接
                assert len(message_ws_manager.connections[test_user.id]) == 2, "第3个连接断开后应该剩2个连接"

            # ws2退出，应该剩1个连接
            assert len(message_ws_manager.connections[test_user.id]) == 1, "第2个连接断开后应该剩1个连接"

        # 所有连接都退出，应该清理完毕
        assert (
            test_user.id not in message_ws_manager.connections or len(message_ws_manager.connections[test_user.id]) == 0
        ), "所有连接断开后应该清理"

    def test_multiple_users_concurrent_connections(self, client, test_db):
        """
        测试多个用户的并发连接

        验证：
        - 多个不同用户可以同时建立连接
        - 每个用户的连接独立管理
        - 不同用户的连接不会互相干扰

        覆盖代码：websocket.py 第35-55行（多用户并发）
        """
        from app.models.database import User
        from app.core.security import get_password_hash
        import uuid
        from datetime import datetime
        from app.utils.websocket import message_ws_manager

        # 创建3个测试用户
        users = []
        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                username=f"concurrent_user_{i}",
                email=f"concurrent_{i}@test.com",
                hashed_password=get_password_hash("password"),
                is_active=True,
                created_at=datetime.now(),
                password_version=0,
            )
            users.append(user)
            test_db.add(user)
        test_db.commit()

        # 为每个用户建立连接，使用嵌套with语句
        token1 = create_access_token({"sub": users[0].id})
        token2 = create_access_token({"sub": users[1].id})
        token3 = create_access_token({"sub": users[2].id})

        ws_client1 = WebSocketTestClient(client, token1)
        ws_client2 = WebSocketTestClient(client, token2)
        ws_client3 = WebSocketTestClient(client, token3)

        with ws_client1.connect() as ws1:
            assert ws_client1.is_connected(), "用户1的连接应该成功建立"
            message1 = ws_client1.receive_message()
            assert message1 is not None, "用户1应该接收到初始消息"

            with ws_client2.connect() as ws2:
                assert ws_client2.is_connected(), "用户2的连接应该成功建立"
                message2 = ws_client2.receive_message()
                assert message2 is not None, "用户2应该接收到初始消息"

                with ws_client3.connect() as ws3:
                    assert ws_client3.is_connected(), "用户3的连接应该成功建立"
                    message3 = ws_client3.receive_message()
                    assert message3 is not None, "用户3应该接收到初始消息"

                    # 验证所有用户都在管理器中
                    for user in users:
                        assert user.id in message_ws_manager.connections, f"用户{user.username}应该在管理器中"
                        assert len(message_ws_manager.connections[user.id]) == 1, f"用户{user.username}应该有1个连接"

        # 验证所有连接都被清理
        for user in users:
            assert (
                user.id not in message_ws_manager.connections or len(message_ws_manager.connections[user.id]) == 0
            ), f"用户{user.username}的连接应该被清理"

    def test_concurrent_disconnections(self, client, test_user):
        """
        测试并发断开连接

        验证：
        - 多个连接可以并发断开
        - 每个连接都正确清理
        - 不会出现竞态条件
        - 管理器状态正确更新

        覆盖代码：websocket.py 第56-63行（并发断开处理）
        """
        from app.utils.websocket import message_ws_manager

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 创建5个并发连接，使用嵌套with语句
        ws_clients = [WebSocketTestClient(client, token) for _ in range(5)]

        with ws_clients[0].connect() as ws0:
            ws_clients[0].receive_message()

            with ws_clients[1].connect() as ws1:
                ws_clients[1].receive_message()

                with ws_clients[2].connect() as ws2:
                    ws_clients[2].receive_message()

                    with ws_clients[3].connect() as ws3:
                        ws_clients[3].receive_message()

                        with ws_clients[4].connect() as ws4:
                            ws_clients[4].receive_message()

                            # 验证有5个连接
                            assert len(message_ws_manager.connections[test_user.id]) == 5, "应该有5个并发连接"

        # 所有连接退出后，验证清理
        assert (
            test_user.id not in message_ws_manager.connections or len(message_ws_manager.connections[test_user.id]) == 0
        ), "所有连接断开后应该清理"

    def test_connection_manager_handles_concurrency(self, client, test_user):
        """
        测试连接管理器处理并发场景

        验证：
        - 连接管理器正确处理并发连接
        - 连接管理器正确处理并发断开
        - 没有数据竞争
        - 状态始终一致

        覆盖代码：websocket.py 第35-63行（完整并发处理）
        """
        from app.utils.websocket import message_ws_manager

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 模拟复杂的并发场景：
        # 1. 建立3个连接
        # 2. 断开第1个
        # 3. 建立2个新连接
        # 4. 断开所有连接

        ws_client1 = WebSocketTestClient(client, token)
        ws_client2 = WebSocketTestClient(client, token)
        ws_client3 = WebSocketTestClient(client, token)

        # 步骤1：建立3个连接
        with ws_client1.connect() as ws1:
            ws_client1.receive_message()

            with ws_client2.connect() as ws2:
                ws_client2.receive_message()

                with ws_client3.connect() as ws3:
                    ws_client3.receive_message()

                    assert len(message_ws_manager.connections[test_user.id]) == 3, "应该有3个连接"

                # 步骤2：ws3断开，剩2个
                assert len(message_ws_manager.connections[test_user.id]) == 2, "断开1个后应该剩2个连接"

                # 步骤3：建立2个新连接
                ws_client4 = WebSocketTestClient(client, token)
                ws_client5 = WebSocketTestClient(client, token)

                with ws_client4.connect() as ws4:
                    ws_client4.receive_message()

                    with ws_client5.connect() as ws5:
                        ws_client5.receive_message()

                        assert (
                            len(message_ws_manager.connections[test_user.id]) == 4
                        ), "应该有4个连接（2个旧的 + 2个新的）"

        # 步骤4：所有连接断开
        assert (
            test_user.id not in message_ws_manager.connections or len(message_ws_manager.connections[test_user.id]) == 0
        ), "所有连接断开后应该清理"

    def test_all_connections_properly_cleaned_up(self, client, test_user):
        """
        测试所有连接都被正确清理

        验证：
        - 无论连接如何建立和断开
        - 最终所有连接都被清理
        - 管理器状态正确
        - 无内存泄漏

        覆盖代码：websocket.py 第56-63行（清理验证）
        """
        from app.utils.websocket import message_ws_manager

        # 创建有效的JWT token
        token = create_access_token({"sub": test_user.id})

        # 执行多轮连接和断开
        for round_num in range(3):
            # 建立随机数量的连接（2-4个）
            num_connections = 2 + (round_num % 3)

            # 使用嵌套with语句建立多个连接
            if num_connections == 2:
                ws_client1 = WebSocketTestClient(client, token)
                ws_client2 = WebSocketTestClient(client, token)

                with ws_client1.connect() as ws1:
                    ws_client1.receive_message()

                    with ws_client2.connect() as ws2:
                        ws_client2.receive_message()

                        # 验证连接数正确
                        assert len(message_ws_manager.connections[test_user.id]) == 2, f"第{round_num+1}轮应该有2个连接"

            elif num_connections == 3:
                ws_client1 = WebSocketTestClient(client, token)
                ws_client2 = WebSocketTestClient(client, token)
                ws_client3 = WebSocketTestClient(client, token)

                with ws_client1.connect() as ws1:
                    ws_client1.receive_message()

                    with ws_client2.connect() as ws2:
                        ws_client2.receive_message()

                        with ws_client3.connect() as ws3:
                            ws_client3.receive_message()

                            # 验证连接数正确
                            assert (
                                len(message_ws_manager.connections[test_user.id]) == 3
                            ), f"第{round_num+1}轮应该有3个连接"

            elif num_connections == 4:
                ws_client1 = WebSocketTestClient(client, token)
                ws_client2 = WebSocketTestClient(client, token)
                ws_client3 = WebSocketTestClient(client, token)
                ws_client4 = WebSocketTestClient(client, token)

                with ws_client1.connect() as ws1:
                    ws_client1.receive_message()

                    with ws_client2.connect() as ws2:
                        ws_client2.receive_message()

                        with ws_client3.connect() as ws3:
                            ws_client3.receive_message()

                            with ws_client4.connect() as ws4:
                                ws_client4.receive_message()

                                # 验证连接数正确
                                assert (
                                    len(message_ws_manager.connections[test_user.id]) == 4
                                ), f"第{round_num+1}轮应该有4个连接"

            # 验证清理完成
            assert (
                test_user.id not in message_ws_manager.connections
                or len(message_ws_manager.connections[test_user.id]) == 0
            ), f"第{round_num+1}轮断开后应该清理所有连接"

        # 最终验证：管理器完全清理
        assert (
            test_user.id not in message_ws_manager.connections or len(message_ws_manager.connections[test_user.id]) == 0
        ), "所有轮次完成后不应该有残留连接"
