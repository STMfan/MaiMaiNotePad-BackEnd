"""
模型导出模块
为应用提供统一的数据模型导入接口
"""

from pydantic import BaseModel, EmailStr, Field, model_validator
from pydantic.generics import GenericModel
from typing import List, Optional, Dict, Any, Literal, Generic, TypeVar
from datetime import datetime

# 从 database_models 导入SQLAlchemy模型
from database_models import (
    User, KnowledgeBase, KnowledgeBaseFile, PersonaCard, PersonaCardFile, Message, StarRecord, Base
)

# Pydantic模型用于API请求和响应

class UserCreate(BaseModel):
    """用户创建请求模型"""
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """用户响应模型"""
    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool
    is_moderator: bool
    created_at: datetime


class LoginResponse(BaseModel):
    """登录成功返回的数据"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class TokenResponse(BaseModel):
    """刷新令牌返回的数据"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUserResponse(BaseModel):
    """当前用户信息返回的数据"""
    id: str
    username: str
    email: str
    role: str
    avatar_url: Optional[str] = None
    avatar_updated_at: Optional[str] = None

class KnowledgeBaseCreate(BaseModel):
    """知识库创建请求模型"""
    name: str
    description: str
    copyright_owner: Optional[str] = None

class KnowledgeBaseUpdate(BaseModel):
    """知识库更新请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    copyright_owner: Optional[str] = None
    is_public: Optional[bool] = None
    is_pending: Optional[bool] = None
    content: Optional[str] = None
    tags: Optional[str] = None

class PersonaCardUpdate(BaseModel):
    """人设卡更新请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    copyright_owner: Optional[str] = None
    is_public: Optional[bool] = None
    is_pending: Optional[bool] = None
    content: Optional[str] = None
    tags: Optional[str] = None

class KnowledgeBaseFileResponse(BaseModel):
    """知识库文件响应"""
    file_id: str
    original_name: str
    file_size: int


class KnowledgeBaseResponse(BaseModel):
    """知识库响应模型"""
    id: str
    name: str
    description: str
    uploader_id: str
    copyright_owner: Optional[str]
    star_count: int
    is_public: bool
    is_pending: bool
    base_path: Optional[str]
    created_at: datetime
    updated_at: datetime
    # 扩展字段
    files: List[KnowledgeBaseFileResponse] = Field(default_factory=list)
    content: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    downloads: int = 0
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    version: Optional[str] = None
    size: Optional[int] = None
    author: Optional[str] = None
    author_id: Optional[str] = None

class PersonaCardCreate(BaseModel):
    """人设卡创建请求模型"""
    name: str
    description: str
    copyright_owner: Optional[str] = None

class PersonaCardResponse(BaseModel):
    """人设卡响应模型"""
    id: str
    name: str
    description: str
    uploader_id: str
    copyright_owner: Optional[str]
    star_count: int
    is_public: bool
    is_pending: bool
    created_at: datetime
    updated_at: datetime
    # 扩展字段
    files: List[Dict[str, Any]] = []
    content: Optional[str] = None
    tags: List[str] = []
    downloads: int = 0
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    version: Optional[str] = None
    size: Optional[int] = None
    author: Optional[str] = None
    author_id: Optional[str] = None
    stars: int = 0


class AvatarInfo(BaseModel):
    """头像相关返回数据"""
    avatar_url: str
    avatar_updated_at: str


T = TypeVar("T")


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class BaseResponse(GenericModel, Generic[T]):
    success: bool = True
    message: str = ""
    data: Optional[T] = None


class PageResponse(GenericModel, Generic[T]):
    success: bool = True
    message: str = ""
    data: List[T]
    pagination: Pagination

class MessageCreate(BaseModel):
    """消息创建请求模型"""
    title: str
    content: str
    summary: Optional[str] = None  # 消息简介，可选
    recipient_id: Optional[str] = None
    recipient_ids: Optional[List[str]] = None
    message_type: Literal["direct", "announcement"] = "direct"
    broadcast_scope: Optional[Literal["all_users"]] = None

    @model_validator(mode='before')
    @classmethod
    def validate_recipients(cls, values):
        if isinstance(values, dict):
            message_type = values.get("message_type", "direct")
            recipient_id = values.get("recipient_id")
            recipient_ids = values.get("recipient_ids") or []
            broadcast_scope = values.get("broadcast_scope")

            if message_type == "direct":
                if not recipient_id:
                    raise ValueError("私信必须指定recipient_id")
            else:
                if not recipient_id and not recipient_ids and broadcast_scope != "all_users":
                    raise ValueError("公告必须指定接收者列表或broadcast_scope=all_users")
            # 去重
            if recipient_ids:
                values["recipient_ids"] = list(dict.fromkeys([rid for rid in recipient_ids if rid]))
        return values

class MessageUpdate(BaseModel):
    """消息更新请求模型"""
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None  # 消息简介，可选

class MessageResponse(BaseModel):
    """消息响应模型"""
    id: str
    sender_id: str
    recipient_id: str
    title: str
    content: str
    summary: Optional[str] = None  # 消息简介，可选
    message_type: Literal["direct", "announcement"]
    broadcast_scope: Optional[str]
    is_read: bool
    created_at: datetime

class StarRecordCreate(BaseModel):
    """Star记录创建请求模型"""
    target_id: str
    target_type: str

class StarResponse(BaseModel):
    """Star响应模型"""
    id: str
    user_id: str
    target_id: str
    target_type: str
    created_at: datetime

class KnowledgeBasePaginatedResponse(BaseModel):
    """知识库分页响应模型"""
    items: List[KnowledgeBaseResponse]
    total: int
    page: int
    page_size: int

class PersonaCardPaginatedResponse(BaseModel):
    """人设卡分页响应模型"""
    items: List[PersonaCardResponse]
    total: int
    page: int
    page_size: int

# 导出所有模型
__all__ = [
    # SQLAlchemy模型
    'Base', 'User', 'KnowledgeBase', 'KnowledgeBaseFile', 'PersonaCard', 'Message', 'StarRecord',
    
    # Pydantic模型
    'UserCreate', 'UserResponse',
    'LoginResponse', 'TokenResponse', 'CurrentUserResponse', 'AvatarInfo',
    'KnowledgeBaseCreate', 'KnowledgeBaseUpdate', 'KnowledgeBaseFileResponse', 'KnowledgeBaseResponse',
    'KnowledgeBasePaginatedResponse',
    'PersonaCardCreate', 'PersonaCardUpdate', 'PersonaCardResponse',
    'PersonaCardPaginatedResponse',
    'MessageCreate', 'MessageResponse',
    'StarRecordCreate', 'StarResponse',
]
