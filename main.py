# 导入用户管理模块
from user_management import load_users
from api_routes import api_router
from database_models import sqlite_db_manager
from fastapi import FastAPI
import uvicorn
from logger import log
import os
import sys
import traceback
from passlib.context import CryptContext
from dotenv import load_dotenv

# 导入新的日志和错误处理模块
from logging_config import app_logger
from error_handlers import setup_exception_handlers

# 导入中间件配置和静态文件路由模块
from middleware_config import setup_middlewares
from static_routes import setup_static_routes

# 加载环境变量
log("加载环境变量", importance='info')
load_dotenv()

host = os.getenv("HOST", "0.0.0.0")
port = int(os.getenv("PORT", "9278"))

if __name__ == '__main__':
    exit_code = 0  # 用于记录程序最终的退出状态
    try:    
        # 创建必要的目录
        os.makedirs('data', exist_ok=True)
        os.makedirs('logs', exist_ok=True)

        # 配置密码哈希（虽然当前未使用，但保留以备将来需要）
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # 初始化FastAPI应用
        app = FastAPI(title="MaiMNP Backend",
                    description="MaiMNP后端服务", version="1.0.0")

        # 配置所有中间件（速率限制、CORS、错误处理等）
        setup_middlewares(app)

        # 包含API路由，添加/api前缀
        app.include_router(api_router, prefix="/api")
        
        # 设置静态文件路由（安全的头像服务）
        setup_static_routes(app)

        # 加载用户数据
        userList = load_users()
        app_logger.info(f"Loaded {len(userList)} users")

        # 初始化数据库管理器
        db_manager = sqlite_db_manager
        app_logger.info("SQLite database manager initialized")

        # 根路径


        @app.get("/")
        async def root():
            return {"message": "MaiMNP Backend API"}

        # 健康检查


        @app.get("/health")
        async def health_check():
            return {"status": "healthy"}

        # 认证路由已在api_routes.py中定义，无需重复定义

        app_logger.info('Server started')
        app_logger.info(f'🌐 访问地址: http://{host}:{port}')
        uvicorn.run(app, host=host, port=port, log_level="critical")
    except Exception as e:
        app_logger.error(f"主程序发生异常: {str(e)} {str(traceback.format_exc())}")
        exit_code = 1  # 标记发生错误
    finally:
        sys.exit(exit_code)  # <--- 使用记录的退出码