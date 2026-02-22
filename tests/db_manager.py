"""
测试数据库管理器

为测试提供统一的数据库管理，支持：
- 多个独立的测试数据库实例（用于并行测试）
- 自动清理和重置功能
- 连接池管理
"""

import os
from typing import Optional, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool


class TestDatabaseManager:
    """管理用于并行测试的测试数据库实例"""

    def __init__(self, database_url: Optional[str] = None):
        """
        初始化数据库管理器

        参数：
            database_url: 数据库 URL。如果为 None，则使用环境变量中的 DATABASE_URL
        """
        self.database_url = database_url or os.environ.get("DATABASE_URL", "sqlite:///./test.db")
        self.engine = None
        self.session_factory = None
        self._setup_engine()

    def _setup_engine(self):
        """使用适当的配置设置数据库引擎"""
        if self.database_url.startswith("sqlite"):
            # SQLite 测试配置
            # 使用 StaticPool 为内存数据库维护单个连接
            # check_same_thread=False 允许多线程访问
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False,  # 设置为 True 以进行 SQL 调试
            )

            # 为 SQLite 启用外键约束
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        else:
            # PostgreSQL 或其他数据库配置
            self.engine = create_engine(
                self.database_url, pool_pre_ping=True, pool_size=5, max_overflow=10, echo=False  # 使用前验证连接
            )

        # 创建会话工厂
        self.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """创建所有数据库表"""
        from app.models.database import Base

        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """删除所有数据库表"""
        from app.models.database import Base

        Base.metadata.drop_all(bind=self.engine)

    def reset_database(self):
        """通过删除并重新创建所有表来重置数据库"""
        self.drop_tables()
        self.create_tables()

    def get_session(self) -> Session:
        """获取新的数据库会话"""
        return self.session_factory()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        为数据库操作提供事务作用域

        用法：
            with db_manager.session_scope() as session:
                # 执行数据库操作
                pass
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def cleanup_session(self, session: Session):
        """
        清理会话中的所有数据（用于测试隔离）

        参数：
            session: 要清理的数据库会话
        """
        from app.models.database import (
            CommentReaction,
            Comment,
            DownloadRecord,
            UploadRecord,
            EmailVerification,
            StarRecord,
            Message,
            PersonaCardFile,
            PersonaCard,
            KnowledgeBaseFile,
            KnowledgeBase,
            User,
        )

        # 按外键依赖的相反顺序删除
        session.query(CommentReaction).delete()
        session.query(Comment).delete()
        session.query(DownloadRecord).delete()
        session.query(UploadRecord).delete()
        session.query(EmailVerification).delete()
        session.query(StarRecord).delete()
        session.query(Message).delete()
        session.query(PersonaCardFile).delete()
        session.query(PersonaCard).delete()
        session.query(KnowledgeBaseFile).delete()
        session.query(KnowledgeBase).delete()
        session.query(User).delete()
        session.commit()

    def close(self):
        """关闭数据库引擎并清理资源"""
        if self.engine:
            self.engine.dispose()


class ParallelTestDatabaseManager:
    """
    用于为并行测试创建隔离数据库实例的管理器

    每个测试 worker 获取自己的数据库实例以避免冲突
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        初始化并行数据库管理器

        参数：
            base_url: 基础数据库 URL 模板
        """
        self.base_url = base_url or os.environ.get("DATABASE_URL", "sqlite:///./test.db")
        self.managers = {}

    def get_manager_for_worker(self, worker_id: str) -> TestDatabaseManager:
        """
        获取或创建特定测试 worker 的数据库管理器

        参数：
            worker_id: 测试 worker 的唯一标识符

        返回：
            此 worker 的 TestDatabaseManager 实例
        """
        if worker_id not in self.managers:
            # 为此 worker 创建唯一的数据库 URL
            if self.base_url.startswith("sqlite"):
                # 对于 SQLite，为每个 worker 创建单独的文件
                db_url = f"sqlite:///./test_{worker_id}.db"
            else:
                # 对于 PostgreSQL，将 worker_id 附加到数据库名称
                # 例如，postgresql://user:pass@host/testdb_worker1
                db_url = f"{self.base_url}_{worker_id}"

            manager = TestDatabaseManager(db_url)
            manager.create_tables()
            self.managers[worker_id] = manager

        return self.managers[worker_id]

    def cleanup_all(self):
        """清理所有 worker 数据库"""
        for manager in self.managers.values():
            manager.close()
        self.managers.clear()


# 全局数据库管理器实例
_db_manager: Optional[TestDatabaseManager] = None


def get_test_db_manager() -> TestDatabaseManager:
    """获取或创建全局测试数据库管理器"""
    global _db_manager
    if _db_manager is None:
        _db_manager = TestDatabaseManager()
        _db_manager.create_tables()
    return _db_manager
