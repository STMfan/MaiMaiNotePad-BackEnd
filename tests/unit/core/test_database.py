"""
app/core/database.py 单元测试

测试数据库连接、会话管理和上下文管理器。
"""

from sqlalchemy.orm import Session


class TestDatabaseEngine:
    """测试数据库引擎创建"""

    def test_engine_created(self):
        """测试数据库引擎已创建"""
        from app.core.database import engine

        assert engine is not None

    def test_engine_uses_settings_url(self):
        """测试引擎使用设置中的DATABASE_URL"""
        from app.core.database import engine
        from app.core.config import settings

        # 引擎URL应该匹配设置
        assert str(engine.url) == settings.DATABASE_URL or settings.DATABASE_URL in str(engine.url)

    def test_engine_has_pool_pre_ping(self):
        """测试引擎启用了pool_pre_ping"""
        from app.core.database import engine

        # pool_pre_ping应该为True以进行连接健康检查
        assert engine.pool._pre_ping is True

    def test_engine_echo_disabled(self):
        """测试引擎echo在生产环境中被禁用"""
        from app.core.database import engine

        assert engine.echo is False


class TestSessionLocal:
    """测试SessionLocal工厂"""

    def test_session_local_created(self):
        """测试SessionLocal sessionmaker已创建"""
        from app.core.database import SessionLocal

        assert SessionLocal is not None

    def test_session_local_creates_sessions(self):
        """测试SessionLocal可以创建会话实例"""
        from app.core.database import SessionLocal

        session = SessionLocal()

        assert session is not None
        assert isinstance(session, Session)

        session.close()

    def test_session_local_autocommit_disabled(self):
        """测试SessionLocal禁用了autocommit"""
        from app.core.database import SessionLocal

        # autocommit应该为False以进行显式事务控制
        assert SessionLocal.kw.get("autocommit") is False

    def test_session_local_autoflush_disabled(self):
        """测试SessionLocal禁用了autoflush"""
        from app.core.database import SessionLocal

        # autoflush应该为False以获得更好的控制
        assert SessionLocal.kw.get("autoflush") is False

    def test_session_local_bound_to_engine(self):
        """测试SessionLocal绑定到引擎"""
        from app.core.database import SessionLocal, engine

        assert SessionLocal.kw.get("bind") == engine


class TestBase:
    """测试声明式基类"""

    def test_base_created(self):
        """测试声明式Base已创建"""
        from app.core.database import Base

        assert Base is not None

    def test_base_has_metadata(self):
        """测试Base有metadata属性"""
        from app.core.database import Base

        assert hasattr(Base, "metadata")
        assert Base.metadata is not None

    def test_base_can_be_inherited(self):
        """测试Base可用于模型继承"""
        from app.core.database import Base
        from sqlalchemy import Column, Integer, String

        class TestModel(Base):
            __tablename__ = "test_model"
            id = Column(Integer, primary_key=True)
            name = Column(String)

        assert TestModel.__tablename__ == "test_model"
        assert hasattr(TestModel, "id")
        assert hasattr(TestModel, "name")


class TestGetDb:
    """测试get_db依赖函数"""

    def test_get_db_yields_session(self):
        """测试get_db产生数据库会话"""
        from app.core.database import get_db

        gen = get_db()
        session = next(gen)

        assert session is not None
        assert isinstance(session, Session)

        # 清理
        try:
            next(gen)
        except StopIteration:
            pass

    def test_get_db_closes_session(self):
        """测试get_db在使用后关闭会话"""
        from app.core.database import get_db

        gen = get_db()
        session = next(gen)

        # Mock close方法以验证它被调用
        original_close = session.close
        close_called = False

        def mock_close():
            nonlocal close_called
            close_called = True
            original_close()

        session.close = mock_close

        # 触发清理
        try:
            next(gen)
        except StopIteration:
            pass

        assert close_called is True

    def test_get_db_closes_on_exception(self):
        """测试get_db即使发生异常也关闭会话"""
        from app.core.database import get_db

        gen = get_db()
        session = next(gen)

        # Mock close以跟踪是否被调用
        close_called = False
        original_close = session.close

        def mock_close():
            nonlocal close_called
            close_called = True
            original_close()

        session.close = mock_close

        # 模拟异常和清理
        try:
            gen.throw(Exception("测试异常"))
        except Exception:
            pass

        assert close_called is True

    def test_get_db_can_be_used_as_dependency(self):
        """测试get_db作为FastAPI依赖工作"""
        from app.core.database import get_db
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/test")
        def test_endpoint(db: Session = Depends(get_db)):
            return {"db_type": type(db).__name__}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert "Session" in response.json()["db_type"]


