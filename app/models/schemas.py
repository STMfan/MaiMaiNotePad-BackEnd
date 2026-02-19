"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel, EmailStr, Field, model_validator, ConfigDict
from typing import List, Optional, Dict, Any, Literal, Generic, TypeVar
from datetime import datetime


# User models
class UserCreate(BaseModel):
    """User creation request model"""
    username: str
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)


class UserUpdate(BaseModel):
    """User update request model"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """User response model"""
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
    """Current user information response"""
    id: str
    username: str
    email: str
    role: str
    avatar_url: Optional[str] = None
    avatar_updated_at: Optional[str] = None
    is_muted: bool = False
    muted_until: Optional[datetime] = None


class LoginResponse(BaseModel):
    """Login success response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class TokenResponse(BaseModel):
    """Token refresh response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AvatarInfo(BaseModel):
    """Avatar information response"""
    avatar_url: str
    avatar_updated_at: str


# Knowledge base models
class KnowledgeBaseCreate(BaseModel):
    """Knowledge base creation request"""
    name: str
    description: str
    copyright_owner: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)


class KnowledgeBaseUpdate(BaseModel):
    """Knowledge base update request"""
    name: Optional[str] = None
    description: Optional[str] = None
    copyright_owner: Optional[str] = None
    is_public: Optional[bool] = None
    is_pending: Optional[bool] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class KnowledgeBaseFileResponse(BaseModel):
    """Knowledge base file response"""
    file_id: str
    original_name: str
    file_size: int


class KnowledgeBaseResponse(BaseModel):
    """Knowledge base response"""
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
    """Knowledge base paginated response"""
    items: List[KnowledgeBaseResponse]
    total: int
    page: int
    page_size: int


# Persona card models
class PersonaCardCreate(BaseModel):
    """Persona card creation request"""
    name: str
    description: str
    copyright_owner: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)


class PersonaCardUpdate(BaseModel):
    """Persona card update request"""
    name: Optional[str] = None
    description: Optional[str] = None
    copyright_owner: Optional[str] = None
    is_public: Optional[bool] = None
    is_pending: Optional[bool] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class PersonaCardResponse(BaseModel):
    """Persona card response"""
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
    """Persona card paginated response"""
    items: List[PersonaCardResponse]
    total: int
    page: int
    page_size: int


# Message models
class MessageCreate(BaseModel):
    """Message creation request"""
    title: str
    content: str
    summary: Optional[str] = None
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
                # Direct message can have either recipient_id or recipient_ids
                if not recipient_id and not recipient_ids:
                    raise ValueError("Direct message must specify recipient_id or recipient_ids")
            else:
                if not recipient_id and not recipient_ids and broadcast_scope != "all_users":
                    raise ValueError("Announcement must specify recipient list or broadcast_scope=all_users")
            
            # Remove duplicates
            if recipient_ids:
                values["recipient_ids"] = list(dict.fromkeys([rid for rid in recipient_ids if rid]))
        return values


class MessageUpdate(BaseModel):
    """Message update request"""
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None


class MessageResponse(BaseModel):
    """Message response"""
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


# Star models
class StarRecordCreate(BaseModel):
    """Star record creation request"""
    target_id: str
    target_type: str


class StarResponse(BaseModel):
    """Star response"""
    id: str
    user_id: str
    target_id: str
    target_type: str
    created_at: datetime


# Generic response models
T = TypeVar("T")


class Pagination(BaseModel):
    """Pagination information"""
    page: int
    page_size: int
    total: int
    total_pages: int


class BaseResponse(BaseModel, Generic[T]):
    """Base API response"""
    success: bool = True
    message: str = ""
    data: Optional[T] = None


class PageResponse(BaseModel, Generic[T]):
    """Paginated API response"""
    success: bool = True
    message: str = ""
    data: List[T]
    pagination: Pagination
