"""
中间件配置模块
提供统一的中间件初始化和管理功能
包含：速率限制、CORS、错误处理等中间件的配置
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from error_handlers import ErrorHandlerMiddleware, setup_exception_handlers
from logging_config import app_logger


def setup_middlewares(app: FastAPI) -> None:
    """
    配置所有中间件
    
    Args:
        app: FastAPI应用实例
        
    中间件执行顺序（从外到内）：
    1. ErrorHandlerMiddleware - 错误处理和请求日志
    2. SlowAPIMiddleware - 速率限制
    3. CORSMiddleware - CORS跨域支持
    """
    try:
        # 1. 初始化速率限制器
        app_logger.info("初始化速率限制器...")
        limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app_logger.info("速率限制器初始化完成")

        # 2. 添加错误处理中间件（最外层，最先执行）
        app_logger.info("添加错误处理中间件...")
        app.add_middleware(ErrorHandlerMiddleware)
        app_logger.info("错误处理中间件添加完成")

        # 3. 添加速率限制中间件（需要在路由注册之前）
        app_logger.info("添加速率限制中间件...")
        app.add_middleware(SlowAPIMiddleware)
        app_logger.info("速率限制中间件添加完成")

        # 4. 添加CORS中间件
        app_logger.info("配置CORS中间件...")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 生产环境应配置具体域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app_logger.info("CORS中间件配置完成")

        # 5. 设置异常处理器
        app_logger.info("设置异常处理器...")
        setup_exception_handlers(app)
        app_logger.info("异常处理器设置完成")

        app_logger.info("所有中间件配置完成")
        
    except Exception as e:
        app_logger.error(f"中间件配置失败: {str(e)}")
        raise