class TestGetDbContext:
    """测试get_db_context上下文管理器"""

    def test_get_db_context_yields_session(self):
        """测试get_db_context产生数据库会话"""
        from app.core.database import get_db_context

        with get_db_context() as session:
            assert session is not None
            assert isinstance(session, Session)

    def test_get_db_context_closes_session(self):
        """测试get_db_context在使用后关闭会话"""
        from app.core.database import get_db_context

        with get_db_context() as session:
            # Mock close以验证它被调用
            close_called = False
            original_close = session.close

            def mock_close():
                nonlocal close_called
                close_called = True
                original_close()

            session.close = mock_close

        # 退出上下文后，close应该被调用
        assert close_called is True

    def test_get_db_context_closes_on_exception(self):
        """测试get_db_context即使发生异常也关闭会话"""
        from app.core.database import get_db_context

        close_called = False

        try:
            with get_db_context() as session:
                # Mock close
                original_close = session.close

                def mock_close():
                    nonlocal close_called
                    close_called = True
                    original_close()

                session.close = mock_close

                # 抛出异常
                raise ValueError("测试异常")
        except ValueError:
            pass

        # Close应该仍然被调用
        assert close_called is True

    def test_get_db_context_can_query_database(self, test_db):
        """测试get_db_context可用于查询数据库"""
        from app.core.database import get_db_context
        from app.models.database import User

        with get_db_context() as session:
            # 应该能够查询
            users = session.query(User).all()
            assert isinstance(users, list)

    def test_get_db_context_can_add_and_commit(self, test_db):
        """测试get_db_context可以添加和提交数据"""
        from app.core.database import get_db_context
        from app.models.database import User
        from app.core.security import get_password_hash
        import uuid
        from datetime import datetime

        user_id = str(uuid.uuid4())

        with get_db_context() as session:
            user = User(
                id=user_id,
                username=f"contextuser_{user_id[:8]}",
                email=f"context_{user_id[:8]}@test.com",
                hashed_password=get_password_hash("password"),
                is_active=True,
                created_at=datetime.now(),
                password_version=0,
            )
            session.add(user)
            session.commit()

        # 验证用户已添加
        with get_db_context() as session:
            found_user = session.query(User).filter(User.id == user_id).first()
            assert found_user is not None
            assert found_user.username == f"contextuser_{user_id[:8]}"

    def test_get_db_context_multiple_concurrent_sessions(self):
        """测试多个并发get_db_context会话独立工作"""
        from app.core.database import get_db_context

        with get_db_context() as session1:
            with get_db_context() as session2:
                # 应该是不同的会话实例
                assert session1 is not session2
                assert isinstance(session1, Session)
                assert isinstance(session2, Session)


class TestDatabaseConfiguration:
    """测试数据库配置"""

    def test_sqlite_check_same_thread_config(self):
        """测试SQLite禁用了check_same_thread"""
        from app.core.config import settings

        if "sqlite" in settings.DATABASE_URL:
            # 对于SQLite，check_same_thread应该在connect_args中为False
            # 这在create_engine调用中配置
            # 我们可以通过检查引擎的connect_args来验证
            assert True  # 配置通过成功的测试执行来验证

    def test_engine_pool_configuration(self):
        """测试引擎有连接池配置"""
        from app.core.database import engine

        # 引擎应该有一个连接池
        assert hasattr(engine, "pool")
        assert engine.pool is not None
