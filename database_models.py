"""
SQLite数据库模型定义
包含知识库、人设卡、信箱等数据模型
"""
import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, create_engine, Index, and_, or_, inspect
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
    
    # 添加索引
    __table_args__ = (
        Index('idx_user_username', 'username'),
        Index('idx_user_email', 'email'),
        Index('idx_user_is_active', 'is_active'),
        Index('idx_user_is_admin', 'is_admin'),
        Index('idx_user_is_moderator', 'is_moderator'),
    )
    
    # 关系
    uploaded_knowledge_bases = relationship("KnowledgeBase", back_populates="uploader")
    uploaded_persona_cards = relationship("PersonaCard", back_populates="uploader")
    received_messages = relationship("Message", foreign_keys="Message.recipient_id", back_populates="recipient")
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    star_records = relationship("StarRecord", back_populates="user")
    
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
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建用户对象"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            username=data.get("username", ""),
            email=data.get("email", ""),
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
    uploader_id = Column(String, ForeignKey("users.id"), nullable=False)
    copyright_owner = Column(String, nullable=True)
    star_count = Column(Integer, default=0)
    base_path = Column(Text, default="[]") 
    metadata_path = Column(String, nullable=False)
    is_public = Column(Boolean, default=False)
    is_pending = Column(Boolean, default=True)
    rejection_reason = Column(Text, nullable=True)
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
    uploader = relationship("User", back_populates="uploaded_knowledge_bases")
    # 移除star_records关系，因为StarRecord没有正确的外键关系
    # star_records = relationship("StarRecord", back_populates="knowledge_base")

    def to_dict(self):
        """将知识库对象转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "uploader_id": self.uploader_id,
            "copyright_owner": self.copyright_owner,
            "star_count": self.star_count or 0,
            "base_path": self.base_path or "[]",
            "is_public": self.is_public,
            "is_pending": self.is_pending if self.is_pending is not None else True,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at if self.created_at else datetime.now(),
            "updated_at": self.updated_at if self.updated_at else datetime.now()
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
            star_count=data.get("star_count", 0),
            base_path=data.get("bast_path", "[]"),
            metadata_path=data.get("metadata_path", ""),
            is_public=data.get("is_public", False),
            is_pending=data.get("is_pending", True),
            rejection_reason=data.get("rejection_reason", None),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
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
    uploader_id = Column(String, ForeignKey("users.id"), nullable=False)
    copyright_owner = Column(String, nullable=True)
    star_count = Column(Integer, default=0)
    base_path = Column(String, nullable=False)
    is_public = Column(Boolean, default=False)
    is_pending = Column(Boolean, default=True)
    rejection_reason = Column(Text, nullable=True)
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
    uploader = relationship("User", back_populates="uploaded_persona_cards")
    # 移除star_records关系，因为StarRecord没有正确的外键关系
    # star_records = relationship("StarRecord", back_populates="persona_card")

    def to_dict(self):
        """将人设卡对象转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "uploader_id": self.uploader_id,
            "copyright_owner": self.copyright_owner,
            "star_count": self.star_count or 0,
            "base_path": self.base_path,
            "is_public": self.is_public,
            "is_pending": self.is_pending if self.is_pending is not None else True,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at if self.created_at else datetime.now(),
            "updated_at": self.updated_at if self.updated_at else datetime.now()
        }


class Message(Base):
    """信箱消息模型"""
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id = Column(String, ForeignKey("users.id"), nullable=False)
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
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
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")

    def to_dict(self):
        """将消息对象转换为字典"""
        data = {
            "id": self.id,
            "recipient_id": self.recipient_id,
            "sender_id": self.sender_id,
            "title": self.title,
            "content": self.content,
            "message_type": self.message_type or "direct",
            "broadcast_scope": self.broadcast_scope,
            "is_read": self.is_read or False,
            "created_at": self.created_at if self.created_at else datetime.now()
        }
        return data


class StarRecord(Base):
    """Star记录模型"""
    __tablename__ = "star_records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    target_id = Column(String, nullable=False)
    target_type = Column(String, nullable=False)  # "knowledge" 或 "persona"
    created_at = Column(DateTime, default=datetime.now)
    
    # 添加索引
    __table_args__ = (
        Index('idx_star_user_id', 'user_id'),
        Index('idx_star_target_id', 'target_id'),
        Index('idx_star_target_type', 'target_type'),
        Index('idx_star_created_at', 'created_at'),
        Index('idx_star_user_target', 'user_id', 'target_id', 'target_type'),  # 复合索引用于检查用户是否已star某个目标
    )
    
    # 关系
    user = relationship("User", back_populates="star_records")
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


