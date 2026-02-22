"""
SQLAlchemy 数据库模型

包含应用的所有数据模型定义。
"""

from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Index
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base

if TYPE_CHECKING:
    # 仅用于类型检查，避免循环导入
    pass


class User(Base):
    """用户模型"""

    __tablename__ = "users"
    __allow_unmapped__ = True  # 允许非 Mapped[] 类型的注解

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_moderator = Column(Boolean, default=False)
    is_super_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_failed_login = Column(DateTime, nullable=True)

    is_muted = Column(Boolean, default=False)
    muted_until = Column(DateTime, nullable=True)

    ban_reason = Column(String, nullable=True)
    mute_reason = Column(String, nullable=True)

    # 头像字段
    avatar_path = Column(String, nullable=True)
    avatar_updated_at = Column(DateTime, nullable=True)

    # 密码版本号，用于令牌失效控制
    password_version = Column(Integer, default=0)

    # 索引
    __table_args__ = (
        Index("idx_user_username", "username"),
        Index("idx_user_email", "email"),
        Index("idx_user_is_active", "is_active"),
        Index("idx_user_is_admin", "is_admin"),
        Index("idx_user_is_moderator", "is_moderator"),
        Index("idx_user_is_super_admin", "is_super_admin"),
    )

    # 关联关系
    uploaded_knowledge_bases: List["KnowledgeBase"] = relationship(
        "KnowledgeBase",
        back_populates="uploader",
        primaryjoin="User.id==KnowledgeBase.uploader_id",
        foreign_keys="KnowledgeBase.uploader_id",
    )
    uploaded_persona_cards: List["PersonaCard"] = relationship(
        "PersonaCard",
        back_populates="uploader",
        primaryjoin="User.id==PersonaCard.uploader_id",
        foreign_keys="PersonaCard.uploader_id",
    )
    received_messages: List["Message"] = relationship(
        "Message",
        foreign_keys="Message.recipient_id",
        back_populates="recipient",
        primaryjoin="User.id==Message.recipient_id",
    )
    sent_messages: List["Message"] = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender",
        primaryjoin="User.id==Message.sender_id",
    )
    star_records: List["StarRecord"] = relationship(
        "StarRecord",
        back_populates="user",
        primaryjoin="User.id==StarRecord.user_id",
        foreign_keys="StarRecord.user_id",
    )


class KnowledgeBase(Base):
    """知识库模型"""

    __tablename__ = "knowledge_bases"
    __allow_unmapped__ = True  # 允许非 Mapped[] 类型的注解

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    uploader_id = Column(String, nullable=False)
    copyright_owner = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # 逗号分隔
    star_count = Column(Integer, default=0)
    downloads = Column(Integer, default=0)
    base_path = Column(Text, default="[]")
    is_public = Column(Boolean, default=False)
    is_pending = Column(Boolean, default=True)
    rejection_reason = Column(Text, nullable=True)
    version = Column(String, default="1.0")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_kb_uploader_id", "uploader_id"),
        Index("idx_kb_is_public", "is_public"),
        Index("idx_kb_is_pending", "is_pending"),
        Index("idx_kb_star_count", "star_count"),
        Index("idx_kb_created_at", "created_at"),
        Index("idx_kb_updated_at", "updated_at"),
    )

    # 关联关系
    uploader: "User" = relationship(
        "User",
        back_populates="uploaded_knowledge_bases",
        primaryjoin="KnowledgeBase.uploader_id==User.id",
        foreign_keys=[uploader_id],
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "uploader_id": self.uploader_id,
            "author": self.uploader.username if self.uploader else None,
            "author_id": self.uploader_id,
            "copyright_owner": self.copyright_owner,
            "content": self.content,
            "tags": self.tags,
            "star_count": self.star_count,
            "downloads": self.downloads,
            "base_path": self.base_path,
            "is_public": self.is_public,
            "is_pending": self.is_pending,
            "rejection_reason": self.rejection_reason,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class KnowledgeBaseFile(Base):
    """知识库文件模型"""

    __tablename__ = "knowledge_base_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_base_id = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_kb_file_knowledge_base_id", "knowledge_base_id"),
        Index("idx_kb_file_file_type", "file_type"),
        Index("idx_kb_file_file_size", "file_size"),
        Index("idx_kb_file_created_at", "created_at"),
        Index("idx_kb_file_updated_at", "updated_at"),
    )


