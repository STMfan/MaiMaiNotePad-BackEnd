"""
消息服务模块

提供消息相关的业务逻辑，包括：
- 消息增删改查
- 广播消息功能
- 消息已读/未读状态管理
"""

import re
from datetime import datetime
from typing import List, Optional, Set, Dict, Any
from sqlalchemy.orm import Session

from app.models.database import Message, User


class MessageService:
    """消息服务类"""

    def __init__(self, db: Session):
        """
        初始化消息服务。

        Args:
            db: SQLAlchemy 数据库会话
        """
        self.db = db

    def get_message_by_id(self, message_id: str) -> Optional[Message]:
        """
        根据 ID 获取消息。

        Args:
            message_id: 消息 ID

        Returns:
            找到返回消息对象，否则返回 None
        """
        return self.db.query(Message).filter(Message.id == message_id).first()

    def get_user_messages(self, user_id: str, page: int = 1, page_size: int = 20) -> List[Message]:
        """
        获取用户收到的消息列表。

        Args:
            user_id: 用户 ID
            page: 页码（从 1 开始）
            page_size: 每页数量

        Returns:
            消息对象列表
        """
        offset = (page - 1) * page_size
        return (
            self.db.query(Message)
            .filter(Message.recipient_id == user_id)
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    def get_conversation_messages(
        self, user_id: str, other_user_id: str, page: int = 1, page_size: int = 20
    ) -> List[Message]:
        """
        获取两个用户之间的对话消息。

        Args:
            user_id: 当前用户 ID
            other_user_id: 对方用户 ID
            page: 页码（从 1 开始）
            page_size: 每页数量

        Returns:
            消息对象列表
        """
        offset = (page - 1) * page_size
        return (
            self.db.query(Message)
            .filter(
                ((Message.sender_id == user_id) & (Message.recipient_id == other_user_id))
                | ((Message.sender_id == other_user_id) & (Message.recipient_id == user_id))
            )
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    def get_user_messages_by_type(
        self, user_id: str, message_type: str, page: int = 1, page_size: int = 20
    ) -> List[Message]:
        """
        按类型获取用户消息。

        Args:
            user_id: 用户 ID
            message_type: 消息类型（如 'direct'、'announcement'）
            page: 页码（从 1 开始）
            page_size: 每页数量

        Returns:
            消息对象列表
        """
        offset = (page - 1) * page_size
        return (
            self.db.query(Message)
            .filter(Message.recipient_id == user_id, Message.message_type == message_type)
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    def get_all_users(self) -> List[User]:
        """
        获取所有用户。

        Returns:
            用户对象列表
        """
        return self.db.query(User).all()

    def get_users_by_ids(self, user_ids: List[str]) -> List[User]:
        """
        根据 ID 列表获取用户。

        Args:
            user_ids: 用户 ID 列表

        Returns:
            用户对象列表
        """
        return self.db.query(User).filter(User.id.in_(user_ids)).all()

    def generate_summary(self, content: str) -> str:
        """
        从内容生成摘要。

        Args:
            content: 消息内容

        Returns:
            生成的摘要（最多 150 字符）
        """
        # 移除 HTML 标签
        text = re.sub(r"<[^>]+>", "", content)
        # 移除多余空白
        text = " ".join(text.split())

        if len(text) > 150:
            truncated = text[:150]
            # 尝试在标点处截断
            last_punctuation = max(
                truncated.rfind("。"),
                truncated.rfind("！"),
                truncated.rfind("？"),
                truncated.rfind("."),
                truncated.rfind("!"),
                truncated.rfind("?"),
            )
            if last_punctuation > 75:
                return truncated[: last_punctuation + 1]
            else:
                return truncated + "..."
        else:
            return text

    def create_messages(
        self,
        sender_id: str,
        recipient_ids: Set[str],
        title: str,
        content: str,
        summary: Optional[str] = None,
        message_type: str = "direct",
        broadcast_scope: Optional[str] = None,
    ) -> List[Message]:
        """
        为多个接收者创建消息。

        Args:
            sender_id: 发送者用户 ID
            recipient_ids: 接收者用户 ID 集合
            title: 消息标题
            content: 消息内容
            summary: 消息摘要（未提供则自动生成）
            message_type: 消息类型（'direct' 或 'announcement'）
            broadcast_scope: 广播范围（如 'all_users'）

        Returns:
            创建的消息对象列表
        """
        # 未提供摘要则自动生成
        if not summary and content:
            summary = self.generate_summary(content)

        # 创建消息对象
        messages = []
        for recipient_id in recipient_ids:
            message = Message(
                sender_id=sender_id,
                recipient_id=recipient_id,
                title=title,
                content=content,
                summary=summary,
                message_type=message_type,
                broadcast_scope=broadcast_scope if message_type == "announcement" else None,
                is_read=False,
                created_at=datetime.now(),
            )
            self.db.add(message)
            messages.append(message)

        # 提交所有消息
        self.db.commit()

        # 刷新以获取 ID
        for message in messages:
            self.db.refresh(message)

        return messages

    def mark_message_read(self, message_id: str, user_id: str) -> bool:
        """
        标记消息为已读。

        Args:
            message_id: 消息 ID
            user_id: 用户 ID（必须是接收者）

        Returns:
            成功返回 True，否则返回 False
        """
        message = self.get_message_by_id(message_id)
        if not message:
            return False

        # 验证用户是接收者
        if str(message.recipient_id) != str(user_id):
            return False

        message.is_read = True
        self.db.commit()
        return True

    def delete_message(self, message_id: str, user_id: str) -> bool:
        """
        删除单条消息。

        Args:
            message_id: 消息 ID
            user_id: 用户 ID（必须是接收者）

        Returns:
            成功返回 True，否则返回 False
        """
        message = self.get_message_by_id(message_id)
        if not message:
            return False

        # 验证用户是接收者
        if str(message.recipient_id) != str(user_id):
            return False

        self.db.delete(message)
        self.db.commit()
        return True

    def delete_broadcast_messages(self, message_id: str, sender_id: str) -> int:
        """
        删除广播消息的所有副本。

        Args:
            message_id: 广播中任一消息的 ID
            sender_id: 发送者用户 ID（必须是发送者）

        Returns:
            删除的消息数量
        """
        # 获取原始消息以查找广播详情
        original_message = self.get_message_by_id(message_id)
        if not original_message:
            return 0

        # 验证用户是发送者
        if str(original_message.sender_id) != str(sender_id):
            return 0

        # 查找同一发送者、同一标题、同一时间（1 秒内）的所有消息
        messages = (
            self.db.query(Message)
            .filter(
                Message.sender_id == sender_id,
                Message.title == original_message.title,
                Message.message_type == "announcement",
                Message.broadcast_scope == "all_users",
            )
            .all()
        )

        # 按创建时间 1 秒内筛选
        target_time = original_message.created_at
        broadcast_messages = [msg for msg in messages if abs((msg.created_at - target_time).total_seconds()) < 1]

        # 删除所有广播消息
        count = 0
        for message in broadcast_messages:
            self.db.delete(message)
            count += 1

        self.db.commit()
        return count

    def update_message(
        self,
        message_id: str,
        user_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> bool:
        """
        更新单条消息。

        Args:
            message_id: 消息 ID
            user_id: 用户 ID（必须是接收者）
            title: 新标题（可选）
            content: 新内容（可选）
            summary: 新摘要（可选）

        Returns:
            成功返回 True，否则返回 False
        """
        message = self.get_message_by_id(message_id)
        if not message:
            return False

        # 验证用户是接收者
        if str(message.recipient_id) != str(user_id):
            return False

        # 更新字段
        if title:
            message.title = title
        if content:
            message.content = content
        if summary is not None:  # 允许空字符串
            message.summary = summary

        self.db.commit()
        return True

    def update_broadcast_messages(
        self,
        message_id: str,
        sender_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> int:
        """
        更新广播消息的所有副本。

        Args:
            message_id: 广播中任一消息的 ID
            sender_id: 发送者用户 ID（必须是发送者）
            title: 新标题（可选）
            content: 新内容（可选）
            summary: 新摘要（可选）

        Returns:
            更新的消息数量
        """
        # 获取原始消息以查找广播详情
        original_message = self.get_message_by_id(message_id)
        if not original_message:
            return 0

        # 验证用户是发送者
        if str(original_message.sender_id) != str(sender_id):
            return 0

        # 查找同一发送者、同一标题、同一时间（1 秒内）的所有消息
        messages = (
            self.db.query(Message)
            .filter(
                Message.sender_id == sender_id,
                Message.title == original_message.title,
                Message.message_type == "announcement",
                Message.broadcast_scope == "all_users",
            )
            .all()
        )

        # 按创建时间 1 秒内筛选
        target_time = original_message.created_at
        broadcast_messages = [msg for msg in messages if abs((msg.created_at - target_time).total_seconds()) < 1]

        # 更新所有广播消息
        count = 0
        for message in broadcast_messages:
            if title:
                message.title = title
            if content:
                message.content = content
            if summary is not None:  # 允许空字符串
                message.summary = summary
            count += 1

        self.db.commit()
        return count

    def get_broadcast_messages(self, page: int = 1, page_size: int = 20) -> List[Message]:
        """
        获取广播消息列表（按发送者、标题和时间去重）。

        Args:
            page: 页码（从 1 开始）
            page_size: 每页数量

        Returns:
            去重后的广播消息对象列表
        """
        # 获取所有公告消息
        all_messages = (
            self.db.query(Message)
            .filter(Message.message_type == "announcement", Message.broadcast_scope == "all_users")
            .order_by(Message.created_at.desc())
            .all()
        )

        # 按发送者、标题和创建时间（1 秒内）分组
        unique_messages = []
        seen = set()

        for msg in all_messages:
            # 基于发送者、标题和取整时间戳创建唯一键
            timestamp_key = int(msg.created_at.timestamp()) if msg.created_at else 0
            key = (msg.sender_id, msg.title, timestamp_key)

            if key not in seen:
                seen.add(key)
                unique_messages.append(msg)

        # 分页
        offset = (page - 1) * page_size
        return unique_messages[offset : offset + page_size]

    def get_broadcast_message_stats(self, message_id: str) -> Dict[str, Any]:
        """
        获取广播消息的统计信息。

        Args:
            message_id: 广播中任一消息的 ID

        Returns:
            包含 total_sent、total_read、total_unread 的统计字典
        """
        # 获取原始消息
        original_message = self.get_message_by_id(message_id)
        if not original_message:
            return {"total_sent": 0, "total_read": 0, "total_unread": 0}

        # 查找同一发送者、同一标题、同一时间（1 秒内）的所有消息
        messages = (
            self.db.query(Message)
            .filter(
                Message.sender_id == original_message.sender_id,
                Message.title == original_message.title,
                Message.message_type == "announcement",
                Message.broadcast_scope == "all_users",
            )
            .all()
        )

        # 按创建时间 1 秒内筛选
        target_time = original_message.created_at
        broadcast_messages = [msg for msg in messages if abs((msg.created_at - target_time).total_seconds()) < 1]

        total_sent = len(broadcast_messages)
        total_read = sum(1 for msg in broadcast_messages if msg.is_read)
        total_unread = total_sent - total_read

        return {"total_sent": total_sent, "total_read": total_read, "total_unread": total_unread}

    def count_broadcast_messages(self) -> int:
        """
        统计广播消息总数。

        Returns:
            广播消息总数
        """
        return (
            self.db.query(Message)
            .filter(Message.message_type == "announcement", Message.broadcast_scope == "all_users")
            .count()
        )
