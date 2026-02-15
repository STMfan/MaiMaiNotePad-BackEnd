from typing import Dict, List, Iterable

from fastapi import WebSocket

from database_models import sqlite_db_manager, Message
from logging_config import app_logger


class MessageWebSocketManager:
    def __init__(self) -> None:
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        key = str(user_id)
        if key not in self.connections:
            self.connections[key] = []
        self.connections[key].append(websocket)
        app_logger.info(
            f"WebSocket connected: user_id={key}, count={len(self.connections[key])}"
        )

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        key = str(user_id)
        conns = self.connections.get(key)
        if not conns:
            return
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.connections.pop(key, None)
        app_logger.info(
            f"WebSocket disconnected: user_id={key}, remaining={len(self.connections.get(key, []))}"
        )

    async def send_message_update(self, user_id: str) -> None:
        key = str(user_id)
        connections = self.connections.get(key)
        if not connections:
            return

        with sqlite_db_manager.get_session() as session:
            unread_count = (
                session.query(Message)
                .filter(Message.recipient_id == key, Message.is_read.is_(False))
                .count()
            )
            latest = (
                session.query(Message)
                .filter(Message.recipient_id == key)
                .order_by(Message.created_at.desc())
                .first()
            )

            payload = {
                "type": "message_update",
                "unread": unread_count,
            }
            if latest:
                payload["last_message"] = latest.to_dict()

        for ws in list(connections):
            try:
                await ws.send_json(payload)
            except Exception as exc:  # noqa: BLE001
                app_logger.warning(
                    f"Send WebSocket message failed: user_id={key}, error={exc}"
                )
                self.disconnect(key, ws)

    async def broadcast_user_update(self, user_ids: Iterable[str]) -> None:
        unique_ids = {str(uid) for uid in user_ids if uid}
        for uid in unique_ids:
            await self.send_message_update(uid)


message_ws_manager = MessageWebSocketManager()

