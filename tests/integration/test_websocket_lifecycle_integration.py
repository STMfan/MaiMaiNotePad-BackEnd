"""
WebSocket完整生命周期集成测试

测试WebSocket连接的完整生命周期、多用户并发、重连机制和网络异常处理。
覆盖任务 2.4.1-2.4.5。
"""

import pytest

# Mark all tests in this file as serial to avoid WebSocket connection conflicts
pytestmark = pytest.mark.serial
import asyncio
from tests.helpers.websocket_client import WebSocketTestClient
from app.core.security import create_access_token
from app.utils.websocket import message_ws_manager
from app.models.database import User
from app.core.security import get_password_hash
import uuid
from datetime import datetime

class TestWebSocketCompleteLifecycle:
    """测试完整连接生命周期（Task 2.4.1）"""

    def test_complete_connection_lifecycle(self, client, test_user):
        """
        测试WebSocket连接的完整生命周期
        
        验证：
        1. Token验证和连接建立
        2. 初始消息推送
        3. 消息接收循环
        4. 客户端消息发送
        5. 正常断开连接
        6. 资源清理
        
        覆盖代码：websocket.py 第35-63行（完整流程）
        """
        # 阶段1：Token验证和连接建立
        token = create_access_token({"sub": test_user.id})
        ws_client = WebSocketTestClient(client, token)
        
        # 验证连接前状态
        assert test_user.id not in message_ws_manager.connections or \
               len(message_ws_manager.connections[test_user.id]) == 0
        
        with ws_client.connect() as ws:
            # 阶段2：验证连接成功建立
            assert ws_client.is_connected()
            assert test_user.id in message_ws_manager.connections
            assert len(message_ws_manager.connections[test_user.id]) == 1
            
            # 阶段3：接收初始消息推送
            initial_message = ws_client.receive_message()
            assert initial_message is not None
            assert "type" in initial_message
            assert initial_message["type"] == "message_update"
            assert "unread" in initial_message
            
            # 阶段4：测试消息接收循环（发送多条消息）
            for i in range(5):
                ws_client.send_message(f"test message {i}")
                assert ws_client.is_connected()
            
            # 阶段5：验证连接仍然活跃
            assert ws_client.is_connected()
            assert test_user.id in message_ws_manager.connections
        
        # 阶段6：验证正常断开和资源清理
        assert not ws_client.is_connected()
        assert test_user.id not in message_ws_manager.connections or \
               len(message_ws_manager.connections[test_user.id]) == 0

    def test_lifecycle_with_immediate_disconnect(self, client, test_user):
        """
        测试连接后立即断开的生命周期
        
        验证：
        - 连接建立
        - 接收初始消息
        - 立即断开
        - 资源正确清理
        """
        token = create_access_token({"sub": test_user.id})
        ws_client = WebSocketTestClient(client, token)
        
        with ws_client.connect() as ws:
            assert ws_client.is_connected()
            initial_message = ws_client.receive_message()
            assert initial_message is not None
            # 立即断开（退出上下文）
        
        # 验证清理
        assert not ws_client.is_connected()
        assert test_user.id not in message_ws_manager.connections or \
               len(message_ws_manager.connections[test_user.id]) == 0

    def test_lifecycle_with_long_running_connection(self, client, test_user):
        """
        测试长时间运行的连接生命周期
        
        验证：
        - 连接可以长时间保持
        - 多次消息交互
        - 连接状态稳定
        """
        token = create_access_token({"sub": test_user.id})
        ws_client = WebSocketTestClient(client, token)
        
        with ws_client.connect() as ws:
            # 接收初始消息
            ws_client.receive_message()
            
            # 模拟长时间运行：发送多条消息
            for i in range(20):
                ws_client.send_message(f"long running message {i}")
                assert ws_client.is_connected()
            
            # 验证连接仍然稳定
            assert ws_client.is_connected()
            assert test_user.id in message_ws_manager.connections


