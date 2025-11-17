# 导入用户管理模块
from user_management import load_users, get_user_by_id, get_user_by_username, get_user_by_credentials, create_user, update_user_role
from user_management import get_current_user, get_admin_user, get_moderator_user
from api_routes import router as api_router
from file_upload import file_upload_service
from models import KnowledgeBase, PersonaCard, Message, StarRecord
from database_models import sqlite_db_manager
from jwt_utils import create_user_token
from pathlib import Path
import logging
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, status
from typing import Optional, List, Dict
from fastapi import FastAPI
import uvicorn
from logger import log
import os
import sys
import json
import uuid
import traceback
from datetime import datetime
from passlib.context import CryptContext
from dotenv import load_dotenv

# 导入新的日志和错误处理模块
from logging_config import setup_logger, app_logger, log_exception, log_api_request
from error_handlers import ErrorHandlerMiddleware, setup_exception_handlers, AuthenticationError, APIError

# 加载环境变量
log("加载环境变量", importance='info')
load_dotenv()

host = os.getenv("HOST", "0.0.0.0")
port = int(os.getenv("PORT", "9278"))

if __name__ == '__main__':
    exit_code = 0  # 用于记录程序最终的退出状态
    try:    
        # 创建数据目录
        os.makedirs('data', exist_ok=True)

        # 初始化密码加密上下文
        # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # 导入必要的库

        # 导入自定义模块

        # 配置日志
        # 使用新的日志系统，替换原有的简单日志配置
        # logging.basicConfig(level=logging.INFO)
        # logger = logging.getLogger(__name__)

        # 创建日志目录
        os.makedirs('logs', exist_ok=True)

        # 配置密码哈希
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # 初始化FastAPI应用
        app = FastAPI(title="MaiMNP Backend",
                    description="MaiMNP后端服务", version="1.0.0")

        # 添加错误处理中间件
        app.add_middleware(ErrorHandlerMiddleware)

        # 添加CORS中间件
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 设置异常处理器
        setup_exception_handlers(app)

        # 包含API路由，添加/api前缀
        app.include_router(api_router, prefix="/api")

        # 加载用户数据
        userList = load_users()
        app_logger.info(f"Loaded {len(userList)} users")

        # 初始化数据库管理器
        db_manager = sqlite_db_manager
        app_logger.info("SQLite database manager initialized")

        # 安全认证
        security = HTTPBearer()

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