"""
WebSocket 管理器模块

提供 WebSocket 连接管理和消息推送功能。
"""

from collections.abc import Iterable

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder

from app.core.database import get_db_context
from app.core.logging import app_logger
from app.models.database import Message


class MessageWebSocketManager:
    """
    消息 WebSocket 管理器

    管理用户的 WebSocket 连接，支持消息推送和广播功能。
    每个用户可以有多个并发连接（例如多个浏览器标签页）。

    Attributes:
        connections: 用户ID到WebSocket连接列表的映射

    Example:
        >>> manager = MessageWebSocketManager()
        >>> await manager.connect("user123", websocket)
        >>> await manager.send_message_update("user123")
        >>> manager.disconnect("user123", websocket)
    """

    def __init__(self) -> None:
        """初始化 WebSocket 管理器"""
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """
        建立 WebSocket 连接

        接受新的 WebSocket 连接并将其添加到用户的连接列表中。

        Args:
            user_id: 用户ID
            websocket: WebSocket 连接对象

        Example:
            >>> await manager.connect("user123", websocket)
        """
        await websocket.accept()
        key = str(user_id)
        if key not in self.connections:
            self.connections[key] = []
        self.connections[key].append(websocket)
        app_logger.info(f"WebSocket connected: user_id={key}, count={len(self.connections[key])}")

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """
        断开 WebSocket 连接

        从用户的连接列表中移除指定的 WebSocket 连接。
        如果用户没有其他连接，则从连接字典中移除该用户。

        Args:
            user_id: 用户ID
            websocket: WebSocket 连接对象

        Example:
            >>> manager.disconnect("user123", websocket)
        """
        key = str(user_id)
        conns = self.connections.get(key)
        if not conns:
            return
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.connections.pop(key, None)
        app_logger.info(f"WebSocket disconnected: user_id={key}, remaining={len(self.connections.get(key, []))}")

    def get_active_connections_count(self) -> int:
        """
        获取当前活动连接总数

        返回所有用户的活动 WebSocket 连接总数。

        Returns:
            int: 活动连接总数

        Example:
            >>> count = manager.get_active_connections_count()
            >>> print(f"Active connections: {count}")
        """
        return sum(len(conns) for conns in self.connections.values())

    async def send_message_update(self, user_id: str) -> None:
        """
        向指定用户发送消息更新通知

        查询用户的未读消息数和最新消息，并通过 WebSocket 推送给用户的所有连接。
        如果发送失败，会自动断开该连接。

        Args:
            user_id: 用户ID

        Example:
            >>> await manager.send_message_update("user123")
        """
        key = str(user_id)
        connections = self.connections.get(key)
        if not connections:
            return

        with get_db_context() as session:
            unread_count = (
                session.query(Message).filter(Message.recipient_id == key, Message.is_read.is_(False)).count()
            )
            latest = (
                session.query(Message).filter(Message.recipient_id == key).order_by(Message.created_at.desc()).first()
            )

            payload = {
                "type": "message_update",
                "unread": unread_count,
            }
            if latest:
                payload["last_message"] = latest.to_dict()

        encoded_payload = jsonable_encoder(payload)

        for ws in list(connections):
            try:
                await ws.send_json(encoded_payload)
            except Exception as exc:  # noqa: BLE001
                app_logger.warning(f"Send WebSocket message failed: user_id={key}, error={exc}")
                self.disconnect(key, ws)

    async def broadcast_user_update(self, user_ids: Iterable[str]) -> None:
        """
        向多个用户广播消息更新

        批量向多个用户发送消息更新通知。
        会自动去重用户ID列表。

        Args:
            user_ids: 用户ID的可迭代对象

        Example:
            >>> await manager.broadcast_user_update(["user123", "user456", "user789"])
        """
        unique_ids = {str(uid) for uid in user_ids if uid}
        for uid in unique_ids:
            await self.send_message_update(uid)


# 创建全局 WebSocket 管理器实例
message_ws_manager = MessageWebSocketManager()