class TestWebSocketMultiUserConcurrency:
    """测试多用户并发连接（Task 2.4.2）"""

    def test_multiple_users_simultaneous_connections(self, client, test_db):
        """
        测试多个用户同时建立连接
        
        验证：
        - 多个用户可以同时连接
        - 每个用户的连接独立管理
        - 所有用户都能接收初始消息
        - 用户间不会互相干扰
        """
        # 创建5个测试用户
        users = []
        for i in range(5):
            user = User(
                id=str(uuid.uuid4()),
                username=f"multi_user_{i}",
                email=f"multi_{i}@test.com",
                hashed_password=get_password_hash("password"),
                is_active=True,
                created_at=datetime.now(),
                password_version=0
            )
            users.append(user)
            test_db.add(user)
        test_db.commit()
        
        # 为每个用户创建token和客户端
        ws_clients = []
        for user in users:
            token = create_access_token({"sub": user.id})
            ws_client = WebSocketTestClient(client, token)
            ws_clients.append((user, ws_client))
        
        # 使用嵌套with语句建立所有连接
        with ws_clients[0][1].connect() as ws0:
            ws_clients[0][1].receive_message()
            
            with ws_clients[1][1].connect() as ws1:
                ws_clients[1][1].receive_message()
                
                with ws_clients[2][1].connect() as ws2:
                    ws_clients[2][1].receive_message()
                    
                    with ws_clients[3][1].connect() as ws3:
                        ws_clients[3][1].receive_message()
                        
                        with ws_clients[4][1].connect() as ws4:
                            ws_clients[4][1].receive_message()
                            
                            # 验证所有用户都已连接
                            for user, ws_client in ws_clients:
                                assert ws_client.is_connected()
                                assert user.id in message_ws_manager.connections
                                assert len(message_ws_manager.connections[user.id]) == 1
                            
                            # 每个用户发送消息
                            for i, (user, ws_client) in enumerate(ws_clients):
                                ws_client.send_message(f"message from user {i}")
                                assert ws_client.is_connected()
        
        # 验证所有连接都已清理
        for user, ws_client in ws_clients:
            assert not ws_client.is_connected()
            assert user.id not in message_ws_manager.connections or \
                   len(message_ws_manager.connections[user.id]) == 0

    def test_same_user_multiple_concurrent_connections(self, client, test_user):
        """
        测试同一用户的多个并发连接
        
        验证：
        - 同一用户可以建立多个连接（多设备场景）
        - 所有连接都正确注册
        - 每个连接独立工作
        """
        token = create_access_token({"sub": test_user.id})
        
        # 创建5个客户端
        ws_clients = [WebSocketTestClient(client, token) for _ in range(5)]
        
        # 建立所有连接
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
                            
                            # 验证所有连接都已建立
                            assert len(message_ws_manager.connections[test_user.id]) == 5
                            
                            # 每个连接发送消息
                            for i, ws_client in enumerate(ws_clients):
                                ws_client.send_message(f"message from connection {i}")
                                assert ws_client.is_connected()
        
        # 验证所有连接都已清理
        assert test_user.id not in message_ws_manager.connections or \
               len(message_ws_manager.connections[test_user.id]) == 0

    def test_concurrent_connections_and_disconnections(self, client, test_user):
        """
        测试并发连接和断开
        
        验证：
        - 连接和断开可以交错进行
        - 管理器正确跟踪连接数
        - 无竞态条件
        """
        token = create_access_token({"sub": test_user.id})
        
        # 场景：建立3个连接，断开第1个，再建立2个，断开所有
        ws1 = WebSocketTestClient(client, token)
        ws2 = WebSocketTestClient(client, token)
        ws3 = WebSocketTestClient(client, token)
        
        with ws1.connect():
            ws1.receive_message()
            assert len(message_ws_manager.connections[test_user.id]) == 1
            
            with ws2.connect():
                ws2.receive_message()
                assert len(message_ws_manager.connections[test_user.id]) == 2
                
                with ws3.connect():
                    ws3.receive_message()
                    assert len(message_ws_manager.connections[test_user.id]) == 3
                
                # ws3断开
                assert len(message_ws_manager.connections[test_user.id]) == 2
                
                # 建立新连接
                ws4 = WebSocketTestClient(client, token)
                ws5 = WebSocketTestClient(client, token)
                
                with ws4.connect():
                    ws4.receive_message()
                    
                    with ws5.connect():
                        ws5.receive_message()
                        assert len(message_ws_manager.connections[test_user.id]) == 4
        
        # 所有连接断开
        assert test_user.id not in message_ws_manager.connections or \
               len(message_ws_manager.connections[test_user.id]) == 0


