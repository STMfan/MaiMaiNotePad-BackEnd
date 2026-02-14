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

os.makedirs('data', exist_ok=True)
os.makedirs('logs', exist_ok=True)

app = FastAPI(title="MaiMNP Backend", description="MaiMNP后端服务", version="1.0.0")
setup_middlewares(app)
app.include_router(api_router, prefix="/api")
setup_static_routes(app)
userList = load_users()
app_logger.info(f"Loaded {len(userList)} users")
db_manager = sqlite_db_manager
app_logger.info("SQLite database manager initialized")


@app.get("/")
async def root():
    return {"message": "MaiMNP Backend API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == '__main__':
    exit_code = 0
    try:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        app_logger.info('Server started')
        app_logger.info(f'🌐 访问地址: http://{host}:{port}')
        uvicorn.run(app, host=host, port=port, log_level="critical")
    except Exception as e:
        app_logger.error(f"主程序发生异常: {str(e)} {str(traceback.format_exc())}")
        exit_code = 1
    finally:
        sys.exit(exit_code)
