"""
Pydantic 模型定义

用于 API 请求和响应的数据验证与序列化。
"""

from pydantic import BaseModel, EmailStr, Field, model_validator, ConfigDict
from typing import List, Optional, Dict, Any, Literal, Generic, TypeVar, Union
from datetime import datetime


# 用户相关模型
class UserCreate(BaseModel):
    """用户注册请求模型"""

    username: str
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)


class UserUpdate(BaseModel):
    """用户信息更新请求模型"""

    username: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """用户信息响应模型"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool
    is_moderator: bool
    is_super_admin: bool
    created_at: datetime
    avatar_path: Optional[str] = None
    avatar_updated_at: Optional[datetime] = None


class CurrentUserResponse(BaseModel):
    """当前用户信息响应模型"""

    id: str
    username: str
    email: str
    role: str
    avatar_url: Optional[str] = None
    avatar_updated_at: Optional[str] = None
    is_muted: bool = False
    muted_until: Optional[datetime] = None


class LoginResponse(BaseModel):
    """登录成功响应模型"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class TokenResponse(BaseModel):
    """令牌刷新响应模型"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AvatarInfo(BaseModel):
    """头像信息响应模型"""

    avatar_url: str
    avatar_updated_at: str


# 知识库相关模型
class KnowledgeBaseCreate(BaseModel):
    """知识库创建请求模型"""

    name: str
    description: str
    copyright_owner: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=lambda: [])


class KnowledgeBaseUpdate(BaseModel):
    """知识库更新请求模型"""

    name: Optional[str] = None
    description: Optional[str] = None
    copyright_owner: Optional[str] = None
    is_public: Optional[bool] = None
    is_pending: Optional[bool] = None
    content: Optional[str] = None
    tags: Optional[Union[str, List[str]]] = None


class KnowledgeBaseFileResponse(BaseModel):
    """知识库文件响应模型"""

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


class KnowledgeBasePaginatedResponse(BaseModel):
    """知识库分页响应模型"""

    items: List[KnowledgeBaseResponse]
    total: int
    page: int
    page_size: int


# 人设卡相关模型
class PersonaCardCreate(BaseModel):
    """人设卡创建请求模型"""

    name: str
    description: str
    copyright_owner: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=lambda: [])


class PersonaCardUpdate(BaseModel):
    """人设卡更新请求模型"""

    name: Optional[str] = None
    description: Optional[str] = None
    copyright_owner: Optional[str] = None
    is_public: Optional[bool] = None
    is_pending: Optional[bool] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


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
    files: List[Dict[str, Any]] = Field(default_factory=list)
    content: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    downloads: int = 0
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    version: Optional[str] = None
    size: Optional[int] = None
    author: Optional[str] = None
    author_id: Optional[str] = None
    stars: int = 0


class PersonaCardPaginatedResponse(BaseModel):
    """人设卡分页响应模型"""

    items: List[PersonaCardResponse]
    total: int
    page: int
    page_size: int


# 消息相关模型
class MessageCreate(BaseModel):
    """消息创建请求模型"""

    title: str
    content: str
    summary: Optional[str] = None
    recipient_id: Optional[str] = None
    recipient_ids: Optional[List[str]] = None
    message_type: Literal["direct", "announcement"] = "direct"
    broadcast_scope: Optional[Literal["all_users"]] = None

    @model_validator(mode="before")
    @classmethod
    def validate_recipients(cls, values):
        if isinstance(values, dict):
            message_type = values.get("message_type", "direct")
            recipient_id = values.get("recipient_id")
            recipient_ids = values.get("recipient_ids") or []
            broadcast_scope = values.get("broadcast_scope")

            if message_type == "direct":
                # 私信必须指定接收者
                if not recipient_id and not recipient_ids:
                    raise ValueError("私信必须指定 recipient_id 或 recipient_ids")
            else:
                if not recipient_id and not recipient_ids and broadcast_scope != "all_users":
                    raise ValueError("公告必须指定接收者列表或 broadcast_scope=all_users")

            # 去重
            if recipient_ids:
                values["recipient_ids"] = list(dict.fromkeys([rid for rid in recipient_ids if rid]))
        return values


class MessageUpdate(BaseModel):
    """消息更新请求模型"""

    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None


class MessageResponse(BaseModel):
    """消息响应模型"""

    id: str
    sender_id: str
    recipient_id: str
    title: str
    content: str
    summary: Optional[str] = None
    message_type: Literal["direct", "announcement"]
    broadcast_scope: Optional[str]
    is_read: bool
    created_at: datetime


# 收藏相关模型
class StarRecordCreate(BaseModel):
    """收藏记录创建请求模型"""

    target_id: str
    target_type: str


class StarResponse(BaseModel):
    """收藏响应模型"""

    id: str
    user_id: str
    target_id: str
    target_type: str
    created_at: datetime


# 通用响应模型
T = TypeVar("T")


class Pagination(BaseModel):
    """分页信息"""

    page: int
    page_size: int
    total: int
    total_pages: int


class BaseResponse(BaseModel, Generic[T]):
    """基础 API 响应"""

    success: bool = True
    message: str = ""
    data: Optional[T] = None


class PageResponse(BaseModel, Generic[T]):
    """分页 API 响应"""

    success: bool = True
    message: str = ""
    data: List[T]
    pagination: Pagination
