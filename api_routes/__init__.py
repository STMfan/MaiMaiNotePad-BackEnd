from fastapi import APIRouter

from .user_router import user_router
from .admin_router import admin_router
from .knowledgeBase_router import knowledgeBase_router
from .messages_router import messages_router
from .persona_router import persona_router
from .review_router import review_router
from .dictionary_router import dictionary_router
from .comment_router import comment_router


api_router = APIRouter()

api_router.include_router(user_router)
api_router.include_router(admin_router)
api_router.include_router(knowledgeBase_router)
api_router.include_router(messages_router)
api_router.include_router(persona_router)
api_router.include_router(review_router)
api_router.include_router(dictionary_router)
api_router.include_router(comment_router)
