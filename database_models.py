"""
SQLite数据库模型定义
包含知识库、人设卡、信箱等数据模型
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, create_engine, Index, and_, or_, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import text
import os
import uuid

# 创建基础模型类
Base = declarative_base()


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_moderator = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    # 账户锁定相关字段
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_failed_login = Column(DateTime, nullable=True)

    # 头像相关字段
    avatar_path = Column(String, nullable=True)  # 头像文件路径（相对路径或URL）
    avatar_updated_at = Column(DateTime, nullable=True)  # 头像最后更新时间

    # 密码版本号（用于Token失效机制）
    password_version = Column(Integer, default=0)  # 密码修改次数，每次修改密码时递增

    # 添加索引
    __table_args__ = (
        Index('idx_user_username', 'username'),
        Index('idx_user_email', 'email'),
        Index('idx_user_is_active', 'is_active'),
        Index('idx_user_is_admin', 'is_admin'),
        Index('idx_user_is_moderator', 'is_moderator'),
    )

    # 关系（通过显式主连接条件，而不是物理外键约束）
    uploaded_knowledge_bases = relationship(
        "KnowledgeBase",
        back_populates="uploader",
        primaryjoin="User.id==KnowledgeBase.uploader_id",
        foreign_keys="KnowledgeBase.uploader_id",
    )
    uploaded_persona_cards = relationship(
        "PersonaCard",
        back_populates="uploader",
        primaryjoin="User.id==PersonaCard.uploader_id",
        foreign_keys="PersonaCard.uploader_id",
    )
    received_messages = relationship(
        "Message",
        foreign_keys="Message.recipient_id",
        back_populates="recipient",
        primaryjoin="User.id==Message.recipient_id",
    )
    sent_messages = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender",
        primaryjoin="User.id==Message.sender_id",
    )
    star_records = relationship(
        "StarRecord",
        back_populates="user",
        primaryjoin="User.id==StarRecord.user_id",
        foreign_keys="StarRecord.user_id",
    )

    def __str__(self):
        return f'ID: {self.id}, Username: {self.username}, Email: {self.email}, Admin: {self.is_admin}, Moderator: {self.is_moderator}'

    def to_dict(self):
        """将用户对象转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "hashed_password": self.hashed_password,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "is_moderator": self.is_moderator,
            "created_at": self.created_at,
            "avatar_path": self.avatar_path,
            "avatar_updated_at": self.avatar_updated_at.isoformat() if self.avatar_updated_at else None,
            "password_version": self.password_version or 0
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建用户对象"""
        # 统一将邮箱转换为小写
        email = data.get("email", "")
        email_lower = email.lower() if email else ""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            username=data.get("username", ""),
            email=email_lower,
            hashed_password=data.get("hashed_password", ""),
            is_active=data.get("is_active", True),
            is_admin=data.get("is_admin", False),
            is_moderator=data.get("is_moderator", False),
            # SQLite的DateTime类型只接受 datetime 或 date 对象，这里做修改
            created_at=data.get("created_at", datetime.now())
        )

    def verify_password(self, password):
        """验证密码"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self.hashed_password)

    def update_password(self, new_password):
        """更新密码"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # 确保密码不超过72字节（bcrypt限制）
        new_password = new_password[:72]
        self.hashed_password = pwd_context.hash(new_password)
        # 增加密码版本号，使所有现有Token失效
        self.password_version = (self.password_version or 0) + 1

    def to_admin(self, highest_pwd):
        """提升用户为管理员"""
        from passlib.context import CryptContext
        import os
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        if pwd_context.verify(highest_pwd, os.getenv('HIGHEST_PASSWORD', '')):
            self.is_admin = True
            return True
        else:
            return False

    def to_moderator(self, highest_pwd):
        """提升用户为版主"""
        from passlib.context import CryptContext
        import os
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        if pwd_context.verify(highest_pwd, os.getenv('HIGHEST_PASSWORD', '')):
            self.is_moderator = True
            return True
        else:
            return False


class KnowledgeBase(Base):
    """知识库数据模型"""
    __tablename__ = "knowledge_bases"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    uploader_id = Column(String, nullable=False)
    copyright_owner = Column(String, nullable=True)
    # 直接在数据库中保存内容与标签，避免依赖外部 metadata 文件
    content = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # 逗号分隔存储
    star_count = Column(Integer, default=0)
    downloads = Column(Integer, default=0)
    base_path = Column(Text, default="[]")
    is_public = Column(Boolean, default=False)
    is_pending = Column(Boolean, default=True)
    rejection_reason = Column(Text, nullable=True)
    version = Column(String, default="1.0")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 添加索引
    __table_args__ = (
        Index('idx_kb_uploader_id', 'uploader_id'),
        Index('idx_kb_is_public', 'is_public'),
        Index('idx_kb_is_pending', 'is_pending'),
        Index('idx_kb_star_count', 'star_count'),
        Index('idx_kb_created_at', 'created_at'),
        Index('idx_kb_updated_at', 'updated_at'),
    )

    # 关系
    uploader = relationship(
        "User",
        back_populates="uploaded_knowledge_bases",
        primaryjoin="KnowledgeBase.uploader_id==User.id",
        foreign_keys=[uploader_id],
    )
    # 移除star_records关系，因为StarRecord没有正确的外键关系
    # star_records = relationship("StarRecord", back_populates="knowledge_base")

    def to_dict(self, include_files: bool = True):
        """将知识库对象转换为字典"""
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "uploader_id": self.uploader_id,
            "copyright_owner": self.copyright_owner,
            "content": self.content,
            "tags": (self.tags or "").split(",") if self.tags else [],
            "star_count": self.star_count or 0,
            "downloads": self.downloads or 0,
            "base_path": self.base_path or "[]",
            "is_public": self.is_public,
            "is_pending": self.is_pending if self.is_pending is not None else True,
            "rejection_reason": self.rejection_reason,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else datetime.now().isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else datetime.now().isoformat(),
            # 默认值
            "files": [],
            "download_url": None,
            "preview_url": None,
            "size": None,
            "author": None,
            "author_id": self.uploader_id
        }

        if include_files:
            # 获取文件列表
            try:
                # 通过全局变量访问数据库管理器
                from database_models import sqlite_db_manager
                files = sqlite_db_manager.get_files_by_knowledge_base_id(self.id)
                result["files"] = [{
                    "file_id": f.id,
                    "original_name": f.original_name,
                    "file_size": f.file_size or 0,
                } for f in files]
                result["size"] = sum(f.file_size or 0 for f in files)
                # 构建下载URL
                result["download_url"] = f"/api/knowledge/{self.id}/download"
            except Exception as e:
                # 如果获取文件失败，使用默认值
                pass

        return result

    def to_db_dict(self):
        """将知识库对象转换为数据库字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "uploader_id": self.uploader_id,
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
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建知识库对象"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            uploader_id=data.get("uploader_id", ""),
            copyright_owner=data.get("copyright_owner", None),
            content=data.get("content"),
            tags=",".join(data.get("tags", [])) if isinstance(
                data.get("tags"), list) else data.get("tags"),
            star_count=data.get("star_count", 0),
            base_path=data.get("base_path", "[]"),
            is_public=data.get("is_public", False),
            is_pending=data.get("is_pending", True),
            rejection_reason=data.get("rejection_reason", None),
            version=data.get("version","1.0"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get(
                "created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get(
                "updated_at") else datetime.now()
        )


