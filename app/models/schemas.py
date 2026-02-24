"""
Pydantic 模型定义

用于 API 请求和响应的数据验证与序列化。
"""

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


# 用户相关模型
class UserCreate(BaseModel):
    """用户注册请求模型"""

    username: str
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)


class UserUpdate(BaseModel):
    """用户信息更新请求模型"""

    username: str | None = None
    email: EmailStr | None = None


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
    avatar_path: str | None = None
    avatar_updated_at: datetime | None = None


class CurrentUserResponse(BaseModel):
    """当前用户信息响应模型"""

    id: str
    username: str
    email: str
    role: str
    avatar_url: str | None = None
    avatar_updated_at: str | None = None
    is_muted: bool = False
    muted_until: datetime | None = None


class LoginResponse(BaseModel):
    """登录成功响应模型"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict[str, Any]


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
    copyright_owner: str | None = None
    content: str | None = None
    tags: list[str] | None = Field(default_factory=lambda: [])


class KnowledgeBaseUpdate(BaseModel):
    """知识库更新请求模型"""

    name: str | None = None
    description: str | None = None
    copyright_owner: str | None = None
    is_public: bool | None = None
    is_pending: bool | None = None
    content: str | None = None
    tags: str | list[str] | None = None


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
    copyright_owner: str | None
    star_count: int
    is_public: bool
    is_pending: bool
    base_path: str | None
    created_at: datetime
    updated_at: datetime
    files: list[KnowledgeBaseFileResponse] = Field(default_factory=list)
    content: str | None = None
    tags: list[str] = Field(default_factory=list)
    downloads: int = 0
    download_url: str | None = None
    preview_url: str | None = None
    version: str | None = None
    size: int | None = None
    author: str | None = None
    author_id: str | None = None


class KnowledgeBasePaginatedResponse(BaseModel):
    """知识库分页响应模型"""

    items: list[KnowledgeBaseResponse]
    total: int
    page: int
    page_size: int


# 人设卡相关模型
class PersonaCardCreate(BaseModel):
    """人设卡创建请求模型"""

    name: str
    description: str
    copyright_owner: str | None = None
    content: str | None = None
    tags: list[str] | None = Field(default_factory=lambda: [])


class PersonaCardUpdate(BaseModel):
    """人设卡更新请求模型"""

    name: str | None = None
    description: str | None = None
    copyright_owner: str | None = None
    is_public: bool | None = None
    is_pending: bool | None = None
    content: str | None = None
    tags: list[str] | None = None


class PersonaCardResponse(BaseModel):
    """人设卡响应模型"""

    id: str
    name: str
    description: str
    uploader_id: str
    copyright_owner: str | None
    star_count: int
    is_public: bool
    is_pending: bool
    created_at: datetime
    updated_at: datetime
    files: list[dict[str, Any]] = Field(default_factory=list)
    content: str | None = None
    tags: list[str] = Field(default_factory=list)
    downloads: int = 0
    download_url: str | None = None
    preview_url: str | None = None
    version: str | None = None
    size: int | None = None
    author: str | None = None
    author_id: str | None = None
    stars: int = 0


class PersonaCardPaginatedResponse(BaseModel):
    """人设卡分页响应模型"""

    items: list[PersonaCardResponse]
    total: int
    page: int
    page_size: int


# 消息相关模型
class MessageCreate(BaseModel):
    """消息创建请求模型"""

    title: str
    content: str
    summary: str | None = None
    recipient_id: str | None = None
    recipient_ids: list[str] | None = None
    message_type: Literal["direct", "announcement"] = "direct"
    broadcast_scope: Literal["all_users"] | None = None

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

    title: str | None = None
    content: str | None = None
    summary: str | None = None


class MessageResponse(BaseModel):
    """消息响应模型"""

    id: str
    sender_id: str
    recipient_id: str
    title: str
    content: str
    summary: str | None = None
    message_type: Literal["direct", "announcement"]
    broadcast_scope: str | None
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
    data: T | None = None


class PageResponse(BaseModel, Generic[T]):
    """分页 API 响应"""

    success: bool = True
    message: str = ""
    data: list[T]
    pagination: Pagination


# 内容审核相关模型
class ModerationRequest(BaseModel):
    """内容审核请求模型"""

    text: str = Field(..., min_length=1, description="待审核的文本内容")
    text_type: Literal["comment", "post", "title", "content"] = Field(
        default="comment", description="文本类型：comment（评论）、post（帖子）、title（标题）、content（正文）"
    )


class ModerationResult(BaseModel):
    """内容审核结果模型"""

    decision: Literal["true", "false", "unknown"] = Field(
        ..., description="审核决策：true（通过）、false（拒绝）、unknown（不确定）"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="违规置信度，0~1 之间的浮点数")
    violation_types: list[Literal["porn", "politics", "abuse"]] = Field(
        default_factory=list, description="违规类型列表，可包含 porn（色情）、politics（涉政）、abuse（辱骂）"
    )


class ModerationResponse(BaseModel):
    """内容审核响应模型"""

    success: bool = Field(..., description="请求是否成功")
    result: ModerationResult | None = Field(None, description="审核结果")
    message: str | None = Field(None, description="附加消息")
