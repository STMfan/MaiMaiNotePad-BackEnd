"""
MaiMNP Backend Application

FastAPI 应用主入口文件，负责应用初始化、路由注册、中间件配置等。
"""

import os
import sys
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket

from app.api import api_router
from app.api.websocket import message_websocket_endpoint
from app.core.config import settings
from app.core.error_handlers import setup_exception_handlers
from app.core.logging import app_logger
from app.core.middleware import setup_middlewares

# 加载环境变量
load_dotenv()
app_logger.debug("环境变量已加载")

# 确保必要的目录存在
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# 动态获取上传目录，支持测试环境
upload_dir = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(upload_dir, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时执行初始化操作，关闭时执行清理操作
    """
    # 启动时执行
    app_logger.info(f"应用启动: {settings.APP_NAME} v{settings.APP_VERSION}")
    app_logger.debug(f"数据库: {settings.DATABASE_URL}")

    yield

    # 关闭时执行
    app_logger.info("应用已关闭")


# 创建 FastAPI 应用实例
app = FastAPI(title=settings.APP_NAME, description="MaiMNP后端服务", version=settings.APP_VERSION, lifespan=lifespan)

# 设置中间件
setup_middlewares(app)

# 设置异常处理器
setup_exception_handlers(app)

# 注册 API 路由
app.include_router(api_router, prefix="/api")

# 设置静态文件路由
# 导入静态文件安全服务（临时使用根目录的模块，后续会迁移）
try:
    from static_routes import setup_static_routes

    setup_static_routes(app)
except ImportError:
    # 如果 static_routes 不存在，使用内联实现
    from fastapi import HTTPException, Request
    from fastapi.responses import FileResponse

    @app.get("/uploads/avatars/{file_path:path}")
    async def serve_avatar_route(file_path: str, request: Request):
        """头像文件服务路由"""
        avatars_dir = Path("uploads/avatars")
        avatars_dir.mkdir(parents=True, exist_ok=True)

        # 安全检查：防止路径遍历
        if ".." in file_path:
            raise HTTPException(status_code=403, detail="Invalid file path")

        full_path = avatars_dir / file_path

        # 确保文件在允许的目录内
        try:
            full_path.resolve().relative_to(avatars_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid file path") from None

        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="Avatar not found")

        return FileResponse(str(full_path))

    app_logger.debug("静态文件路由已设置")


@app.get("/")
async def root():
    """根路径端点"""
    return {"message": "MaiMNP Backend API"}


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


# 注册 WebSocket 端点
@app.websocket("/api/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket 端点用于实时消息推送

    Args:
        websocket: WebSocket 连接对象
        token: JWT 认证令牌
    """
    await message_websocket_endpoint(websocket, token)


if __name__ == "__main__":
    """直接运行此文件时的入口点"""
    exit_code = 0
    try:
        app_logger.info(f"服务器启动: http://{settings.HOST}:{settings.PORT}")
        uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level="critical")
    except Exception as e:
        app_logger.error(f"主程序异常: {str(e)}")
        app_logger.error(traceback.format_exc())
        exit_code = 1
    finally:
        sys.exit(exit_code)