class PersonaCard(Base):
    """人设卡模型"""

    __tablename__ = "persona_cards"
    __allow_unmapped__ = True  # 允许非 Mapped[] 类型的注解

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    uploader_id = Column(String, nullable=False)
    copyright_owner = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # 逗号分隔
    star_count = Column(Integer, default=0)
    downloads = Column(Integer, default=0)
    base_path = Column(String, nullable=False)
    is_public = Column(Boolean, default=False)
    is_pending = Column(Boolean, default=True)
    rejection_reason = Column(Text, nullable=True)
    version = Column(String, default="1.0")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_pc_uploader_id", "uploader_id"),
        Index("idx_pc_is_public", "is_public"),
        Index("idx_pc_is_pending", "is_pending"),
        Index("idx_pc_star_count", "star_count"),
        Index("idx_pc_created_at", "created_at"),
        Index("idx_pc_updated_at", "updated_at"),
    )

    # 关联关系
    uploader: "User" = relationship(
        "User",
        back_populates="uploaded_persona_cards",
        primaryjoin="PersonaCard.uploader_id==User.id",
        foreign_keys=[uploader_id],
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "uploader_id": self.uploader_id,
            "author": self.uploader.username if self.uploader else None,
            "author_id": self.uploader_id,
            "copyright_owner": self.copyright_owner,
            "content": self.content,
            "tags": self.tags,
            "star_count": self.star_count,
            "downloads": self.downloads,
            "base_path": self.base_path,
            "is_public": self.is_public,
            "is_pending": self.is_pending,
            "rejection_reason": self.rejection_reason,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PersonaCardFile(Base):
    """人设卡文件模型"""

    __tablename__ = "persona_card_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    persona_card_id = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_pc_file_persona_card_id", "persona_card_id"),
        Index("idx_pc_file_file_type", "file_type"),
        Index("idx_pc_file_file_size", "file_size"),
        Index("idx_pc_file_created_at", "created_at"),
        Index("idx_pc_file_updated_at", "updated_at"),
    )


class Message(Base):
    """消息模型"""

    __tablename__ = "messages"
    __allow_unmapped__ = True  # 允许非 Mapped[] 类型的注解

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id = Column(String, nullable=False)
    sender_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    message_type = Column(String, default="direct")
    broadcast_scope = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_message_recipient_id", "recipient_id"),
        Index("idx_message_sender_id", "sender_id"),
        Index("idx_message_is_read", "is_read"),
        Index("idx_message_created_at", "created_at"),
        Index("idx_message_recipient_read", "recipient_id", "is_read"),
    )

    # 关联关系
    recipient: "User" = relationship(
        "User",
        foreign_keys=[recipient_id],
        back_populates="received_messages",
        primaryjoin="Message.recipient_id==User.id",
    )
    sender: "User" = relationship(
        "User",
        foreign_keys=[sender_id],
        back_populates="sent_messages",
        primaryjoin="Message.sender_id==User.id",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "recipient_id": self.recipient_id,
            "sender_id": self.sender_id,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "message_type": self.message_type,
            "broadcast_scope": self.broadcast_scope,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StarRecord(Base):
    """收藏记录模型"""

    __tablename__ = "star_records"
    __allow_unmapped__ = True  # 允许非 Mapped[] 类型的注解

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    target_type = Column(String, nullable=False)  # "knowledge" 或 "persona"
    created_at = Column(DateTime, default=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_star_user_id", "user_id"),
        Index("idx_star_target_id", "target_id"),
        Index("idx_star_target_type", "target_type"),
        Index("idx_star_created_at", "created_at"),
        Index("idx_star_user_target", "user_id", "target_id", "target_type"),
    )

    # 关联关系
    user: "User" = relationship(
        "User",
        back_populates="star_records",
        primaryjoin="StarRecord.user_id==User.id",
        foreign_keys=[user_id],
    )


class EmailVerification(Base):
    """邮箱验证码模型"""

    __tablename__ = "email_verifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, nullable=False)
    code = Column(String, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)

    # 索引
    __table_args__ = (
        Index("idx_email_verification_email", "email"),
        Index("idx_email_verification_code", "code"),
        Index("idx_email_verification_expires", "expires_at"),
    )


class UploadRecord(Base):
    """上传记录模型"""

    __tablename__ = "upload_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    uploader_id = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    target_type = Column(String, nullable=False)  # "knowledge" 或 "persona"
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="pending")  # "pending"、"approved"、"rejected"
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_upload_record_uploader_id", "uploader_id"),
        Index("idx_upload_record_target_id", "target_id"),
        Index("idx_upload_record_target_type", "target_type"),
        Index("idx_upload_record_status", "status"),
        Index("idx_upload_record_created_at", "created_at"),
    )


class DownloadRecord(Base):
    """下载记录模型"""

    __tablename__ = "download_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    target_id = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_download_record_target_id", "target_id"),
        Index("idx_download_record_target_type", "target_type"),
        Index("idx_download_record_created_at", "created_at"),
    )


class Comment(Base):
    """评论模型"""

    __tablename__ = "comments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    parent_id = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False)
    like_count = Column(Integer, default=0)
    dislike_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_comment_target", "target_id", "target_type"),
        Index("idx_comment_user_id", "user_id"),
        Index("idx_comment_parent_id", "parent_id"),
        Index("idx_comment_created_at", "created_at"),
    )


class CommentReaction(Base):
    """评论反应模型"""

    __tablename__ = "comment_reactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    comment_id = Column(String, nullable=False)
    reaction_type = Column(String, nullable=False)  # "like" 或 "dislike"
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_comment_reaction_user_comment", "user_id", "comment_id"),
        Index("idx_comment_reaction_comment_id", "comment_id"),
    )
