"""
中间件配置模块

提供统一的中间件初始化和管理，包括：速率限制、CORS、错误处理等。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.logging import app_logger


def setup_middlewares(app: FastAPI) -> None:
    """
    为 FastAPI 应用配置所有中间件。

    Args:
        app: FastAPI 应用实例

    中间件执行顺序（从外到内）：
    1. ErrorHandlerMiddleware - 错误处理和请求日志（待添加）
    2. SlowAPIMiddleware - 速率限制
    3. CORSMiddleware - 跨域支持
    """
    try:
        # 1. 初始化速率限制器
        limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app_logger.debug("速率限制器已初始化")

        # 2. 添加速率限制中间件
        app.add_middleware(SlowAPIMiddleware)
        app_logger.debug("速率限制中间件已添加")

        # 3. 添加 CORS 中间件
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
