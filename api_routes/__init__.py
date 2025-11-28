from fastapi import APIRouter

# 导入各模块路由
from .user_router import user_router
from .admin_router import admin_router
from .knowledgeBase_router import knowledgeBase_router
from .messages_router import messages_router
from .persona_router import persona_router
from .review_router import review_router

# 创建主路由器
api_router = APIRouter()

# 将各模块路由包含到主路由器中
api_router.include_router(user_router)
api_router.include_router(admin_router)
api_router.include_router(knowledgeBase_router)
api_router.include_router(messages_router)
api_router.include_router(persona_router)
api_router.include_router(review_router)