class KnowledgeBaseFile(Base):
    """知识库文件数据模型"""
    __tablename__ = "knowledge_base_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_base_id = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, default=0)  # 文件大小，单位为B
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 添加索引
    __table_args__ = (
        Index('idx_kb_file_knowledge_base_id', 'knowledge_base_id'),
        Index('idx_kb_file_file_type', 'file_type'),
        Index('idx_kb_file_file_size', 'file_size'),
        Index('idx_kb_file_created_at', 'created_at'),
        Index('idx_kb_file_updated_at', 'updated_at'),
    )

    def to_dict(self):
        """将知识库文件对象转换为字典"""
        return {
            "id": self.id,
            "knowledge_base_id": self.knowledge_base_id,
            "file_name": self.file_name,
            "original_name": self.original_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size or 0,
            "created_at": self.created_at.isoformat() if self.created_at else datetime.now().isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else datetime.now().isoformat()
        }


class PersonaCardFile(Base):
    """人设卡文件数据模型"""
    __tablename__ = "persona_card_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    persona_card_id = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, default=0)  # 文件大小，单位为B
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 添加索引
    __table_args__ = (
        Index('idx_pc_file_persona_card_id', 'persona_card_id'),
        Index('idx_pc_file_file_type', 'file_type'),
        Index('idx_pc_file_file_size', 'file_size'),
        Index('idx_pc_file_created_at', 'created_at'),
        Index('idx_pc_file_updated_at', 'updated_at'),
    )

    def to_dict(self):
        """将人设卡文件对象转换为字典"""
        return {
            "id": self.id,
            "persona_card_id": self.persona_card_id,
            "file_name": self.file_name,
            "original_name": self.original_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size or 0,
            "created_at": self.created_at.isoformat() if self.created_at else datetime.now().isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else datetime.now().isoformat()
        }