class SQLiteDatabaseManager:
    """SQLite数据库管理器"""
    
    def __init__(self, db_path: str = "./data/maimnp.db"):
        self.db_path = db_path
        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 创建数据库引擎
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False, connect_args={"check_same_thread": False})
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 创建所有表
        Base.metadata.create_all(bind=self.engine)
        
        # 执行数据库迁移
        self._migrate_database()
    
    def _migrate_database(self):
        """执行数据库迁移，添加缺失的列"""
        try:
            inspector = inspect(self.engine)
            
            # 检查 messages 表是否存在
            if 'messages' in inspector.get_table_names():
                # 获取现有列
                existing_columns = [col['name'] for col in inspector.get_columns('messages')]
                
                # 检查并添加 message_type 列
                if 'message_type' not in existing_columns:
                    with self.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN message_type VARCHAR DEFAULT 'direct'"))
                    print("已添加 message_type 列到 messages 表")
                
                # 检查并添加 broadcast_scope 列（如果缺失）
                if 'broadcast_scope' not in existing_columns:
                    with self.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE messages ADD COLUMN broadcast_scope VARCHAR"))
                    print("已添加 broadcast_scope 列到 messages 表")
        except Exception as e:
            print(f"数据库迁移失败: {str(e)}")
            # 不抛出异常，允许应用继续运行
    
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
        """获取所有待审核的知识库，支持分页、搜索、按上传者筛选和排序"""
        with self.get_session() as session:
            query = session.query(KnowledgeBase).filter(KnowledgeBase.is_pending == True)
            
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
            
            # 分页
            offset = (page - 1) * page_size
            return query.offset(offset).limit(page_size).all()
    
    def get_public_knowledge_bases(self, page: int = 1, page_size: int = 10, name: str = None, uploader_id: str = None, sort_by: str = "created_at", sort_order: str = "desc"):
        """获取所有公开的知识库，支持分页、搜索、按上传者筛选和排序"""
        with self.get_session() as session:
            query = session.query(KnowledgeBase).filter(KnowledgeBase.is_public == True)
            
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
            
            # 分页
            offset = (page - 1) * page_size
            return query.offset(offset).limit(page_size).all()
    
    def get_knowledge_bases_by_uploader(self, uploader_id: str):
        """根据上传者ID获取知识库"""
        with self.get_session() as session:
            return session.query(KnowledgeBase).filter(KnowledgeBase.uploader_id == uploader_id).all()
    
    def save_knowledge_base(self, kb_data: dict) -> KnowledgeBase:
        """保存知识库并返回保存后的对象"""
        try:
            with self.get_session() as session:
                kb_id = kb_data.get("id")
                kb = None
                if kb_id:
                    kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
                
                if kb:
                    # 更新现有记录
                    for key, value in kb_data.items():
                        if hasattr(kb, key):
                            setattr(kb, key, value)
                    kb.updated_at = datetime.now()
                else:
                    if not kb_data.get("metadata_path"):
                        kb_data["metadata_path"] = "default_metadata_path"  # 设置默认值
                    # 创建新记录
                    kb = KnowledgeBase(**kb_data)
                    # 确保file_paths是字符串格式
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
                kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
                if kb:
                    session.delete(kb)
                # 同时删除相关的文件记录
                session.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == kb_id).delete()
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
                    kb_file = session.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.id == file_id).first()
                
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
                kb_file = session.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.id == file_id).first()
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
                session.query(KnowledgeBaseFile).filter(KnowledgeBaseFile.knowledge_base_id == knowledge_base_id).delete()
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
        """获取所有待审核的人设卡，支持分页、搜索、按上传者筛选和排序"""
        with self.get_session() as session:
            query = session.query(PersonaCard).filter(PersonaCard.is_pending == True)
            
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
            
            # 分页
            offset = (page - 1) * page_size
            return query.offset(offset).limit(page_size).all()
    
    def get_public_persona_cards(self, page: int = 1, page_size: int = 19, name: str = None, uploader_id: str = None, sort_by: str = "created_at", sort_order: str = "desc"):
        """获取所有公开的人设卡，支持分页、搜索、按上传者筛选和排序"""
        with self.get_session() as session:
            query = session.query(PersonaCard).filter(PersonaCard.is_public == True)
            
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
            
            # 分页
            offset = (page - 1) * page_size
            return query.offset(offset).limit(page_size).all()
    
    def get_persona_cards_by_uploader(self, uploader_id: str):
        """根据上传者ID获取人设卡"""
        with self.get_session() as session:
            return session.query(PersonaCard).filter(PersonaCard.uploader_id == uploader_id).all()
    
    def save_persona_card(self, pc_data: dict) -> PersonaCard:
        """保存人设卡并返回保存后的对象"""
        try:
            with self.get_session() as session:
                pc_id = pc_data.get("id")
                pc = session.query(PersonaCard).filter(PersonaCard.id == pc_id).first()
                
                if pc:
                    # 更新现有记录
                    for key, value in pc_data.items():
                        if hasattr(pc, key):
                            setattr(pc, key, value)
                    pc.updated_at = datetime.now()
                else:
                    # 创建新记录
                    pc = PersonaCard(**pc_data)
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
                pc = session.query(PersonaCard).filter(PersonaCard.id == pc_id).first()
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
        broadcast_scope: Optional[str] = None
    ):
        """创建消息"""
        try:
            with self.get_session() as session:
                message = Message(
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    title=title or "新消息",
                    content=content,
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
                message_models = [Message(**msg) for msg in messages]
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
    
    def get_conversation_messages(self, user_id: str, other_user_id: str, limit: int = 50, offset: int = 0):
        """获取与特定用户的对话消息"""
        with self.get_session() as session:
            return session.query(Message).filter(
                or_(
                    and_(Message.sender_id == user_id, Message.recipient_id == other_user_id),
                    and_(Message.sender_id == other_user_id, Message.recipient_id == user_id)
                )
            ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
    
    def get_user_messages(self, user_id: str, limit: int = 50, offset: int = 0):
        """获取用户的所有消息（发送和接收）"""
        with self.get_session() as session:
            return session.query(Message).filter(
                or_(Message.sender_id == user_id, Message.recipient_id == user_id)
            ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
    
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
                message = session.query(Message).filter(Message.id == message_id).first()
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
                message = session.query(Message).filter(Message.id == message_id).first()
                if message:
                    message.is_read = True
                    session.commit()
                return True
        except Exception as e:
            print(f"标记消息已读失败: {str(e)}")
            return False
    
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
            return session.query(StarRecord).filter(
                StarRecord.user_id == user_id,
                StarRecord.target_id == target_id,
                StarRecord.target_type == target_type
            ).first() is not None
    
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
                    kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == target_id).first()
                    if kb:
                        kb.star_count += 1
                elif target_type == "persona":
                    pc = session.query(PersonaCard).filter(PersonaCard.id == target_id).first()
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
                        kb = session.query(KnowledgeBase).filter(KnowledgeBase.id == target_id).first()
                        if kb and kb.star_count > 0:
                            kb.star_count -= 1
                    elif target_type == "persona":
                        pc = session.query(PersonaCard).filter(PersonaCard.id == target_id).first()
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
                    pc_file = session.query(PersonaCardFile).filter(PersonaCardFile.id == file_id).first()
                
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
                pc_file = session.query(PersonaCardFile).filter(PersonaCardFile.id == file_id).first()
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
                session.query(PersonaCardFile).filter(PersonaCardFile.persona_card_id == persona_card_id).delete()
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
            return session.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: str):
        """根据ID获取用户"""
        with self.get_session() as session:
            return session.query(User).filter(User.id == user_id).first()
    
    def save_user(self, user_data: dict) -> bool:
        """保存用户"""
        try:
            with self.get_session() as session:
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
                user = session.query(User).filter(User.username == username).first()
                if user:
                    return "用户名已存在"
                # 检查邮箱是否已被注册
                user = session.query(User).filter(User.email == email).first()
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
                record = session.query(EmailVerification).filter(
                    EmailVerification.email == email,
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
        """检查同一邮箱1小时内是否超过5次请求"""
        from datetime import datetime, timedelta
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        with self.get_session() as session:
            record = session.query(EmailVerification).filter(
                EmailVerification.email == email,
                EmailVerification.created_at > one_hour_ago
            ).count()
            if record >= 5:
                return False
            return True

    def update_user_password(self, email: str, new_password: str) -> bool:
        """通过邮箱更新用户密码"""
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            with self.get_session() as session:
                user = session.query(User).filter(User.email == email).first()
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
                verification=EmailVerification(
                    email=email,
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



# 创建全局SQLite数据库管理器实例
sqlite_db_manager = SQLiteDatabaseManager()