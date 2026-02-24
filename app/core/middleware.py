"""
中间件配置模块

提供统一的中间件初始化和管理，包括：速率限制、CORS、错误处理、缓存等。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.logging import app_logger


def setup_middlewares(app: FastAPI) -> None:
    """
    为 FastAPI 应用配置所有中间件。

    Args:
        app: FastAPI 应用实例

    中间件执行顺序（从外到内）：
    1. ErrorHandlerMiddleware - 错误处理和请求日志（待添加）
    2. CacheMiddleware - 缓存处理（如果启用）
    3. SlowAPIMiddleware - 速率限制
    4. CORSMiddleware - 跨域支持
    """
    try:
        # 1. 初始化速率限制器
        limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
        app_logger.debug("速率限制器已初始化")

        # 2. 添加缓存中间件（如果启用）
        try:
            from app.core.cache.factory import get_cache_manager
            from app.core.cache.middleware import CacheMiddleware

            cache_manager = get_cache_manager()

            # 创建缓存中间件实例
            cache_middleware = CacheMiddleware(
                app=app,
                cache_manager=cache_manager,
                default_ttl=300,  # 默认 5 分钟
                cache_query_params=True,
                excluded_paths=[
                    "/api/admin",
                    "/api/auth",
                    "/api/ws",
                    "/api/review",
                    "/api/users/me",
                ],  # 排除管理、认证、WebSocket、审核和用户个人信息路径
            )

            # 将中间件实例保存到 app.state，以便 API 端点访问
            app.state.cache_middleware = cache_middleware

            # 添加中间件到应用
            app.add_middleware(
                CacheMiddleware,
                cache_manager=cache_manager,
                default_ttl=300,
                cache_query_params=True,
                excluded_paths=["/api/admin", "/api/auth", "/api/ws", "/api/review", "/api/users/me"],
            )

            if cache_manager.is_enabled():
                app_logger.info("缓存中间件已启用")
            else:
                app_logger.info("缓存中间件已添加（降级模式：缓存禁用）")

        except Exception as e:
            app_logger.warning(f"缓存中间件初始化失败，将跳过缓存功能: {str(e)}")
            app.state.cache_middleware = None

        # 3. 添加速率限制中间件
        app.add_middleware(SlowAPIMiddleware)
        app_logger.debug("速率限制中间件已添加")

        # 4. 添加 CORS 中间件
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 生产环境应配置具体域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["Content-Disposition"],
        )
        app_logger.debug("CORS 中间件已配置")

        app_logger.info("中间件配置完成")

    except Exception as e:
        app_logger.error(f"中间件配置失败: {str(e)}")
        raise