class PersonaCard(Base):
    """人设卡数据模型"""
    __tablename__ = "persona_cards"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    uploader_id = Column(String, nullable=False)
    copyright_owner = Column(String, nullable=True)
    # 直接存储正文与标签，避免依赖外部 metadata 文件
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

    # 添加索引
    __table_args__ = (
        Index('idx_pc_uploader_id', 'uploader_id'),
        Index('idx_pc_is_public', 'is_public'),
        Index('idx_pc_is_pending', 'is_pending'),
        Index('idx_pc_star_count', 'star_count'),
        Index('idx_pc_created_at', 'created_at'),
        Index('idx_pc_updated_at', 'updated_at'),
    )

    # 关系
    uploader = relationship(
        "User",
        back_populates="uploaded_persona_cards",
        primaryjoin="PersonaCard.uploader_id==User.id",
        foreign_keys=[uploader_id],
    )
    # 移除star_records关系，因为StarRecord没有正确的外键关系
    # star_records = relationship("StarRecord", back_populates="persona_card")

    def to_dict(self, include_files: bool = True):
        """将人设卡对象转换为字典"""
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "uploader_id": self.uploader_id,
            "copyright_owner": self.copyright_owner,
            "content": self.content,
            "tags": (self.tags or "").split(",") if self.tags else [],
            "star_count": self.star_count or 0,
            "base_path": self.base_path,
            "is_public": self.is_public,
            "is_pending": self.is_pending if self.is_pending is not None else True,
            "rejection_reason": self.rejection_reason,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else datetime.now().isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else datetime.now().isoformat(),
            # 默认值
            "files": [],
            "downloads": self.downloads or 0,
            "download_url": None,
            "preview_url": None,
            "size": None,
            "author": None,
            "author_id": self.uploader_id,
            "stars": self.star_count or 0
        }

        if include_files:
            # 获取文件列表
            try:
                # 通过全局变量访问数据库管理器
                from database_models import sqlite_db_manager
                files = sqlite_db_manager.get_files_by_persona_card_id(self.id)
                result["files"] = [{
                    "file_id": f.id,
                    "original_name": f.original_name,
                    "file_size": f.file_size or 0,
                }for f in files]
                result["size"] = sum(f.file_size or 0 for f in files)
                # 构建下载URL
                result["download_url"] = f"/api/persona/{self.id}/download"
            except Exception as e:
                # 如果获取文件失败，使用默认值
                pass

        return result

    def to_db_dict(self):
        """将人设卡对象转换为数据库字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "uploader_id": self.uploader_id,
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
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class Message(Base):
    """信箱消息模型"""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id = Column(String, nullable=False)
    sender_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)  # 消息简介，可选
    message_type = Column(String, default="direct")  # 直接声明
    broadcast_scope = Column(String, nullable=True)  # 比如所有用户
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    # 添加索引
    __table_args__ = (
        Index('idx_message_recipient_id', 'recipient_id'),
        Index('idx_message_sender_id', 'sender_id'),
        Index('idx_message_is_read', 'is_read'),
        Index('idx_message_created_at', 'created_at'),
        Index('idx_message_recipient_read', 'recipient_id', 'is_read'),
    )

    # 关系
    recipient = relationship(
        "User",
        foreign_keys=[recipient_id],
        back_populates="received_messages",
        primaryjoin="Message.recipient_id==User.id",
    )
    sender = relationship(
        "User",
        foreign_keys=[sender_id],
        back_populates="sent_messages",
        primaryjoin="Message.sender_id==User.id",
    )

    def to_dict(self):
        """将消息对象转换为字典"""
        data = {
            "id": self.id,
            "recipient_id": self.recipient_id,
            "sender_id": self.sender_id,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,  # 添加summary字段
            "message_type": self.message_type or "direct",
            "broadcast_scope": self.broadcast_scope,
            "is_read": self.is_read or False,
            "created_at": self.created_at.isoformat() if self.created_at else datetime.now().isoformat()
        }
        return data

    def to_db_dict(self):
        """将消息对象转换为数据库字典"""
        return {
            "id": self.id,
            "recipient_id": self.recipient_id,
            "sender_id": self.sender_id,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,  # 添加summary字段
            "message_type": self.message_type or "direct",
            "broadcast_scope": self.broadcast_scope,
            "is_read": self.is_read or False,
            "created_at": self.created_at or datetime.now()
        }


class StarRecord(Base):
    """Star记录模型"""
    __tablename__ = "star_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    target_type = Column(String, nullable=False)  # "knowledge" 或 "persona"
    created_at = Column(DateTime, default=datetime.now)

    # 添加索引
    __table_args__ = (
        Index('idx_star_user_id', 'user_id'),
        Index('idx_star_target_id', 'target_id'),
        Index('idx_star_target_type', 'target_type'),
        Index('idx_star_created_at', 'created_at'),
        Index('idx_star_user_target', 'user_id', 'target_id',
              'target_type'),  # 复合索引用于检查用户是否已star某个目标
    )

    # 关系
    user = relationship(
        "User",
        back_populates="star_records",
        primaryjoin="StarRecord.user_id==User.id",
        foreign_keys=[user_id],
    )
    # 移除直接关系，因为target_id不是真正的外键
    # knowledge_base = relationship("KnowledgeBase", back_populates="star_records", foreign_keys=[target_id])
    # persona_card = relationship("PersonaCard", back_populates="star_records", foreign_keys=[target_id])

    def to_dict(self):
        """将Star记录对象转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class EmailVerification(Base):
    """邮箱验证码记录模型"""
    __tablename__ = "email_verifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, nullable=False)
    code = Column(String, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)  # 验证码过期时间

    # 添加索引
    __table_args__ = (
        Index('idx_email_verification_email', 'email'),
        Index('idx_email_verification_code', 'code'),
        Index('idx_email_verification_expires', 'expires_at'),
    )

    def to_dict(self):
        """将邮箱验证对象转换为字典"""
        return {
            "id": self.id,
            "email": self.email,
            "code": self.code,
            "is_used": self.is_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


class UploadRecord(Base):
    """上传记录模型 - 用于记录所有上传操作，防止恶意删除"""
    __tablename__ = "upload_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    uploader_id = Column(String, nullable=False)
    target_id = Column(String, nullable=False)  # 知识库或人设卡的ID
    target_type = Column(String, nullable=False)  # "knowledge" 或 "persona"
    name = Column(String, nullable=False)  # 知识库或人设卡名称
    description = Column(Text, nullable=True)  # 描述
    # "pending", "approved", "rejected"
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 添加索引
    __table_args__ = (
        Index('idx_upload_record_uploader_id', 'uploader_id'),
        Index('idx_upload_record_target_id', 'target_id'),
        Index('idx_upload_record_target_type', 'target_type'),
        Index('idx_upload_record_status', 'status'),
        Index('idx_upload_record_created_at', 'created_at'),
    )

    def to_dict(self):
        """将上传记录对象转换为字典"""
        return {
            "id": self.id,
            "uploader_id": self.uploader_id,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class SQLiteDatabaseManager:
    """SQLite数据库管理器"""

    def __init__(self, db_path: str = "./data/maimnp.db"):
        self.db_path = db_path
        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 创建数据库引擎
        self.engine = create_engine(
            f"sqlite:///{db_path}", echo=False, connect_args={"check_same_thread": False})

        # 创建会话工厂
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine)

        # 创建所有表
        Base.metadata.create_all(bind=self.engine)

        # 执行数据库迁移
        self._migrate_database()

    def _add_column_if_not_exists(self, table_name: str, column_name: str, column_definition: str):
        """为表添加列（如果不存在）"""
        try:
            inspector = inspect(self.engine)
            if table_name not in inspector.get_table_names():
                return

            existing_columns = [col['name']
                                for col in inspector.get_columns(table_name)]
            if column_name not in existing_columns:
                with self.engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"))
                # 使用日志系统记录迁移操作（静默执行，不输出到控制台）
        except Exception:
            # 数据库迁移失败时静默处理，不输出到控制台（避免启动时干扰）
            # 不抛出异常，允许应用继续运行
            pass

    def _migrate_database(self):
        """执行数据库迁移，添加缺失的列"""
        # 迁移配置：表名 -> [(列名, 列定义), ...]
        migrations = [
            ('messages', [
                ('message_type', "VARCHAR DEFAULT 'direct'"),
                ('broadcast_scope', 'VARCHAR'),
                ('summary', 'TEXT'),
            ]),
            ('knowledge_bases', [
                ('downloads', 'INTEGER DEFAULT 0'),
                ('content', 'TEXT'),
                ('tags', 'TEXT'),
            ]),
            ('persona_cards', [
                ('downloads', 'INTEGER DEFAULT 0'),
                ('content', 'TEXT'),
                ('tags', 'TEXT'),
            ]),
            ('users', [
                ('failed_login_attempts', 'INTEGER DEFAULT 0'),
                ('locked_until', 'DATETIME'),
                ('last_failed_login', 'DATETIME'),
                ('avatar_path', 'VARCHAR'),
                ('avatar_updated_at', 'DATETIME'),
                ('password_version', 'INTEGER DEFAULT 0'),
            ]),
        ]

        # 执行所有迁移
        for table_name, columns in migrations:
            for column_name, column_definition in columns:
                self._add_column_if_not_exists(
                    table_name, column_name, column_definition)

    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()

    # 知识库相关方法
    def get_all_knowledge_bases(self):
        """获取所有知识库"""
        with self.get_session() as session:
            return session.query(KnowledgeBase).all()

    def get_knowledge_base_by_id(self, kb_id: str):
        """根据ID获取知识库"""
        with self.get_session() as session:
            return session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

    def get_pending_knowledge_bases(self, page: int = 1, page_size: int = 10, name: str = None, uploader_id: str = None, sort_by: str = "created_at", sort_order: str = "desc"):
        """获取所有待审核的知识库，支持分页、搜索、按上传者筛选和排序，返回(items, total)元组"""
        with self.get_session() as session:
            # 使用 == True 查询待审核的知识库（SQLAlchemy 的 Boolean 类型应使用 Python 的 True/False）
            query = session.query(KnowledgeBase).filter(
                KnowledgeBase.is_pending == True)

            # 按名称搜索
            if name:
                query = query.filter(KnowledgeBase.name.contains(name))

            # 按上传者ID筛选
            if uploader_id:
                query = query.filter(KnowledgeBase.uploader_id == uploader_id)

            # 排序
            if sort_by == "star_count":
                order_column = KnowledgeBase.star_count
            elif sort_by == "updated_at":
                order_column = KnowledgeBase.updated_at
            else:
                order_column = KnowledgeBase.created_at

            if sort_order == "asc":
                query = query.order_by(order_column.asc())
            else:
                query = query.order_by(order_column.desc())

            # 在应用分页前计算总数
            total = query.count()

            # 分页
            offset = (page - 1) * page_size
            items = query.offset(offset).limit(page_size).all()

            return items, total

    def get_public_knowledge_bases(self, page: int = 1, page_size: int = 10, name: str = None, uploader_id: str = None, sort_by: str = "created_at", sort_order: str = "desc"):
        """获取所有公开的知识库，支持分页、搜索、按上传者筛选和排序，返回(items, total)元组"""
        with self.get_session() as session:
            query = session.query(KnowledgeBase).filter(
                KnowledgeBase.is_public == True,
                KnowledgeBase.is_pending == False  # 只显示已审核通过的内容
            )

            # 按名称搜索
            if name:
                query = query.filter(KnowledgeBase.name.contains(name))

            # 按上传者ID筛选
            if uploader_id:
                query = query.filter(KnowledgeBase.uploader_id == uploader_id)

            # 排序
            if sort_by == "star_count":
                order_column = KnowledgeBase.star_count
            elif sort_by == "updated_at":
                order_column = KnowledgeBase.updated_at
            else:
                order_column = KnowledgeBase.created_at

            if sort_order == "asc":
                query = query.order_by(order_column.asc())
            else:
                query = query.order_by(order_column.desc())

            # 在应用分页前计算总数
            total = query.count()

            # 分页
            offset = (page - 1) * page_size
            items = query.offset(offset).limit(page_size).all()

            return items, total

    def get_knowledge_bases_by_uploader(self, uploader_id: str):
        """根据上传者ID获取知识库"""
        with self.get_session() as session:
            return session.query(KnowledgeBase).filter(KnowledgeBase.uploader_id == uploader_id).all()

    def save_knowledge_base(self, kb_data: dict) -> KnowledgeBase:
        """保存知识库并返回保存后的对象"""
        try:
            with self.get_session() as session:
                # 规范化字段，避免非字符串写入SQLite
                tags_value = kb_data.get("tags")
                if isinstance(tags_value, list):
                    kb_data["tags"] = ",".join(tags_value)

                # 清理时间字段，避免将已序列化的字符串写回 DateTime 列
                created_at_value = kb_data.get("created_at")
                if isinstance(created_at_value, str):
                    kb_data.pop("created_at", None)
                updated_at_value = kb_data.get("updated_at")
                if isinstance(updated_at_value, str):
                    kb_data.pop("updated_at", None)

                kb_id = kb_data.get("id")
                kb = None
                if kb_id:
                    kb = session.query(KnowledgeBase).filter(
                        KnowledgeBase.id == kb_id).first()

                if kb:
                    # 更新现有记录
                    for key, value in kb_data.items():
                        if hasattr(kb, key):
                            setattr(kb, key, value)
                    kb.updated_at = datetime.now()
                else:
                    # 创建新记录
                    kb = KnowledgeBase(**kb_data)
                    session.add(kb)

                session.commit()
                session.refresh(kb)  # 刷新对象以获取数据库生成的值
                return kb
        except Exception as e:
            print(f"保存知识库失败: {str(e)}")
            return None

    def delete_knowledge_base(self, kb_id: str) -> bool:
        """删除知识库"""
        try:
            with self.get_session() as session:
                kb = session.query(KnowledgeBase).filter(
                    KnowledgeBase.id == kb_id).first()
                if kb:
                    session.delete(kb)
                # 同时删除相关的文件记录
                session.query(KnowledgeBaseFile).filter(
                    KnowledgeBaseFile.knowledge_base_id == kb_id).delete()
                session.commit()
                return True
        except Exception as e:
            print(f"删除知识库失败: {str(e)}")
            return False

    # KnowledgeBaseFile 相关方法
    def get_files_by_knowledge_base_id(self, knowledge_base_id: str):
        """根据知识库ID获取所有文件"""
        with self.get_session() as session:
            return session.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == knowledge_base_id).all()

    def get_knowledge_base_file_by_id(self, file_id: str):
        """根据文件ID获取知识库文件"""
        with self.get_session() as session:
            return session.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.id == file_id).first()

    def save_knowledge_base_file(self, file_data: dict) -> KnowledgeBaseFile:
        """保存知识库文件并返回保存后的对象"""
        try:
            with self.get_session() as session:
                file_id = file_data.get("id")
                kb_file = None
                if file_id:
                    kb_file = session.query(KnowledgeBaseFile).filter(
                        KnowledgeBaseFile.id == file_id).first()

                if kb_file:
                    # 更新现有记录
                    for key, value in file_data.items():
                        if hasattr(kb_file, key):
                            setattr(kb_file, key, value)
                    kb_file.updated_at = datetime.now()
                else:
                    # 创建新记录
                    kb_file = KnowledgeBaseFile(**file_data)
                    session.add(kb_file)

                session.commit()
                session.refresh(kb_file)
                return kb_file
        except Exception as e:
            print(f"保存知识库文件失败: {str(e)}")
            return None

    def delete_knowledge_base_file(self, file_id: str) -> bool:
        """删除知识库文件"""
        try:
            with self.get_session() as session:
                kb_file = session.query(KnowledgeBaseFile).filter(
                    KnowledgeBaseFile.id == file_id).first()
                if kb_file:
                    session.delete(kb_file)
                    session.commit()
                return True
        except Exception as e:
            print(f"删除知识库文件失败: {str(e)}")
            return False

    def delete_files_by_knowledge_base_id(self, knowledge_base_id: str) -> bool:
        """根据知识库ID删除所有相关文件"""
        try:
            with self.get_session() as session:
                session.query(KnowledgeBaseFile).filter(
                    KnowledgeBaseFile.knowledge_base_id == knowledge_base_id).delete()
                session.commit()
                return True
        except Exception as e:
            print(f"删除知识库文件失败: {str(e)}")
            return False

    # 人设卡相关方法
    def get_all_persona_cards(self):
        """获取所有人设卡"""
        with self.get_session() as session:
            return session.query(PersonaCard).all()

    def get_persona_card_by_id(self, pc_id: str):
        """根据ID获取人设卡"""
        with self.get_session() as session:
            return session.query(PersonaCard).filter(PersonaCard.id == pc_id).first()

    def get_pending_persona_cards(self, page: int = 1, page_size: int = 10, name: str = None, uploader_id: str = None, sort_by: str = "created_at", sort_order: str = "desc"):
        """获取所有待审核的人设卡，支持分页、搜索、按上传者筛选和排序，返回(items, total)元组"""
        with self.get_session() as session:
            # 使用 == True 查询待审核的人设卡（SQLAlchemy 的 Boolean 类型应使用 Python 的 True/False）
            query = session.query(PersonaCard).filter(
                PersonaCard.is_pending == True)

            # 按名称搜索
            if name:
                query = query.filter(PersonaCard.name.contains(name))

            # 按上传者ID筛选
            if uploader_id:
                query = query.filter(PersonaCard.uploader_id == uploader_id)

            # 排序
            if sort_by == "star_count":
                order_column = PersonaCard.star_count
            elif sort_by == "updated_at":
                order_column = PersonaCard.updated_at
            else:
                order_column = PersonaCard.created_at

            if sort_order == "asc":
                query = query.order_by(order_column.asc())
            else:
                query = query.order_by(order_column.desc())

            # 在应用分页前计算总数
            total = query.count()

            # 分页
            offset = (page - 1) * page_size
            items = query.offset(offset).limit(page_size).all()

            return items, total

    def get_public_persona_cards(self, page: int = 1, page_size: int = 19, name: str = None, uploader_id: str = None, sort_by: str = "created_at", sort_order: str = "desc"):
        """获取所有公开的人设卡，支持分页、搜索、按上传者筛选和排序，返回(items, total)元组"""
        with self.get_session() as session:
            query = session.query(PersonaCard).filter(
                PersonaCard.is_public == True,
                PersonaCard.is_pending == False  # 只显示已审核通过的内容
            )

            # 按名称搜索
            if name:
                query = query.filter(PersonaCard.name.contains(name))

            # 按上传者ID筛选
            if uploader_id:
                query = query.filter(PersonaCard.uploader_id == uploader_id)

            # 排序
            if sort_by == "star_count":
                order_column = PersonaCard.star_count
            elif sort_by == "updated_at":
                order_column = PersonaCard.updated_at
            else:
                order_column = PersonaCard.created_at

            if sort_order == "asc":
                query = query.order_by(order_column.asc())
            else:
                query = query.order_by(order_column.desc())

            # 在应用分页前计算总数
            total = query.count()

            # 分页
            offset = (page - 1) * page_size
            items = query.offset(offset).limit(page_size).all()

            return items, total

    def get_persona_cards_by_uploader(self, uploader_id: str):
        """根据上传者ID获取人设卡"""
        with self.get_session() as session:
            return session.query(PersonaCard).filter(PersonaCard.uploader_id == uploader_id).all()

    def save_persona_card(self, pc_data: dict) -> PersonaCard:
        """保存人设卡并返回保存后的对象"""
        try:
            with self.get_session() as session:
                tags_value = pc_data.get("tags")
                if isinstance(tags_value, list):
                    pc_data["tags"] = ",".join(tags_value)

                pc_id = pc_data.get("id")
                pc = session.query(PersonaCard).filter(
                    PersonaCard.id == pc_id).first()

                if pc:
                    # 更新现有记录
                    for key, value in pc_data.items():
                        if hasattr(pc, key):
                            # 处理日期时间字段，将其转换为datetime对象
                            if key in ['created_at', 'updated_at'] and isinstance(value, str):
                                try:
                                    setattr(pc, key, datetime.fromisoformat(value.replace('Z', '+00:00')))
                                except ValueError:
                                    # 如果格式不正确，使用当前时间
                                    setattr(pc, key, datetime.now())
                            else:
                                setattr(pc, key, value)
                    pc.updated_at = datetime.now()
                else:
                    # 创建新记录，处理日期时间字段
                    pc_data_for_db = pc_data.copy()
                    for key in ['created_at', 'updated_at']:
                        if key in pc_data_for_db and isinstance(pc_data_for_db[key], str):
                            try:
                                pc_data_for_db[key] = datetime.fromisoformat(pc_data_for_db[key].replace('Z', '+00:00'))
                            except ValueError:
                                pc_data_for_db[key] = datetime.now()
                    pc = PersonaCard(**pc_data_for_db)
                    session.add(pc)

                session.commit()
                session.refresh(pc)  # 刷新对象以获取数据库生成的值
                return pc
        except Exception as e:
            print(f"保存人设卡失败: {str(e)}")
            return None

    def delete_persona_card(self, pc_id: str) -> bool:
        """删除人设卡"""
        try:
            with self.get_session() as session:
                pc = session.query(PersonaCard).filter(
                    PersonaCard.id == pc_id).first()
                if pc:
                    session.delete(pc)
                    session.commit()
                return True
        except Exception as e:
            print(f"删除人设卡失败: {str(e)}")
            return False

    # 消息相关方法
    def get_all_messages(self):
        """获取所有消息"""
        with self.get_session() as session:
            return session.query(Message).all()

    def get_message_by_id(self, message_id: str):
        """根据ID获取消息"""
        with self.get_session() as session:
            return session.query(Message).filter(Message.id == message_id).first()

    def get_messages_by_recipient(self, recipient_id: str):
        """根据接收者ID获取消息"""
        with self.get_session() as session:
            return session.query(Message).filter(Message.recipient_id == recipient_id).all()

    def create_message(
        self,
        sender_id: str,
        recipient_id: str,
        title: str,
        content: str,
        message_type: str = "direct",
        broadcast_scope: Optional[str] = None,
        summary: Optional[str] = None
    ):
        """创建消息"""
        try:
            with self.get_session() as session:
                message = Message(
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    title=title or "新消息",
                    content=content,
                    summary=summary,
                    message_type=message_type or "direct",
                    broadcast_scope=broadcast_scope
                )
                session.add(message)
                session.commit()
                session.refresh(message)
                return message
        except Exception as e:
            print(f"创建消息失败: {str(e)}")
            return None

    def bulk_create_messages(self, messages: List[dict]) -> List[Message]:
        """批量创建消息"""
        if not messages:
            return []
        session = None
        try:
            with self.get_session() as session:
                # 为同一批消息使用同一个时间戳，确保统计查询时能正确匹配
                from datetime import datetime
                common_timestamp = datetime.now()

                # 为每个消息设置相同的 created_at 时间戳
                message_models = []
                for msg in messages:
                    msg_copy = msg.copy()
                    msg_copy['created_at'] = common_timestamp
                    message_models.append(Message(**msg_copy))

                session.add_all(message_models)
                session.commit()
                for msg in message_models:
                    session.refresh(msg)
                return message_models
        except Exception as e:
            # 回滚事务（如果session存在）
            if session:
                try:
                    session.rollback()
                except:
                    pass
            # 重新抛出异常，让调用者知道具体错误
            raise Exception(f"批量创建消息失败: {str(e)}")

    def get_conversation_messages(self, user_id: str, other_user_id: str, page: int = 1, page_size: int = 20):
        """获取与特定用户的对话消息"""
        offset = (page - 1) * page_size
        with self.get_session() as session:
            return session.query(Message).filter(
                or_(
                    and_(Message.sender_id == user_id,
                         Message.recipient_id == other_user_id),
                    and_(Message.sender_id == other_user_id,
                         Message.recipient_id == user_id)
                )
            ).order_by(Message.created_at.desc()).offset(offset).limit(page_size).all()

    def get_user_messages(self, user_id: str, page: int = 1, page_size: int = 20):
        """获取用户收到的消息（仅接收者）"""
        with self.get_session() as session:
            return session.query(Message).filter(
                Message.recipient_id == user_id
            ).order_by(Message.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    def get_broadcast_messages(self, page: int = 1, page_size: int = 20):
        """获取所有广播消息（按发送者分组，返回每个广播的唯一消息）"""
        with self.get_session() as session:
            # 获取所有广播消息
            messages = session.query(Message).filter(
                Message.message_type == "announcement",
                Message.broadcast_scope == "all_users"
                # 获取更多以便去重
            ).order_by(Message.created_at.desc()).offset((page - 1) * page_size).limit(page_size * 10).all()

            # 去重：相同sender_id、title、content、created_at的消息只保留一条
            seen = set()
            unique_messages = []
            for msg in messages:
                # 使用created_at的秒级精度作为key的一部分（因为同一广播的所有消息创建时间相同）
                created_at_key = msg.created_at.strftime(
                    "%Y-%m-%d %H:%M:%S") if msg.created_at else ""
                key = (msg.sender_id, msg.title, msg.content, created_at_key)
                if key not in seen:
                    seen.add(key)
                    unique_messages.append(msg)
                    if len(unique_messages) >= page_size:
                        break

            return unique_messages

    def get_broadcast_message_stats(self, message_id: str = None, sender_id: str = None, title: str = None):
        """获取广播消息统计信息（发送数量、已读数量等）"""
        with self.get_session() as session:
            query = session.query(Message).filter(
                Message.message_type == "announcement",
                Message.broadcast_scope == "all_users"
            )

            # 如果提供了message_id，查找相同广播的所有消息
            if message_id:
                # 先找到这条消息
                msg = session.query(Message).filter(
                    Message.id == message_id).first()
                if msg:
                    # 使用 sender_id、title、content 来唯一标识一个广播批次
                    # created_at 作为辅助条件，使用时间范围匹配（同一秒内）以应对可能的精度问题
                    # 注意：由于批量创建时已使用同一时间戳，理论上 created_at 应该完全相同
                    # 但使用时间范围匹配可以应对 SQLite 存储精度丢失等边缘情况
                    from datetime import timedelta
                    if msg.created_at:
                        # 使用时间范围：同一秒内的消息（确保匹配到所有同一批的消息）
                        # 由于批量创建时使用同一时间戳，同一批消息的 created_at 应该完全相同
                        # 但为了安全，使用时间范围匹配（同一秒内）
                        time_start = msg.created_at.replace(microsecond=0)
                        time_end = time_start + timedelta(seconds=1)
                        query = query.filter(
                            Message.sender_id == msg.sender_id,
                            Message.title == msg.title,
                            Message.content == msg.content,
                            Message.created_at >= time_start,
                            Message.created_at < time_end
                        )
                    else:
                        # 如果没有 created_at，只使用前三个条件
                        query = query.filter(
                            Message.sender_id == msg.sender_id,
                            Message.title == msg.title,
                            Message.content == msg.content
                        )
            elif sender_id and title:
                # 根据发送者和标题查找（不推荐，可能匹配到多个批次）
                query = query.filter(
                    Message.sender_id == sender_id,
                    Message.title == title
                )

            messages = query.all()
            total_count = len(messages)
            read_count = sum(1 for msg in messages if msg.is_read)

            return {
                "total_count": total_count,
                "read_count": read_count,
                "unread_count": total_count - read_count,
                "read_rate": (read_count / total_count * 100) if total_count > 0 else 0
            }

    def save_message(self, message_data) -> bool:
        """保存单条消息，支持dict或Message对象"""
        try:
            with self.get_session() as session:
                if isinstance(message_data, Message):
                    session.add(message_data)
                elif isinstance(message_data, dict):
                    session.add(Message(**message_data))
                else:
                    raise ValueError("message_data必须是dict或Message实例")
                session.commit()
                return True
        except Exception as e:
            print(f"保存消息失败: {str(e)}")
            return False

    def mark_message_read(self, message_id: str, user_id: str) -> bool:
        """标记消息为已读"""
        try:
            with self.get_session() as session:
                message = session.query(Message).filter(
                    Message.id == message_id).first()
                if message and message.recipient_id == user_id:
                    message.is_read = True
                    session.commit()
                    return True
                return False
        except Exception as e:
            print(f"标记消息已读失败: {str(e)}")
            return False

    def mark_message_as_read(self, message_id: str) -> bool:
        """标记消息为已读（兼容旧方法）"""
        try:
            with self.get_session() as session:
                message = session.query(Message).filter(
                    Message.id == message_id).first()
                if message:
                    message.is_read = True
                    session.commit()
                return True
        except Exception as e:
            print(f"标记消息已读失败: {str(e)}")
            return False

    def delete_message(self, message_id: str, user_id: str) -> bool:
        """删除消息（仅接收者可以删除）"""
        try:
            with self.get_session() as session:
                message = session.query(Message).filter(
                    Message.id == message_id).first()
                if message and message.recipient_id == user_id:
                    session.delete(message)
                    session.commit()
                    return True
                return False
        except Exception as e:
            print(f"删除消息失败: {str(e)}")
            return False

    def delete_messages(self, message_ids: List[str], user_id: str) -> int:
        """批量删除消息（仅接收者可以删除）"""
        try:
            deleted_count = 0
            with self.get_session() as session:
                messages = session.query(Message).filter(
                    Message.id.in_(message_ids),
                    Message.recipient_id == user_id
                ).all()
                for message in messages:
                    session.delete(message)
                    deleted_count += 1
                session.commit()
                return deleted_count
        except Exception as e:
            print(f"批量删除消息失败: {str(e)}")
            return 0

    def delete_broadcast_messages(self, message_id: str, user_id: str) -> int:
        """批量删除公告消息（发送者可以删除所有相关消息）"""
        try:
            with self.get_session() as session:
                # 先找到这条消息
                message = session.query(Message).filter(
                    Message.id == message_id).first()
                if not message:
                    return 0

                # 验证权限：只有发送者可以删除公告
                sender_id = str(message.sender_id) if message.sender_id else ""
                user_id_str = str(user_id) if user_id else ""

                if sender_id != user_id_str:
                    return 0

                # 如果是公告类型，删除所有相关的消息
                if message.message_type == "announcement" and message.broadcast_scope == "all_users":
                    # 查找所有相同广播的消息（相同sender_id、title、content、created_at）
                    created_at_key = message.created_at.strftime(
                        "%Y-%m-%d %H:%M:%S") if message.created_at else ""
                    related_messages = session.query(Message).filter(
                        Message.message_type == "announcement",
                        Message.broadcast_scope == "all_users",
                        Message.sender_id == message.sender_id,
                        Message.title == message.title,
                        Message.content == message.content
                    ).all()

                    # 进一步过滤：只删除相同时间（秒级精度）的消息
                    deleted_count = 0
                    for msg in related_messages:
                        msg_created_at_key = msg.created_at.strftime(
                            "%Y-%m-%d %H:%M:%S") if msg.created_at else ""
                        if msg_created_at_key == created_at_key:
                            session.delete(msg)
                            deleted_count += 1

                    session.commit()
                    return deleted_count
                else:
                    # 非公告消息，只删除单条
                    session.delete(message)
                    session.commit()
                    return 1
        except Exception as e:
            print(f"批量删除公告消息失败: {str(e)}")
            return 0

    def update_broadcast_messages(self, message_id: str, user_id: str, title: str = None, content: str = None, summary: str = None) -> int:
        """批量更新公告消息（发送者可以更新所有相关消息）"""
        try:
            with self.get_session() as session:
                # 先找到这条消息
                message = session.query(Message).filter(
                    Message.id == message_id).first()
                if not message:
                    return 0

                # 验证权限：只有发送者可以更新公告
                sender_id = str(message.sender_id) if message.sender_id else ""
                user_id_str = str(user_id) if user_id else ""

                if sender_id != user_id_str:
                    return 0

                # 如果没有提供更新内容，返回0
                if not title and not content and summary is None:
                    return 0

                # 如果是公告类型，更新所有相关的消息
                if message.message_type == "announcement" and message.broadcast_scope == "all_users":
                    # 查找所有相同广播的消息（相同sender_id、title、content、created_at）
                    created_at_key = message.created_at.strftime(
                        "%Y-%m-%d %H:%M:%S") if message.created_at else ""
                    related_messages = session.query(Message).filter(
                        Message.message_type == "announcement",
                        Message.broadcast_scope == "all_users",
                        Message.sender_id == message.sender_id,
                        Message.title == message.title,
                        Message.content == message.content
                    ).all()

                    # 进一步过滤：只更新相同时间（秒级精度）的消息
                    updated_count = 0
                    for msg in related_messages:
                        msg_created_at_key = msg.created_at.strftime(
                            "%Y-%m-%d %H:%M:%S") if msg.created_at else ""
                        if msg_created_at_key == created_at_key:
                            if title:
                                msg.title = title
                            if content:
                                msg.content = content
                            if summary is not None:  # 允许设置为空字符串
                                msg.summary = summary
                            updated_count += 1

                    session.commit()
                    return updated_count
                else:
                    # 非公告消息，只更新单条
                    if title:
                        message.title = title
                    if content:
                        message.content = content
                    session.commit()
                    return 1
        except Exception as e:
            print(f"批量更新公告消息失败: {str(e)}")
            return 0

    # Star记录相关方法
    def get_all_stars(self):
        """获取所有Star记录"""
        with self.get_session() as session:
            return session.query(StarRecord).all()

    def get_stars_by_user(self, user_id: str):
        """根据用户ID获取Star记录"""
        with self.get_session() as session:
            return session.query(StarRecord).filter(StarRecord.user_id == user_id).all()

    def is_starred(self, user_id: str, target_id: str, target_type: str) -> bool:
        """检查用户是否已star某个目标"""
        with self.get_session() as session:
            star = session.query(StarRecord).filter(
                and_(
                    StarRecord.user_id == user_id,
                    StarRecord.target_id == target_id,
                    StarRecord.target_type == target_type
                )
            ).first()
            return star is not None

    def add_star(self, user_id: str, target_id: str, target_type: str) -> bool:
        """添加Star记录"""
        try:
            with self.get_session() as session:
                # 检查是否已经star过
                existing_star = session.query(StarRecord).filter(
                    StarRecord.user_id == user_id,
                    StarRecord.target_id == target_id,
                    StarRecord.target_type == target_type
                ).first()

                if existing_star:
                    return False  # 已经star过了

                # 添加新star记录
                star = StarRecord(
                    user_id=user_id,
                    target_id=target_id,
                    target_type=target_type
                )
                session.add(star)

                # 更新目标的star数量
                if target_type == "knowledge":
                    kb = session.query(KnowledgeBase).filter(
                        KnowledgeBase.id == target_id).first()
                    if kb:
                        kb.star_count += 1
                elif target_type == "persona":
                    pc = session.query(PersonaCard).filter(
                        PersonaCard.id == target_id).first()
                    if pc:
                        pc.star_count += 1

                session.commit()
                return True
        except Exception as e:
            print(f"添加Star记录失败: {str(e)}")
            return False

    def remove_star(self, user_id: str, target_id: str, target_type: str) -> bool:
        """移除Star记录"""
        try:
            with self.get_session() as session:
                # 查找并删除star记录
                star = session.query(StarRecord).filter(
                    StarRecord.user_id == user_id,
                    StarRecord.target_id == target_id,
                    StarRecord.target_type == target_type
                ).first()

                if star:
                    session.delete(star)

                    # 更新目标的star数量
                    if target_type == "knowledge":
                        kb = session.query(KnowledgeBase).filter(
                            KnowledgeBase.id == target_id).first()
                        if kb and kb.star_count > 0:
                            kb.star_count -= 1
                    elif target_type == "persona":
                        pc = session.query(PersonaCard).filter(
                            PersonaCard.id == target_id).first()
                        if pc and pc.star_count > 0:
                            pc.star_count -= 1

                session.commit()
                return True
        except Exception as e:
            print(f"移除Star记录失败: {str(e)}")
            return False

    # 人设卡相关方法
    def get_persona_cards_by_user_id(self, user_id: str):
        """根据用户ID获取所有人设卡"""
        with self.get_session() as session:
            return session.query(PersonaCard).filter(PersonaCard.uploader_id == user_id).all()

    # 人设卡文件相关方法
    def get_persona_card_files_by_persona_card_id(self, persona_card_id: str):
        """根据人设卡ID获取所有相关文件"""
        with self.get_session() as session:
            return session.query(PersonaCardFile).filter(PersonaCardFile.persona_card_id == persona_card_id).all()

    def get_persona_card_file_by_id(self, file_id: str):
        """根据文件ID获取人设卡文件"""
        with self.get_session() as session:
            return session.query(PersonaCardFile).filter(PersonaCardFile.id == file_id).first()

    def save_persona_card_file(self, file_data: dict) -> PersonaCardFile:
        """保存人设卡文件并返回保存后的对象"""
        try:
            with self.get_session() as session:
                file_id = file_data.get("id")
                pc_file = None
                if file_id:
                    pc_file = session.query(PersonaCardFile).filter(
                        PersonaCardFile.id == file_id).first()

                if pc_file:
                    # 更新现有记录
                    for key, value in file_data.items():
                        if hasattr(pc_file, key):
                            setattr(pc_file, key, value)
                    pc_file.updated_at = datetime.now()
                else:
                    # 创建新记录
                    pc_file = PersonaCardFile(**file_data)
                    session.add(pc_file)

                session.commit()
                session.refresh(pc_file)
                return pc_file
        except Exception as e:
            print(f"保存人设卡文件失败: {str(e)}")
            # 打印更详细的错误信息
            import traceback
            traceback.print_exc()
            return None

    def get_files_by_persona_card_id(self, persona_card_id: str):
        """根据人设卡ID获取所有相关文件"""
        with self.get_session() as session:
            return session.query(PersonaCardFile).filter(PersonaCardFile.persona_card_id == persona_card_id).all()

    def delete_persona_card_file(self, file_id: str) -> bool:
        """删除人设卡文件"""
        try:
            with self.get_session() as session:
                pc_file = session.query(PersonaCardFile).filter(
                    PersonaCardFile.id == file_id).first()
                if pc_file:
                    session.delete(pc_file)
                    session.commit()
                return True
        except Exception as e:
            print(f"删除人设卡文件失败: {str(e)}")
            return False

    def delete_files_by_persona_card_id(self, persona_card_id: str) -> bool:
        """根据人设卡ID删除所有相关文件"""
        try:
            with self.get_session() as session:
                session.query(PersonaCardFile).filter(
                    PersonaCardFile.persona_card_id == persona_card_id).delete()
                session.commit()
                return True
        except Exception as e:
            print(f"删除人设卡文件失败: {str(e)}")
            return False

    # 用户相关方法
    def get_user_by_username(self, username: str):
        """根据用户名获取用户"""
        with self.get_session() as session:
            return session.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str):
        """根据邮箱获取用户"""
        with self.get_session() as session:
            # 统一转换为小写进行查询
            email_lower = email.lower()
            return session.query(User).filter(User.email == email_lower).first()

    def get_user_by_id(self, user_id: str):
        """根据ID获取用户"""
        with self.get_session() as session:
            return session.query(User).filter(User.id == user_id).first()

    def save_user(self, user_data: dict) -> bool:
        """保存用户"""
        try:
            with self.get_session() as session:
                # 统一将邮箱转换为小写
                if "email" in user_data and user_data["email"]:
                    user_data["email"] = user_data["email"].lower()

                # 处理 DateTime 字段：如果传入的是字符串，转换为 datetime 对象
                datetime_fields = ["created_at", "avatar_updated_at"]
                for field in datetime_fields:
                    if field in user_data:
                        value = user_data[field]
                        # 如果是字符串，转换为 datetime 对象
                        if isinstance(value, str):
                            try:
                                # 尝试解析 ISO 格式字符串（处理带Z和不带Z的情况）
                                if value.endswith('Z'):
                                    value = value[:-1] + '+00:00'
                                user_data[field] = datetime.fromisoformat(
                                    value)
                            except (ValueError, AttributeError):
                                # 如果解析失败，尝试其他格式
                                try:
                                    user_data[field] = datetime.strptime(
                                        value, "%Y-%m-%dT%H:%M:%S.%f")
                                except ValueError:
                                    try:
                                        user_data[field] = datetime.strptime(
                                            value, "%Y-%m-%dT%H:%M:%S")
                                    except ValueError:
                                        # 如果还是失败，使用当前时间
                                        user_data[field] = datetime.now()
                        # 如果已经是 datetime 对象，保持不变
                        elif isinstance(value, datetime):
                            pass
                        # 如果是 None，保持 None（允许清空字段）
                        elif value is None:
                            pass
                        else:
                            # 其他类型，使用当前时间
                            user_data[field] = datetime.now()

                user_id = user_data.get("id")
                user = session.query(User).filter(User.id == user_id).first()

                if user:
                    # 更新现有记录
                    for key, value in user_data.items():
                        if hasattr(user, key):
                            setattr(user, key, value)
                else:
                    # 创建新记录
                    user = User(**user_data)
                    session.add(user)

                session.commit()
                return True
        except Exception as e:
            print(f"保存用户失败: {str(e)}")
            return False

    def get_all_users(self):
        """获取所有用户"""
        with self.get_session() as session:
            return session.query(User).all()

    def get_users_by_ids(self, user_ids: List[str]):
        """根据ID列表批量获取用户"""
        if not user_ids:
            return []
        with self.get_session() as session:
            return session.query(User).filter(User.id.in_(user_ids)).all()

    def check_user_register_legality(self, username: str, email: str) -> str:
        """检查用户注册合法性"""
        try:
            with self.get_session() as session:
                # 检查用户名是否已存在
                user = session.query(User).filter(
                    User.username == username).first()
                if user:
                    return "用户名已存在"
                # 检查邮箱是否已被注册（统一转换为小写进行查询）
                email_lower = email.lower()
                user = session.query(User).filter(
                    User.email == email_lower).first()
                if user:
                    return "该邮箱已被注册"
                return "ok"
        except Exception as e:
            print(f"检查用户注册合法性失败: {str(e)}")
            return "系统错误"

    def verify_email_code(self, email: str, code: str) -> bool:
        """验证邮箱验证码是否有效（未使用且未过期）"""
        try:
            with self.get_session() as session:
                # 统一转换为小写进行查询
                email_lower = email.lower()
                record = session.query(EmailVerification).filter(
                    EmailVerification.email == email_lower,
                    EmailVerification.code == code,
                    EmailVerification.is_used == False,
                    EmailVerification.expires_at > datetime.now()
                ).first()
                if record:
                    record.is_used = True  # 标记为已使用
                    session.commit()
                    return True
                return False
        except Exception as e:
            print(f"验证邮箱验证码失败: {str(e)}")
            return False

    def check_email_rate_limit(self, email: str) -> bool:
        """检查同一邮箱1小时内是否超过5次请求 或 1分钟内是否超过1次"""
        from datetime import datetime, timedelta
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        one_minute_ago = now - timedelta(minutes=1)

        with self.get_session() as session:
            # 统一转换为小写进行查询
            email_lower = email.lower()
            record = session.query(EmailVerification).filter(
                EmailVerification.email == email_lower,
                EmailVerification.created_at > one_hour_ago
            ).count()
            if record >= 5:
                return False
            record = session.query(EmailVerification).filter(
                EmailVerification.email == email_lower,
                EmailVerification.created_at > one_minute_ago
            ).count()
            if record >= 1:
                return False
            return True

    def update_user_password(self, email: str, new_password: str) -> bool:
        """通过邮箱更新用户密码"""
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

            with self.get_session() as session:
                # 统一转换为小写进行查询
                email_lower = email.lower()
                user = session.query(User).filter(
                    User.email == email_lower).first()
                if not user:
                    return False

                # 确保密码不超过72字节（bcrypt限制）
                new_password = new_password[:72]
                user.hashed_password = pwd_context.hash(new_password)
                session.commit()
                return True
        except Exception as e:
            print(f"更新用户密码失败: {str(e)}")
            return False

    def save_verification_code(self, email: str, code: str):
        """保存邮箱验证码"""
        try:
            with self.get_session() as session:
                # 统一转换为小写进行存储
                email_lower = email.lower()
                verification = EmailVerification(
                    email=email_lower,
                    code=code,
                    is_used=False,
                    expires_at=datetime.now() + timedelta(minutes=2)
                )
                session.add(verification)
                session.commit()
                return verification.id
        except Exception as e:
            print(f"保存验证码失败: {str(e)}")
            return None

    def increment_knowledge_base_downloads(self, kb_id: str) -> bool:
        """原子性地增加知识库下载计数器"""
        try:
            with self.get_session() as session:
                session.execute(
                    text(
                        "UPDATE knowledge_bases SET downloads = downloads + 1 WHERE id = :kb_id"),
                    {"kb_id": kb_id}
                )
                session.commit()
                return True
        except Exception as e:
            print(f"更新知识库下载计数器失败: {str(e)}")
            return False

    def increment_persona_card_downloads(self, pc_id: str) -> bool:
        """原子性地增加人设卡下载计数器"""
        try:
            with self.get_session() as session:
                session.execute(
                    text(
                        "UPDATE persona_cards SET downloads = downloads + 1 WHERE id = :pc_id"),
                    {"pc_id": pc_id}
                )
                session.commit()
                return True
        except Exception as e:
            print(f"更新人设卡下载计数器失败: {str(e)}")
            return False

    # 上传记录相关方法
    def create_upload_record(
        self,
        uploader_id: str,
        target_id: str,
        target_type: str,
        name: str,
        description: Optional[str] = None,
        status: str = "pending"
    ) -> UploadRecord:
        """创建上传记录"""
        try:
            with self.get_session() as session:
                upload_record = UploadRecord(
                    uploader_id=uploader_id,
                    target_id=target_id,
                    target_type=target_type,
                    name=name,
                    description=description,
                    status=status
                )
                session.add(upload_record)
                session.commit()
                session.refresh(upload_record)
                return upload_record
        except Exception as e:
            print(f"创建上传记录失败: {str(e)}")
            return None

    def update_upload_record_status(self, target_id: str, status: str) -> bool:
        """更新上传记录状态"""
        try:
            with self.get_session() as session:
                upload_record = session.query(UploadRecord).filter(
                    UploadRecord.target_id == target_id
                ).first()
                if upload_record:
                    upload_record.status = status
                    upload_record.updated_at = datetime.now()
                    session.commit()
                    return True
                return False
        except Exception as e:
            print(f"更新上传记录状态失败: {str(e)}")
            return False

    def get_all_upload_records(self, page: int = 1, page_size: int = 20):
        """获取所有上传记录（分页）"""
        with self.get_session() as session:
            offset = (page - 1) * page_size
            return session.query(UploadRecord).order_by(
                UploadRecord.created_at.desc()
            ).offset(offset).limit(page_size).all()

    def get_upload_records_count(self):
        """获取上传记录总数"""
        with self.get_session() as session:
            return session.query(UploadRecord).count()

    def get_upload_records_by_uploader(self, uploader_id: str, page: int = 1, page_size: int = 20):
        """根据上传者ID获取上传记录（分页）"""
        with self.get_session() as session:
            offset = (page - 1) * page_size
            return session.query(UploadRecord).filter(
                UploadRecord.uploader_id == uploader_id
            ).order_by(
                UploadRecord.created_at.desc()
            ).offset(offset).limit(page_size).all()

    def get_upload_records_count_by_uploader(self, uploader_id: str):
        """根据上传者ID获取上传记录总数"""
        with self.get_session() as session:
            return session.query(UploadRecord).filter(
                UploadRecord.uploader_id == uploader_id
            ).count()

    def get_upload_stats_by_uploader(self, uploader_id: str):
        """根据上传者ID获取上传统计"""
        with self.get_session() as session:
            # 获取该用户的所有上传记录
            records = session.query(UploadRecord).filter(
                UploadRecord.uploader_id == uploader_id
            ).all()
            
            total_count = len(records)
            success_count = len([r for r in records if r.status == "success"])
            pending_count = len([r for r in records if r.status == "pending"])
            failed_count = len([r for r in records if r.status == "failed"])
            
            # 计算按类型统计
            knowledge_count = len([r for r in records if r.target_type == "knowledge"])
            persona_count = len([r for r in records if r.target_type == "persona"])
            
            return {
                "total": total_count,
                "success": success_count,
                "pending": pending_count,
                "failed": failed_count,
                "knowledge": knowledge_count,
                "persona": persona_count
            }

    def get_upload_records_by_status(self, status: str):
        """根据状态获取上传记录"""
        with self.get_session() as session:
            return session.query(UploadRecord).filter(
                UploadRecord.status == status
            ).all()

    def get_total_file_size_by_target(self, target_id: str, target_type: str) -> int:
        """根据目标ID和类型获取总文件大小"""
        try:
            with self.get_session() as session:
                if target_type == "knowledge":
                    files = session.query(KnowledgeBaseFile).filter(
                        KnowledgeBaseFile.knowledge_base_id == target_id
                    ).all()
                elif target_type == "persona":
                    files = session.query(PersonaCardFile).filter(
                        PersonaCardFile.persona_card_id == target_id
                    ).all()
                else:
                    return 0

                return sum(f.file_size or 0 for f in files)
        except Exception as e:
            print(f"获取文件大小失败: {str(e)}")
            return 0

    def get_upload_record_by_id(self, record_id: str) -> Optional[UploadRecord]:
        """根据ID获取上传记录"""
        with self.get_session() as session:
            return session.query(UploadRecord).filter(
                UploadRecord.id == record_id
            ).first()

    def delete_upload_record(self, record_id: str) -> bool:
        """删除上传记录"""
        try:
            with self.get_session() as session:
                upload_record = session.query(UploadRecord).filter(
                    UploadRecord.id == record_id
                ).first()

                if upload_record:
                    session.delete(upload_record)
                    session.commit()
                    return True
                return False
        except Exception as e:
            print(f"删除上传记录失败: {str(e)}")
            return False

    def delete_upload_records_by_target(self, target_id: str, target_type: str) -> bool:
        """根据目标ID和类型删除上传记录"""
        try:
            with self.get_session() as session:
                upload_records = session.query(UploadRecord).filter(
                    UploadRecord.target_id == target_id,
                    UploadRecord.target_type == target_type
                ).all()

                if upload_records:
                    for record in upload_records:
                        session.delete(record)
                    session.commit()
                    return True
                return False
        except Exception as e:
            print(f"根据目标删除上传记录失败: {str(e)}")
            return False

    def update_upload_record_status_by_id(self, record_id: str, status: str) -> bool:
        """根据记录ID更新上传记录状态"""
        try:
            with self.get_session() as session:
                upload_record = session.query(UploadRecord).filter(
                    UploadRecord.id == record_id
                ).first()

                if upload_record:
                    upload_record.status = status
                    upload_record.updated_at = datetime.now()
                    session.commit()
                    return True
                return False
        except Exception as e:
            print(f"更新上传记录状态失败: {str(e)}")
            return False

    def count_broadcast_messages(self) -> int:
        with self.get_session() as session:
            return session.query(Message).count()


# 创建全局SQLite数据库管理器实例
sqlite_db_manager = SQLiteDatabaseManager()