class TestWebSocketReconnection:
    """测试连接重连机制（Task 2.4.3）"""

    def test_reconnect_after_normal_disconnect(self, client, test_user):
        """
        测试正常断开后重连
        
        验证：
        - 断开连接后可以重新连接
        - 重连后功能正常
        - 无残留状态影响
        """
        token = create_access_token({"sub": test_user.id})
        ws_client = WebSocketTestClient(client, token)
        
        # 第一次连接
        with ws_client.connect() as ws:
            message1 = ws_client.receive_message()
            assert message1 is not None
            ws_client.send_message("first connection")
        
        # 验证断开
        assert not ws_client.is_connected()
        
        # 重新连接
        ws_client2 = WebSocketTestClient(client, token)
        with ws_client2.connect() as ws:
            message2 = ws_client2.receive_message()
            assert message2 is not None
            ws_client2.send_message("second connection")
            assert ws_client2.is_connected()
        
        # 验证清理
        assert not ws_client2.is_connected()

    def test_multiple_reconnections(self, client, test_user):
        """
        测试多次重连
        
        验证：
        - 可以多次重连
        - 每次重连都正常工作
        - 无资源泄漏
        """
        token = create_access_token({"sub": test_user.id})
        
        # 执行5次连接-断开-重连循环
        for i in range(5):
            ws_client = WebSocketTestClient(client, token)
            
            with ws_client.connect() as ws:
                message = ws_client.receive_message()
                assert message is not None
                ws_client.send_message(f"reconnection {i}")
                assert ws_client.is_connected()
            
            # 验证每次断开后都清理
            assert not ws_client.is_connected()
            assert test_user.id not in message_ws_manager.connections or \
                   len(message_ws_manager.connections[test_user.id]) == 0

    def test_reconnect_after_exception_disconnect(self, client, test_user):
        """
        测试异常断开后重连
        
        验证：
        - 异常断开后可以重连
        - 重连后功能正常
        """
        token = create_access_token({"sub": test_user.id})
        ws_client = WebSocketTestClient(client, token)
        
        # 第一次连接并模拟异常
        with ws_client.connect() as ws:
            ws_client.receive_message()
            ws_client.simulate_network_error()
        
        # 验证断开
        assert not ws_client.is_connected()
        
        # 重新连接
        ws_client2 = WebSocketTestClient(client, token)
        with ws_client2.connect() as ws:
            message = ws_client2.receive_message()
            assert message is not None
            assert ws_client2.is_connected()

    def test_rapid_reconnections(self, client, test_user):
        """
        测试快速重连
        
        验证：
        - 快速连接-断开-重连不会导致问题
        - 管理器正确处理快速状态变化
        """
        token = create_access_token({"sub": test_user.id})
        
        # 快速执行10次连接-断开
        for i in range(10):
            ws_client = WebSocketTestClient(client, token)
            with ws_client.connect() as ws:
                ws_client.receive_message()
                # 立即断开
            
            # 验证清理
            assert test_user.id not in message_ws_manager.connections or \
                   len(message_ws_manager.connections[test_user.id]) == 0


class TestWebSocketNetworkExceptions:
    """测试网络异常处理（Task 2.4.4）"""

    def test_network_error_during_connection(self, client, test_user):
        """
        测试连接期间的网络错误
        
        验证：
        - 网络错误被正确捕获
        - 连接被正确清理
        - 不会抛出未捕获的异常
        """
        token = create_access_token({"sub": test_user.id})
        ws_client = WebSocketTestClient(client, token)
        
        with ws_client.connect() as ws:
            ws_client.receive_message()
            
            # 模拟网络错误
            ws_client.simulate_network_error()
        
        # 验证清理
        assert not ws_client.is_connected()

    def test_abnormal_closure_handling(self, client, test_user):
        """
        测试异常关闭处理
        
        验证：
        - 异常关闭（code 1006）被正确处理
        - 资源被清理
        """
        token = create_access_token({"sub": test_user.id})
        ws_client = WebSocketTestClient(client, token)
        
        with ws_client.connect() as ws:
            ws_client.receive_message()
            
            # 模拟异常关闭
            try:
                ws.close(code=1006)  # Abnormal Closure
            except Exception:
                pass
        
        # 验证清理
        assert not ws_client.is_connected()

    def test_exception_during_message_receive(self, client, test_user):
        """
        测试消息接收时的异常
        
        验证：
        - 接收消息时的异常被捕获
        - 连接被正确清理
        """
        from unittest.mock import patch
        
        token = create_access_token({"sub": test_user.id})
        ws_client = WebSocketTestClient(client, token)
        
        with ws_client.connect() as ws:
            ws_client.receive_message()
            
            # 发送消息后模拟错误
            ws_client.send_message("test")
            ws_client.simulate_network_error()
        
        # 验证清理
        assert not ws_client.is_connected()

    def test_multiple_network_errors(self, client, test_user):
        """
        测试多次网络错误
        
        验证：
        - 多次网络错误都被正确处理
        - 每次都正确清理
        - 可以在错误后重连
        """
        token = create_access_token({"sub": test_user.id})
        
        # 执行3次网络错误场景
        for i in range(3):
            ws_client = WebSocketTestClient(client, token)
            
            with ws_client.connect() as ws:
                ws_client.receive_message()
                ws_client.send_message(f"message {i}")
                
                # 模拟网络错误
                ws_client.simulate_network_error()
            
            # 验证清理
            assert not ws_client.is_connected()
            assert test_user.id not in message_ws_manager.connections or \
                   len(message_ws_manager.connections[test_user.id]) == 0

    def test_exception_cleanup_ensures_disconnect(self, client, test_user):
        """
        测试异常时确保调用disconnect
        
        验证：
        - 异常发生时disconnect被调用
        - 连接从管理器中移除
        """
        from unittest.mock import patch
        
        token = create_access_token({"sub": test_user.id})
        
        disconnect_called = []
        original_disconnect = message_ws_manager.disconnect
        
        def track_disconnect(user_id, websocket):
            disconnect_called.append((user_id, websocket))
            return original_disconnect(user_id, websocket)
        
        with patch.object(message_ws_manager, 'disconnect', side_effect=track_disconnect):
            ws_client = WebSocketTestClient(client, token)
            
            with ws_client.connect() as ws:
                ws_client.receive_message()
                ws_client.simulate_network_error()
        
        # 验证disconnect被调用
        assert len(disconnect_called) >= 1
        assert disconnect_called[-1][0] == test_user.id
