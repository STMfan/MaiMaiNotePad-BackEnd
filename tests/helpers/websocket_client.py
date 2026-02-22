"""
WebSocket测试客户端模块

提供用于测试WebSocket连接的客户端类，支持token认证、消息收发和错误模拟。
"""

from typing import Optional, Dict, Any, Union, List
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession
from contextlib import contextmanager
from enum import Enum
import time
import logging
import json
from collections import deque

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型枚举"""

    JSON = "json"
    TEXT = "text"
    BINARY = "binary"


class ConnectionState(Enum):
    """WebSocket连接状态枚举"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class WebSocketTestClient:
    """
    WebSocket测试客户端

    用于模拟WebSocket客户端连接，支持：
    - Token认证
    - 消息收发
    - 连接生命周期管理
    - 网络错误模拟

    Note:
        此类使用FastAPI的TestClient，因此所有方法都是同步的。
        在实际的WebSocket端点中使用async/await，但测试客户端是同步的。

    Example:
        >>> client = WebSocketTestClient(test_client, token)
        >>> with client.connect() as ws:
        ...     message = client.receive_message()
        ...     client.send_message("test")
    """

    def __init__(
        self,
        test_client: TestClient,
        token: str,
        connection_timeout: float = 5.0,
        max_retries: int = 3,
        message_timeout: float = 5.0,
        enable_message_queue: bool = False,
    ):
        """
        初始化WebSocket测试客户端

        Args:
            test_client: FastAPI TestClient实例
            token: JWT认证令牌
            connection_timeout: 连接超时时间（秒），默认5秒
            max_retries: 最大重试次数，默认3次
            message_timeout: 消息接收超时时间（秒），默认5秒
            enable_message_queue: 是否启用消息队列，默认False
        """
        self.test_client = test_client
        self.token = token
        self.websocket: Optional[WebSocketTestSession] = None
        self._url = f"/api/ws/{token}"
        self._state = ConnectionState.DISCONNECTED
        self._connection_timeout = connection_timeout
        self._max_retries = max_retries
        self._retry_count = 0
        self._last_error: Optional[Exception] = None
        self._connection_start_time: Optional[float] = None

        # 消息收发相关
        self._message_timeout = message_timeout
        self._enable_message_queue = enable_message_queue
        self._message_queue: deque = deque()
        self._sent_messages: List[Dict[str, Any]] = []
        self._received_messages: List[Dict[str, Any]] = []

    @contextmanager
    def connect(self):
        """
        建立WebSocket连接（上下文管理器）

        使用with语句自动管理连接生命周期：
        - 进入时建立连接
        - 退出时自动断开连接

        Yields:
            WebSocketTestSession: WebSocket连接对象

        Example:
            >>> with client.connect() as ws:
            ...     # 使用连接
            ...     pass
        """
        self._state = ConnectionState.CONNECTING
        self._connection_start_time = time.time()

        try:
            with self.test_client.websocket_connect(self._url) as ws:
                self.websocket = ws
                self._state = ConnectionState.CONNECTED
                self._retry_count = 0
                self._last_error = None
                logger.info(f"WebSocket connected successfully to {self._url}")
                yield ws
        except Exception as e:
            self._state = ConnectionState.ERROR
            self._last_error = e
            logger.error(f"WebSocket connection failed: {e}")
            raise
        finally:
            self.websocket = None
            self._state = ConnectionState.DISCONNECTED
            self._connection_start_time = None

    def connect_with_retry(self) -> bool:
        """
        带重试机制的连接方法

        尝试建立连接，失败时自动重试，直到达到最大重试次数。

        Returns:
            bool: 连接是否成功

        Example:
            >>> if client.connect_with_retry():
            ...     print("Connected successfully")
        """
        self._retry_count = 0

        while self._retry_count < self._max_retries:
            try:
                self._state = ConnectionState.CONNECTING
                self._connection_start_time = time.time()

                # 尝试建立连接
                self.websocket = self.test_client.websocket_connect(self._url).__enter__()
                self._state = ConnectionState.CONNECTED
                self._last_error = None
                logger.info(f"WebSocket connected on attempt {self._retry_count + 1}")
                return True

            except Exception as e:
                self._retry_count += 1
                self._state = ConnectionState.ERROR
                self._last_error = e
                logger.warning(f"Connection attempt {self._retry_count} failed: {e}")

                if self._retry_count < self._max_retries:
                    # 等待一段时间后重试（指数退避）
                    wait_time = min(2**self._retry_count, 10)
                    time.sleep(wait_time)

        self._state = ConnectionState.DISCONNECTED
        logger.error(f"Failed to connect after {self._max_retries} attempts")
        return False

    def get_connection_state(self) -> ConnectionState:
        """
        获取当前连接状态

        Returns:
            ConnectionState: 当前连接状态

        Example:
            >>> state = client.get_connection_state()
            >>> if state == ConnectionState.CONNECTED:
            ...     print("Connected")
        """
        return self._state

    def is_connected(self) -> bool:
        """
        检查是否已连接

        Returns:
            bool: 是否处于已连接状态

        Example:
            >>> if client.is_connected():
            ...     client.send_message("Hello")
        """
        return self._state == ConnectionState.CONNECTED and self.websocket is not None

    def get_connection_duration(self) -> Optional[float]:
        """
        获取连接持续时间

        Returns:
            Optional[float]: 连接持续时间（秒），如果未连接则返回None

        Example:
            >>> duration = client.get_connection_duration()
            >>> if duration:
            ...     print(f"Connected for {duration:.2f} seconds")
        """
        if self._connection_start_time and self._state == ConnectionState.CONNECTED:
            return time.time() - self._connection_start_time
        return None

    def check_connection_health(self) -> Dict[str, Any]:
        """
        检查连接健康状态

        Returns:
            Dict[str, Any]: 包含连接健康信息的字典
                - state: 连接状态
                - is_connected: 是否已连接
                - duration: 连接持续时间（秒）
                - retry_count: 重试次数
                - last_error: 最后一次错误信息

        Example:
            >>> health = client.check_connection_health()
            >>> print(f"State: {health['state']}, Duration: {health['duration']}")
        """
        return {
            "state": self._state.value,
            "is_connected": self.is_connected(),
            "duration": self.get_connection_duration(),
            "retry_count": self._retry_count,
            "last_error": str(self._last_error) if self._last_error else None,
            "connection_timeout": self._connection_timeout,
            "max_retries": self._max_retries,
        }

    def reset_connection_state(self) -> None:
        """
        重置连接状态

        清除错误信息和重试计数，用于重新开始连接尝试。

        Example:
            >>> client.reset_connection_state()
            >>> client.connect_with_retry()
        """
        self._retry_count = 0
        self._last_error = None
        if self._state != ConnectionState.CONNECTED:
            self._state = ConnectionState.DISCONNECTED
        logger.info("Connection state reset")

    def receive_message(
        self, timeout: Optional[float] = None, message_type: MessageType = MessageType.JSON
    ) -> Union[Dict[str, Any], str, bytes, None]:
        """
        接收WebSocket消息（支持超时和多种消息类型）

        Args:
            timeout: 接收超时时间（秒），None表示使用默认超时
            message_type: 期望的消息类型（JSON、文本或二进制）

        Returns:
            Union[Dict[str, Any], str, bytes, None]: 接收到的消息，超时返回None

        Raises:
            RuntimeError: 如果连接未建立
            ValueError: 如果消息格式无效

        Example:
            >>> # 接收JSON消息
            >>> message = client.receive_message()
            >>> print(message["type"])
            >>>
            >>> # 接收文本消息，设置超时
            >>> text = client.receive_message(timeout=3.0, message_type=MessageType.TEXT)
            >>>
            >>> # 接收二进制消息
            >>> data = client.receive_message(message_type=MessageType.BINARY)
        """
        if not self.websocket:
            raise RuntimeError("WebSocket connection not established. Use connect() first.")

        timeout = timeout or self._message_timeout
        start_time = time.time()

        try:
            # 如果启用了消息队列，先检查队列
            if self._enable_message_queue and len(self._message_queue) > 0:
                message = self._message_queue.popleft()
                self._received_messages.append(
                    {"type": message_type.value, "data": message, "timestamp": time.time(), "from_queue": True}
                )
                return message

            # 根据消息类型接收
            if message_type == MessageType.JSON:
                message = self.websocket.receive_json()
            elif message_type == MessageType.TEXT:
                message = self.websocket.receive_text()
            elif message_type == MessageType.BINARY:
                message = self.websocket.receive_bytes()
            else:
                raise ValueError(f"Unsupported message type: {message_type}")

            # 记录接收的消息
            self._received_messages.append(
                {"type": message_type.value, "data": message, "timestamp": time.time(), "from_queue": False}
            )

            logger.debug(f"Received {message_type.value} message: {message}")
            return message

        except TimeoutError:
            elapsed = time.time() - start_time
            logger.warning(f"Message receive timeout after {elapsed:.2f}s")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON message: {e}")
            raise ValueError(f"Invalid JSON message: {e}")
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            raise

    def receive_message_with_validation(
        self, expected_fields: List[str], timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        接收并验证JSON消息包含期望的字段

        Args:
            expected_fields: 期望的字段列表
            timeout: 接收超时时间（秒）

        Returns:
            Optional[Dict[str, Any]]: 验证通过的消息，失败返回None

        Example:
            >>> message = client.receive_message_with_validation(["type", "data"])
            >>> if message:
            ...     print("Valid message received")
        """
        message = self.receive_message(timeout=timeout, message_type=MessageType.JSON)

        if message is None:
            logger.warning("No message received within timeout")
            return None

        if not isinstance(message, dict):
            logger.error(f"Expected dict message, got {type(message)}")
            return None

        # 验证必需字段
        missing_fields = [field for field in expected_fields if field not in message]
        if missing_fields:
            logger.error(f"Message missing required fields: {missing_fields}")
            return None

        logger.debug(f"Message validation passed: {expected_fields}")
        return message

    def try_receive_message(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """
        尝试接收消息（非阻塞，快速超时）

        Args:
            timeout: 超时时间（秒），默认0.1秒

        Returns:
            Optional[Dict[str, Any]]: 接收到的消息，无消息返回None

        Example:
            >>> message = client.try_receive_message()
            >>> if message:
            ...     print("Got message")
            ... else:
            ...     print("No message available")
        """
        return self.receive_message(timeout=timeout, message_type=MessageType.JSON)

    def send_message(
        self, message: Union[str, Dict[str, Any], bytes], message_type: Optional[MessageType] = None
    ) -> bool:
        """
        发送WebSocket消息（支持多种消息类型）

        Args:
            message: 要发送的消息（字符串、字典或字节）
            message_type: 消息类型，None表示自动检测

        Returns:
            bool: 发送是否成功

        Raises:
            RuntimeError: 如果连接未建立

        Example:
            >>> # 发送文本消息
            >>> client.send_message("Hello")
            >>>
            >>> # 发送JSON消息
            >>> client.send_message({"type": "ping", "data": "test"})
            >>>
            >>> # 发送二进制消息
            >>> client.send_message(b"binary data", message_type=MessageType.BINARY)
        """
        if not self.websocket:
            raise RuntimeError("WebSocket connection not established. Use connect() first.")

        try:
            # 自动检测消息类型
            if message_type is None:
                if isinstance(message, dict):
                    message_type = MessageType.JSON
                elif isinstance(message, bytes):
                    message_type = MessageType.BINARY
                else:
                    message_type = MessageType.TEXT

            # 根据消息类型发送
            if message_type == MessageType.JSON:
                if isinstance(message, dict):
                    self.websocket.send_json(message)
                else:
                    # 尝试将字符串解析为JSON
                    json_data = json.loads(message) if isinstance(message, str) else message
                    self.websocket.send_json(json_data)
            elif message_type == MessageType.TEXT:
                text_message = message if isinstance(message, str) else str(message)
                self.websocket.send_text(text_message)
            elif message_type == MessageType.BINARY:
                binary_message = message if isinstance(message, bytes) else message.encode()
                self.websocket.send_bytes(binary_message)
            else:
                raise ValueError(f"Unsupported message type: {message_type}")

            # 记录发送的消息
            self._sent_messages.append({"type": message_type.value, "data": message, "timestamp": time.time()})

            logger.debug(f"Sent {message_type.value} message: {message}")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"Failed to encode JSON message: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def send_json_message(self, data: Dict[str, Any]) -> bool:
        """
        发送JSON消息（便捷方法）

        Args:
            data: JSON数据字典

        Returns:
            bool: 发送是否成功

        Example:
            >>> client.send_json_message({"type": "ping", "timestamp": time.time()})
        """
        return self.send_message(data, message_type=MessageType.JSON)

    def send_text_message(self, text: str) -> bool:
        """
        发送文本消息（便捷方法）

        Args:
            text: 文本内容

        Returns:
            bool: 发送是否成功

        Example:
            >>> client.send_text_message("Hello, WebSocket!")
        """
        return self.send_message(text, message_type=MessageType.TEXT)

    def send_binary_message(self, data: bytes) -> bool:
        """
        发送二进制消息（便捷方法）

        Args:
            data: 二进制数据

        Returns:
            bool: 发送是否成功

        Example:
            >>> client.send_binary_message(b"\\x00\\x01\\x02\\x03")
        """
        return self.send_message(data, message_type=MessageType.BINARY)

    def get_sent_messages(self) -> List[Dict[str, Any]]:
        """
        获取已发送的消息历史

        Returns:
            List[Dict[str, Any]]: 发送的消息列表

        Example:
            >>> messages = client.get_sent_messages()
            >>> print(f"Sent {len(messages)} messages")
        """
        return self._sent_messages.copy()

    def get_received_messages(self) -> List[Dict[str, Any]]:
        """
        获取已接收的消息历史

        Returns:
            List[Dict[str, Any]]: 接收的消息列表

        Example:
            >>> messages = client.get_received_messages()
            >>> for msg in messages:
            ...     print(f"{msg['type']}: {msg['data']}")
        """
        return self._received_messages.copy()

    def clear_message_history(self) -> None:
        """
        清除消息历史记录

        Example:
            >>> client.clear_message_history()
        """
        self._sent_messages.clear()
        self._received_messages.clear()
        self._message_queue.clear()
        logger.debug("Message history cleared")

    def get_message_statistics(self) -> Dict[str, Any]:
        """
        获取消息统计信息

        Returns:
            Dict[str, Any]: 包含消息统计的字典
                - sent_count: 发送消息数量
                - received_count: 接收消息数量
                - queue_size: 队列中的消息数量
                - sent_by_type: 按类型统计的发送消息
                - received_by_type: 按类型统计的接收消息

        Example:
            >>> stats = client.get_message_statistics()
            >>> print(f"Sent: {stats['sent_count']}, Received: {stats['received_count']}")
        """
        sent_by_type = {}
        for msg in self._sent_messages:
            msg_type = msg["type"]
            sent_by_type[msg_type] = sent_by_type.get(msg_type, 0) + 1

        received_by_type = {}
        for msg in self._received_messages:
            msg_type = msg["type"]
            received_by_type[msg_type] = received_by_type.get(msg_type, 0) + 1

        return {
            "sent_count": len(self._sent_messages),
            "received_count": len(self._received_messages),
            "queue_size": len(self._message_queue),
            "sent_by_type": sent_by_type,
            "received_by_type": received_by_type,
            "message_timeout": self._message_timeout,
            "queue_enabled": self._enable_message_queue,
        }

    def disconnect(self) -> None:
        """
        主动断开WebSocket连接

        Example:
            >>> client.disconnect()
        """
        if self.websocket:
            try:
                self.websocket.close()
                logger.info("WebSocket disconnected")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.websocket = None
                self._state = ConnectionState.DISCONNECTED
                self._connection_start_time = None

    def simulate_network_error(self) -> None:
        """
        模拟网络错误

        通过强制关闭连接来模拟网络中断。
        这会触发服务器端的异常处理逻辑。

        Example:
            >>> client.simulate_network_error()
        """
        if self.websocket:
            # 强制关闭连接，不发送关闭帧
            # 这会在服务器端触发异常
            try:
                self.websocket.close(code=1006)  # 1006 = Abnormal Closure
                logger.info("Simulated network error (abnormal closure)")
            except Exception as e:
                logger.warning(f"Error during network error simulation: {e}")
            finally:
                self.websocket = None
                self._state = ConnectionState.ERROR
                self._connection_start_time = None

    def simulate_connection_timeout(self, timeout: float = 0.1) -> bool:
        """
        模拟连接超时

        尝试使用极短的超时时间建立连接，模拟连接超时场景。

        Args:
            timeout: 超时时间（秒），默认0.1秒

        Returns:
            bool: 是否成功模拟超时（True表示确实超时了）

        Example:
            >>> if client.simulate_connection_timeout():
            ...     print("Connection timeout simulated successfully")
        """
        original_timeout = self._connection_timeout
        self._connection_timeout = timeout

        try:
            self._state = ConnectionState.CONNECTING
            self._connection_start_time = time.time()

            # 尝试建立连接，使用极短的超时
            self.websocket = self.test_client.websocket_connect(self._url).__enter__()
            self._state = ConnectionState.CONNECTED

            # 如果连接成功，说明没有超时
            logger.info("Connection succeeded (timeout not triggered)")
            return False

        except Exception as e:
            # 连接失败，模拟超时成功
            self._state = ConnectionState.ERROR
            self._last_error = e
            logger.info(f"Connection timeout simulated: {e}")
            return True

        finally:
            self._connection_timeout = original_timeout

    def simulate_send_failure(self, error_type: str = "network") -> None:
        """
        模拟消息发送失败

        通过在发送前关闭连接来模拟发送失败。

        Args:
            error_type: 错误类型，可选值：
                - "network": 网络错误（关闭连接）
                - "encoding": 编码错误（发送无效数据）
                - "timeout": 超时错误

        Raises:
            RuntimeError: 如果连接未建立
            Exception: 根据error_type抛出相应的异常

        Example:
            >>> try:
            ...     client.simulate_send_failure("network")
            ... except Exception as e:
            ...     print(f"Send failed as expected: {e}")
        """
        if not self.websocket:
            raise RuntimeError("WebSocket connection not established. Use connect() first.")

        if error_type == "network":
            # 关闭连接后尝试发送
            self.websocket.close(code=1006)
            self.websocket = None
            self._state = ConnectionState.ERROR
            logger.info("Simulated send failure: network error")
            raise ConnectionError("Network connection lost")

        elif error_type == "encoding":
            # 尝试发送无法编码的数据
            logger.info("Simulated send failure: encoding error")
            raise ValueError("Failed to encode message")

        elif error_type == "timeout":
            # 模拟发送超时
            logger.info("Simulated send failure: timeout")
            raise TimeoutError("Message send timeout")

        else:
            raise ValueError(f"Unknown error type: {error_type}")

    def simulate_receive_failure(self, error_type: str = "timeout") -> None:
        """
        模拟消息接收失败

        Args:
            error_type: 错误类型，可选值：
                - "timeout": 接收超时
                - "network": 网络错误（关闭连接）
                - "decode": 解码错误
                - "empty": 空消息

        Raises:
            RuntimeError: 如果连接未建立
            Exception: 根据error_type抛出相应的异常

        Example:
            >>> try:
            ...     client.simulate_receive_failure("timeout")
            ... except TimeoutError:
            ...     print("Receive timeout as expected")
        """
        if not self.websocket:
            raise RuntimeError("WebSocket connection not established. Use connect() first.")

        if error_type == "timeout":
            # 模拟接收超时
            logger.info("Simulated receive failure: timeout")
            raise TimeoutError("Message receive timeout")

        elif error_type == "network":
            # 关闭连接
            self.websocket.close(code=1006)
            self.websocket = None
            self._state = ConnectionState.ERROR
            logger.info("Simulated receive failure: network error")
            raise ConnectionError("Network connection lost during receive")

        elif error_type == "decode":
            # 模拟解码错误
            logger.info("Simulated receive failure: decode error")
            raise json.JSONDecodeError("Invalid JSON", "", 0)

        elif error_type == "empty":
            # 模拟空消息
            logger.info("Simulated receive failure: empty message")
            raise ValueError("Received empty message")

        else:
            raise ValueError(f"Unknown error type: {error_type}")

    def simulate_auth_failure(self, failure_type: str = "invalid_token") -> Dict[str, Any]:
        """
        模拟认证失败

        尝试使用无效的token建立连接，测试认证失败场景。

        Args:
            failure_type: 失败类型，可选值：
                - "invalid_token": 无效的token格式
                - "expired_token": 过期的token
                - "no_user_id": token中缺少user_id
                - "malformed": 格式错误的token

        Returns:
            Dict[str, Any]: 包含认证失败信息的字典
                - success: 是否成功模拟失败（False）
                - error_type: 错误类型
                - error_message: 错误消息
                - close_code: WebSocket关闭代码（如果有）

        Example:
            >>> result = client.simulate_auth_failure("invalid_token")
            >>> print(f"Auth failed with code: {result['close_code']}")
        """
        # 保存原始token
        original_token = self.token
        original_url = self._url

        # 根据失败类型设置无效token
        if failure_type == "invalid_token":
            invalid_token = "invalid_token_string"
        elif failure_type == "expired_token":
            invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjB9.invalid"
        elif failure_type == "no_user_id":
            # 创建一个没有user_id的token（仅用于测试）
            invalid_token = "token_without_user_id"
        elif failure_type == "malformed":
            invalid_token = "malformed.token"
        else:
            raise ValueError(f"Unknown failure type: {failure_type}")

        # 更新token和URL
        self.token = invalid_token
        self._url = f"/api/ws/{invalid_token}"

        result = {"success": False, "error_type": failure_type, "error_message": None, "close_code": None}

        try:
            # 尝试建立连接
            self._state = ConnectionState.CONNECTING
            with self.test_client.websocket_connect(self._url) as ws:
                self.websocket = ws
                self._state = ConnectionState.CONNECTED
                # 如果连接成功，说明认证没有失败
                result["error_message"] = "Authentication succeeded unexpectedly"
                logger.warning(f"Auth failure simulation failed: connection succeeded with {failure_type}")

        except Exception as e:
            # 认证失败，符合预期
            result["success"] = True
            result["error_message"] = str(e)

            # 尝试提取关闭代码
            if hasattr(e, "code"):
                result["close_code"] = e.code
            elif "1008" in str(e):
                result["close_code"] = 1008

            self._state = ConnectionState.ERROR
            self._last_error = e
            logger.info(f"Auth failure simulated successfully: {failure_type}, error: {e}")

        finally:
            # 恢复原始token和URL
            self.token = original_token
            self._url = original_url
            self.websocket = None
            self._state = ConnectionState.DISCONNECTED

        return result

    def simulate_server_close(self, close_code: int = 1000, reason: str = "Normal closure") -> None:
        """
        模拟服务器主动关闭连接

        Args:
            close_code: WebSocket关闭代码，常用值：
                - 1000: 正常关闭
                - 1001: 端点离开
                - 1002: 协议错误
                - 1003: 不支持的数据类型
                - 1006: 异常关闭（无关闭帧）
                - 1008: 策略违规
                - 1011: 服务器错误
            reason: 关闭原因描述

        Raises:
            RuntimeError: 如果连接未建立

        Example:
            >>> # 模拟正常关闭
            >>> client.simulate_server_close(1000, "Server shutdown")
            >>>
            >>> # 模拟策略违规关闭
            >>> client.simulate_server_close(1008, "Policy violation")
        """
        if not self.websocket:
            raise RuntimeError("WebSocket connection not established. Use connect() first.")

        try:
            self.websocket.close(code=close_code, reason=reason)
            logger.info(f"Simulated server close: code={close_code}, reason={reason}")
        except Exception as e:
            logger.warning(f"Error during server close simulation: {e}")
        finally:
            self.websocket = None
            self._state = ConnectionState.DISCONNECTED
            self._connection_start_time = None

    def simulate_intermittent_connection(
        self, disconnect_after: float = 1.0, reconnect_delay: float = 0.5
    ) -> Dict[str, Any]:
        """
        模拟间歇性连接（连接-断开-重连）

        Args:
            disconnect_after: 连接后多久断开（秒）
            reconnect_delay: 断开后多久重连（秒）

        Returns:
            Dict[str, Any]: 包含模拟结果的字典
                - initial_connected: 初始连接是否成功
                - disconnected: 是否成功断开
                - reconnected: 是否成功重连
                - total_duration: 总耗时（秒）

        Example:
            >>> result = client.simulate_intermittent_connection(1.0, 0.5)
            >>> print(f"Reconnected: {result['reconnected']}")
        """
        start_time = time.time()
        result = {"initial_connected": False, "disconnected": False, "reconnected": False, "total_duration": 0.0}

        try:
            # 初始连接
            with self.connect() as ws:
                result["initial_connected"] = True
                logger.info("Initial connection established")

                # 等待指定时间
                time.sleep(disconnect_after)

                # 模拟断开
                self.simulate_network_error()
                result["disconnected"] = True
                logger.info("Connection disconnected")

            # 等待后重连
            time.sleep(reconnect_delay)

            # 尝试重连
            result["reconnected"] = self.connect_with_retry()
            if result["reconnected"]:
                logger.info("Reconnection successful")
                self.disconnect()
            else:
                logger.warning("Reconnection failed")

        except Exception as e:
            logger.error(f"Error during intermittent connection simulation: {e}")

        finally:
            result["total_duration"] = time.time() - start_time

        return result

    def get_exception_simulation_capabilities(self) -> Dict[str, List[str]]:
        """
        获取支持的异常模拟类型

        Returns:
            Dict[str, List[str]]: 各类异常模拟方法支持的类型

        Example:
            >>> capabilities = client.get_exception_simulation_capabilities()
            >>> print(f"Send failure types: {capabilities['send_failure']}")
        """
        return {
            "connection_timeout": ["可配置超时时间"],
            "send_failure": ["network", "encoding", "timeout"],
            "receive_failure": ["timeout", "network", "decode", "empty"],
            "auth_failure": ["invalid_token", "expired_token", "no_user_id", "malformed"],
            "server_close": [
                "1000-正常关闭",
                "1001-端点离开",
                "1002-协议错误",
                "1003-不支持的数据",
                "1006-异常关闭",
                "1008-策略违规",
                "1011-服务器错误",
            ],
            "intermittent_connection": ["可配置断开和重连时间"],
        }
