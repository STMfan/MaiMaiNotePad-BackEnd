"""
API 路由处理器

此模块导出所有路由路由器以在主 API 路由器中注册。
"""

from app.api.routes.users import router as users_router
from app.api.routes.auth import router as auth_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.persona import router as persona_router
from app.api.routes.messages import router as messages_router
from app.api.routes.admin import router as admin_router
from app.api.routes.review import router as review_router
from app.api.routes.dictionary import router as dictionary_router
from app.api.routes.comments import router as comments_router

__all__ = [
    "users_router",
    "auth_router",
    "knowledge_router",
    "persona_router",
    "messages_router",
    "admin_router",
    "review_router",
    "dictionary_router",
    "comments_router",
]
