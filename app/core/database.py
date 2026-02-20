"""
数据库连接与会话管理模块

提供 SQLAlchemy 引擎创建、会话工厂和依赖注入支持。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from contextlib import contextmanager
from typing import Generator

from app.core.config import settings


# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True,
    echo=False
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明式模型基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（用于 FastAPI 依赖注入）。
    
    Yields:
        Session: SQLAlchemy 数据库会话
        
    示例:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    获取数据库会话（上下文管理器方式）。
    
    Yields:
        Session: SQLAlchemy 数据库会话
        
    示例:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
