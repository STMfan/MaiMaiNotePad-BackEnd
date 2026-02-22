"""
API routes module - 统一注册所有路由
"""

from fastapi import APIRouter

from app.api.routes import (
    users,
    auth,
    knowledge,
    persona,
    messages,
    admin,
    review,
    dictionary,
    comments,
)

# 创建主 APIRouter
api_router = APIRouter()

# 注册所有子路由
# 用户路由
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 向后兼容：添加 /user 前缀的 stars 路由
# 这是为了支持旧的 API 路径 /api/user/stars
from fastapi import APIRouter as _APIRouter

_user_compat_router = _APIRouter()
_user_compat_router.add_api_route("/stars", users.get_user_stars, methods=["GET"], tags=["users"])
api_router.include_router(_user_compat_router, prefix="/user")

# 认证路由
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

#
# 知识库路由
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
#
# 人设卡路由
# persona 路由自身已包含 /persona 前缀，这里不再额外加一级
api_router.include_router(persona.router, prefix="", tags=["persona"])
#
# 消息路由
# messages 路由自身已包含 /messages 与 /admin/broadcast-messages 等前缀，这里使用空前缀
api_router.include_router(messages.router, prefix="", tags=["messages"])

# 管理员路由
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

#
# 审核路由
# review 路由内部已包含 /review 前缀，这里不再重复添加
api_router.include_router(review.router, prefix="", tags=["review"])

#
# 字典路由
api_router.include_router(dictionary.router, prefix="/dictionary", tags=["dictionary"])
#
# 评论路由
# comments 路由本身已定义 /comments 前缀，这里使用空前缀
api_router.include_router(comments.router, prefix="", tags=["comments"])

__all__ = ["api_router"]
