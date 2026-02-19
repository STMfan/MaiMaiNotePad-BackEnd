"""
WebSocket 处理模块

提供 WebSocket 端点用于实时消息推送。
"""

from fastapi import WebSocket, WebSocketDisconnect

from app.core.security import get_user_from_token
from app.utils.websocket import message_ws_manager


async def message_websocket_endpoint(websocket: WebSocket, token: str) -> None:
    """
    消息 WebSocket 端点
    
    处理用户的 WebSocket 连接，用于实时消息推送。
    客户端通过 JWT token 进行认证。
    
    Args:
        websocket: WebSocket 连接对象
        token: JWT 认证令牌
    
    流程:
        1. 验证 JWT token
        2. 建立 WebSocket 连接
        3. 发送初始消息更新
        4. 保持连接并接收客户端消息
        5. 断开连接时清理资源
    
    Example:
        客户端连接: ws://localhost:9278/api/ws/{jwt_token}
    """
    # 验证 token
    payload = get_user_from_token(token)
    if not payload:
        await websocket.close(code=1008)
        return

    # 获取用户 ID
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008)
        return

    # 建立连接
    await message_ws_manager.connect(str(user_id), websocket)
    
    # 发送初始消息更新
    await message_ws_manager.send_message_update(str(user_id))

    # 保持连接
    try:
        while True:
            # 接收客户端消息（保持连接活跃）
            await websocket.receive_text()
    except WebSocketDisconnect:
        # 正常断开连接
        message_ws_manager.disconnect(str(user_id), websocket)
    except Exception:
        # 异常断开连接
        message_ws_manager.disconnect(str(user_id), websocket)
        await websocket.close()
