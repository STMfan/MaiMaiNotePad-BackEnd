import pytest
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Union, List
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from hypothesis import settings, Verbosity, HealthCheck

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set TEST_LANGUAGE to English for all tests
os.environ["TEST_LANGUAGE"] = "en"

# 设置默认的测试数据库 URL（在 pytest_configure 之前）
# 这确保当 app.main 被导入时，它使用测试数据库而不是生产数据库
# pytest_configure 会为每个 worker 覆盖这个值
if "DATABASE_URL" not in os.environ:
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
    os.environ["DATABASE_URL"] = f"sqlite:///./tests/test_{worker_id}.db"

# 设置测试专用的上传目录（在导入应用代码之前）
# 这确保当 app.core.config 被导入时，它使用测试上传目录而不是生产目录
if "UPLOAD_DIR" not in os.environ:
    os.environ["UPLOAD_DIR"] = "test_uploads"

# 从 .test_env 或 .test_env.template 加载测试配置
from tests.fixtures.config import test_config  # noqa: E402

# ============================================================================
# Pytest Configuration Options
# ============================================================================


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--run-parallel-isolation",
        action="store_true",
        default=False,
        help="Run parallel isolation tests (normally skipped in main test suite)",
    )


# ============================================================================
# Pytest Hooks for Per-Worker Database Isolation
# ============================================================================


def pytest_configure(config):
    """配置 pytest，为每个 worker 创建独立的数据库和上传目录"""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")

    # 为每个 worker 使用独立的数据库文件（在 tests 目录内）
    test_db_url = f"sqlite:///./tests/test_{worker_id}.db"
    os.environ["DATABASE_URL"] = test_db_url

    # 确保测试专用的上传目录已设置（应该在模块级别已经设置了）
    if "UPLOAD_DIR" not in os.environ:
        os.environ["UPLOAD_DIR"] = "test_uploads"

    print(f"Worker {worker_id} using database: {test_db_url}")
    print(f"Worker {worker_id} using upload directory: {os.environ['UPLOAD_DIR']}")

    # 确保测试数据库有表结构
    # 这样即使测试直接创建 TestClient 而不使用 fixture，也能正常工作
    from sqlalchemy import create_engine, inspect
    from app.models.database import Base

    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})

    # 检查表是否已存在，避免重复创建
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if not existing_tables:
        # 只在表不存在时创建
        Base.metadata.create_all(bind=engine)

    engine.dispose()


def pytest_collection_modifyitems(config, items):
    """修改测试收集，将标记为 serial 的测试分组"""
    # 将 serial 标记的测试移到最后，并确保它们在同一个 worker 中串行运行
    serial_tests = []
    parallel_tests = []

    for item in items:
        if item.get_closest_marker("serial"):
            serial_tests.append(item)
            # 添加 xdist_group 标记，确保所有 serial 测试在同一个 worker 中运行
            # 这样它们就会真正串行执行
            item.add_marker(pytest.mark.xdist_group(name="serial_group"))
        else:
            parallel_tests.append(item)

    # 重新排序：先并行测试，后串行测试
    items[:] = parallel_tests + serial_tests


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束后清理所有测试相关文件"""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")

    if worker_id != "master":
        _cleanup_worker_files(worker_id)
    else:
        _cleanup_master_files()
        _cleanup_test_artifacts()
        _cleanup_upload_directory()


def _safe_remove_file(file_path: str, max_retries: int = 3, retry_delay: float = 0.1) -> bool:
    """
    安全删除文件，带重试逻辑和文件存在性检查

    Args:
        file_path: 要删除的文件路径
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）

    Returns:
        bool: 删除成功返回 True，失败返回 False
    """
    path = Path(file_path)

    # 检查文件是否存在
    if not path.exists():
        return True  # 文件不存在，视为成功

    # 尝试删除文件，带重试逻辑
    for attempt in range(max_retries):
        if _try_remove_file(path, attempt, max_retries, retry_delay, file_path):
            return True

    return False


def _try_remove_file(path: Path, attempt: int, max_retries: int, retry_delay: float, file_path: str) -> bool:
    """尝试删除单个文件"""
    import time

    try:
        # 检查文件是否仍在使用
        if not _check_file_available(path, attempt, max_retries, retry_delay, file_path):
            return False

        # 删除文件
        path.unlink()
        return True

    except FileNotFoundError:
        # 文件在检查后被其他进程删除，视为成功
        return True
    except Exception as e:
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
        else:
            print(f"  ✗ Failed to remove {file_path} after {max_retries} attempts: {e}")
            return False

    return False


def _check_file_available(path: Path, attempt: int, max_retries: int, retry_delay: float, file_path: str) -> bool:
    """检查文件是否可用（未被锁定）"""
    import time

    try:
        with open(path, "a"):
            pass  # 文件可以打开，说明没有被独占锁定
        return True
    except (IOError, OSError):
        # 文件被锁定，等待后重试
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
            return False
        else:
            print(f"  ⚠ File still in use, skipping: {file_path}")
            return False


def _cleanup_worker_files(worker_id: str):
    """清理 worker 的数据库文件"""
    import glob

    db_patterns = [
        f"./tests/test_{worker_id}.db",
        f"./tests/test_{worker_id}.db-shm",
        f"./tests/test_{worker_id}.db-wal",
    ]

    for pattern in db_patterns:
        for file_path in glob.glob(pattern):
            if _safe_remove_file(file_path):
                print(f"✓ Worker {worker_id} cleaned up: {file_path}")


def _cleanup_master_files():
    """清理 master 的数据库文件"""
    import glob

    master_db_patterns = [
        "./tests/test_master.db",
        "./tests/test_master.db-shm",
        "./tests/test_master.db-wal",
    ]

    for pattern in master_db_patterns:
        for file_path in glob.glob(pattern):
            if _safe_remove_file(file_path):
                print(f"✓ Master cleaned up: {file_path}")


def _cleanup_test_artifacts():
    """清理所有遗留的测试文件"""
    import glob

    cleanup_patterns = [
        "./tests/test_gw*.db",  # Worker 数据库文件
        "./tests/test_gw*.db-shm",
        "./tests/test_gw*.db-wal",
        "./tests/.coverage.*",
        "./tests/coverage.json",
        "./tests/test_results_*.log",
        "./tests/tests.log",
    ]

    print("\n🧹 Master cleaning up test artifacts...")
    cleaned_count = 0

    for pattern in cleanup_patterns:
        for file_path in glob.glob(pattern):
            if _safe_remove_file(file_path):
                cleaned_count += 1
                print(f"  ✓ Removed: {file_path}")

    if cleaned_count > 0:
        print(f"✨ Cleaned up {cleaned_count} test artifact(s)\n")
    else:
        print("✨ No test artifacts to clean up\n")


def _cleanup_upload_directory():
    """清理测试上传目录"""
    import shutil

    upload_dir = os.environ.get("UPLOAD_DIR", "test_uploads")
    if os.path.exists(upload_dir):
        try:
            shutil.rmtree(upload_dir)
            print(f"✨ Cleaned up test upload directory: {upload_dir}\n")
        except Exception as e:
            print(f"⚠ Failed to clean up upload directory {upload_dir}: {e}\n")


# ============================================================================
# Configuration
# ============================================================================

# 优化测试环境的密码哈希速度
# 从配置文件读取 bcrypt rounds，如果未设置则默认为 4（测试环境）
# 这样可以显著提升测试速度（21倍提升：451s → 21s）
if "BCRYPT_ROUNDS" not in os.environ:
    bcrypt_rounds = test_config.get("BCRYPT_ROUNDS", "4")
    os.environ["BCRYPT_ROUNDS"] = bcrypt_rounds

# 配置 hypothesis 配置文件用于基于属性的测试
# CI 配置文件：100 次迭代，详细输出以获得详细的测试结果
settings.register_profile(
    "ci",
    max_examples=100,
    verbosity=Verbosity.verbose,
    deadline=None,  # 禁用截止时间以避免 CI 中的不稳定测试
    suppress_health_check=[HealthCheck.too_slow],
)

# 开发配置文件：10 次迭代，在开发过程中获得更快的反馈
settings.register_profile("dev", max_examples=10, verbosity=Verbosity.normal, deadline=None)

# 默认配置文件：使用 CI 配置文件以确保至少 100 次迭代
# 可以通过 HYPOTHESIS_PROFILE 环境变量覆盖
settings.load_profile(test_config.get("HYPOTHESIS_PROFILE", "ci"))

# 设置环境变量后导入
from app.models.database import (  # noqa: E402
    Base,
    User,
    EmailVerification,
    KnowledgeBase,
    KnowledgeBaseFile,
    PersonaCard,
    PersonaCardFile,
    Message,
    StarRecord,
    UploadRecord,
    DownloadRecord,
    Comment,
    CommentReaction,
)
from app.core.database import get_db  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from tests.fixtures.data_factory import TestDataFactory  # noqa: E402
from tests.helpers.boundary_generator import BoundaryValueGenerator  # noqa: E402

# ============================================================================
# Fixture Caching Optimization
# ============================================================================

# 缓存常用密码的哈希值，避免重复计算
# 这可以显著提升测试速度，因为密码哈希是一个昂贵的操作
# 使用 worker-specific 字典以避免并行测试中的状态污染
_PASSWORD_HASH_CACHE = {}


def get_cached_password_hash(password: str) -> str:
    """获取缓存的密码哈希，如果不存在则计算并缓存"""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")

    # 为每个 worker 创建独立的缓存
    if worker_id not in _PASSWORD_HASH_CACHE:
        _PASSWORD_HASH_CACHE[worker_id] = {}

    worker_cache = _PASSWORD_HASH_CACHE[worker_id]
    if password not in worker_cache:
        worker_cache[password] = get_password_hash(password)
    return worker_cache[password]


# 缓存数据库引擎和会话工厂（worker级别）
# 避免每个测试都重新创建引擎和会话工厂
# 使用 worker-specific 字典以避免并行测试中的状态污染
_DB_ENGINE_CACHE = {}
_SESSION_FACTORY_CACHE = {}


def get_cached_db_engine():
    """获取缓存的数据库引擎"""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")

    # 为每个 worker 创建独立的引擎
    if worker_id not in _DB_ENGINE_CACHE:
        _DB_ENGINE_CACHE[worker_id] = create_engine(
            os.environ["DATABASE_URL"], connect_args={"timeout": 30, "check_same_thread": False}
        )

        # 为 SQLite 启用 WAL 模式以提高并发性能
        @event.listens_for(_DB_ENGINE_CACHE[worker_id], "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        # 创建所有表（只需要一次）
        Base.metadata.create_all(bind=_DB_ENGINE_CACHE[worker_id])

    return _DB_ENGINE_CACHE[worker_id]


def get_cached_session_factory():
    """获取缓存的会话工厂"""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")

    # 为每个 worker 创建独立的会话工厂
    if worker_id not in _SESSION_FACTORY_CACHE:
        engine = get_cached_db_engine()
        _SESSION_FACTORY_CACHE[worker_id] = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return _SESSION_FACTORY_CACHE[worker_id]


def override_get_db():
    """覆盖数据库依赖用于测试"""
    # 动态获取当前 worker 的会话工厂，而不是使用模块级别的全局变量
    # 这确保每个 worker 使用自己的数据库连接
    SessionLocal = get_cached_session_factory()
    try:
        db = SessionLocal()
        # 调试：验证我们使用的是正确的数据库
        worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
        db_url = os.environ.get("DATABASE_URL", "unknown")
        print(f"[override_get_db] Worker: {worker_id}, DB URL: {db_url}")
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_db() -> Session:
    """创建测试数据库会话"""
    # 动态获取当前 worker 的会话工厂
    SessionLocal = get_cached_session_factory()
    # 使用简单的会话，不使用事务隔离，用于集成测试
    session = SessionLocal()

    try:
        yield session
    finally:
        try:
            # 首先回滚所有事务，确保会话处于干净状态
            # 无论事务是否活动，都执行回滚以确保完全清理
            session.rollback()

            # 然后分离所有对象，避免在删除时刷新已删除的对象
            session.expunge_all()

            # 测试后清理所有数据（按外键依赖的相反顺序）
            # 先删除子表（有外键的表），再删除父表
            # 正确的删除顺序（遵循外键约束）：
            # CommentReaction → Comment → DownloadRecord → UploadRecord →
            # EmailVerification → StarRecord → Message → PersonaCardFile →
            # PersonaCard → KnowledgeBaseFile → KnowledgeBase → User
            try:
                session.query(CommentReaction).delete()  # 依赖 Comment
                session.query(Comment).delete()  # 依赖 User
                session.query(DownloadRecord).delete()  # 无外键依赖
                session.query(UploadRecord).delete()  # 依赖 User
                session.query(EmailVerification).delete()  # 无外键依赖
                session.query(StarRecord).delete()  # 依赖 User
                session.query(Message).delete()  # 依赖 User (sender_id, recipient_id)
                session.query(PersonaCardFile).delete()  # 依赖 PersonaCard
                session.query(PersonaCard).delete()  # 依赖 User
                session.query(KnowledgeBaseFile).delete()  # 依赖 KnowledgeBase
                session.query(KnowledgeBase).delete()  # 依赖 User
                session.query(User).delete()  # 父表，最后删除
                session.commit()
            except Exception as delete_error:
                # 详细记录删除失败的错误
                print(f"Error during data deletion in test_db cleanup: {delete_error}")
                print(f"Error type: {type(delete_error).__name__}")
                print(f"Transaction state before rollback: in_transaction={session.in_transaction()}")
                session.rollback()
                raise
        except Exception as e:
            # 记录清理错误但不抛出，确保会话总是被关闭
            print(f"Error during test_db cleanup: {e}")
            print(f"Error type: {type(e).__name__}")
            try:
                if session.in_transaction():
                    session.rollback()
            except Exception as rollback_error:
                print(f"Error during rollback: {rollback_error}")
        finally:
            session.close()


@pytest.fixture(scope="function")
def factory(test_db: Session):
    """创建 TestDataFactory 实例"""
    return TestDataFactory(test_db)


@pytest.fixture(scope="session")
def boundary_generator():
    """
    提供 BoundaryValueGenerator 实例作为 pytest fixture

    使用 session 作用域以在所有测试中重用同一个实例，
    因为生成器是无状态的，可以安全地共享。

    Example:
        def test_my_function(boundary_generator):
            boundaries = boundary_generator.generate_string_boundaries()
            for boundary in boundaries:
                # 测试逻辑
                pass
    """
    return BoundaryValueGenerator()


@pytest.fixture(scope="function")
def null_boundaries(boundary_generator):
    """
    提供空值边界值的 pytest fixture

    Example:
        def test_null_handling(null_boundaries):
            for boundary in null_boundaries:
                result = my_function(boundary.value)
                assert result is not None or boundary.value is None
    """
    return boundary_generator.generate_null_values()


@pytest.fixture(scope="function")
def string_boundaries(boundary_generator):
    """
    提供字符串边界值的 pytest fixture（默认最大长度 10000）

    Example:
        def test_string_processing(string_boundaries):
            for boundary in string_boundaries:
                if boundary.expected_behavior == "raise_exception":
                    with pytest.raises(Exception):
                        process_string(boundary.value)
    """
    return boundary_generator.generate_string_boundaries()


@pytest.fixture(scope="function")
def integer_boundaries(boundary_generator):
    """
    提供整数边界值的 pytest fixture

    Example:
        def test_integer_validation(integer_boundaries):
            for boundary in integer_boundaries:
                result = validate_integer(boundary.value)
                # 验证逻辑
    """
    return boundary_generator.generate_integer_boundaries()


@pytest.fixture(scope="function")
def float_boundaries(boundary_generator):
    """
    提供浮点数边界值的 pytest fixture

    Example:
        def test_float_calculation(float_boundaries):
            for boundary in float_boundaries:
                if not math.isnan(boundary.value):
                    result = calculate(boundary.value)
                    assert isinstance(result, float)
    """
    return boundary_generator.generate_float_boundaries()


@pytest.fixture(scope="function")
def list_boundaries(boundary_generator):
    """
    提供列表边界值的 pytest fixture

    Example:
        def test_list_processing(list_boundaries):
            for boundary in list_boundaries:
                result = process_list(boundary.value)
                assert isinstance(result, list)
    """
    return boundary_generator.generate_list_boundaries()


@pytest.fixture(scope="function")
def dict_boundaries(boundary_generator):
    """
    提供字典边界值的 pytest fixture

    Example:
        def test_dict_processing(dict_boundaries):
            for boundary in dict_boundaries:
                result = process_dict(boundary.value)
                assert isinstance(result, dict)
    """
    return boundary_generator.generate_dict_boundaries()


@pytest.fixture(scope="function")
def test_user(test_db: Session):
    """创建具有唯一邮箱的测试用户"""
    # 生成唯一邮箱以避免 UNIQUE 约束失败
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        id=str(uuid.uuid4()),
        username=f"testuser_{unique_id}",
        email=f"test_{unique_id}@example.com",
        hashed_password=get_cached_password_hash("testpassword123"),  # 使用缓存
        is_active=True,
        is_admin=False,
        is_moderator=False,
        is_super_admin=False,
        created_at=datetime.now(),
        password_version=0,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_user(test_db: Session):
    """创建具有唯一邮箱的测试管理员用户"""
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        id=str(uuid.uuid4()),
        username=f"adminuser_{unique_id}",
        email=f"admin_{unique_id}@example.com",
        hashed_password=get_cached_password_hash("adminpassword123"),  # 使用缓存
        is_active=True,
        is_admin=True,
        is_moderator=False,
        is_super_admin=False,
        created_at=datetime.now(),
        password_version=0,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def moderator_user(test_db: Session):
    """创建具有唯一邮箱的测试审核员用户"""
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        id=str(uuid.uuid4()),
        username=f"moderatoruser_{unique_id}",
        email=f"moderator_{unique_id}@example.com",
        hashed_password=get_cached_password_hash("moderatorpassword123"),  # 使用缓存
        is_active=True,
        is_admin=False,
        is_moderator=True,
        is_super_admin=False,
        created_at=datetime.now(),
        password_version=0,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def super_admin_user(test_db: Session):
    """创建测试超级管理员用户"""
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        id=str(uuid.uuid4()),
        username=f"superadmin_{unique_id}",
        email=f"superadmin_{unique_id}@example.com",
        hashed_password=get_cached_password_hash("superadminpassword123"),
        is_active=True,
        is_admin=True,
        is_moderator=True,
        is_super_admin=True,
        created_at=datetime.now(),
        password_version=0,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


# 仅在应用存在时导入（用于集成测试）
# 仅在应用存在时导入（用于集成测试）
_app_available = False
try:
    from app.main import app

    _app_available = True
except ImportError:
    # 应用不可用，跳过集成测试 fixtures
    app = None


def _setup_test_client_with_db_override():
    """设置测试客户端并配置数据库依赖覆盖

    Returns:
        TestClient: 配置好的测试客户端
    """
    test_client = TestClient(app)
    print("[client fixture] Setting dependency override for get_db")
    print(f"[client fixture] get_db function: {get_db}")
    print(f"[client fixture] override_get_db function: {override_get_db}")
    app.dependency_overrides[get_db] = override_get_db
    print(f"[client fixture] Dependency overrides: {app.dependency_overrides}")
    return test_client


def _cleanup_db_override():
    """清理数据库依赖覆盖"""
    if app is not None:
        app.dependency_overrides.pop(get_db, None)


def _extract_token_from_response(resp_data: dict) -> str:
    """从响应数据中提取访问令牌

    Args:
        resp_data: 响应数据字典

    Returns:
        str: 访问令牌
    """
    if "data" in resp_data:
        return resp_data["data"]["access_token"]
    return resp_data["access_token"]


def _authenticate_user(client: TestClient, username: str, password: str, role_name: str = "用户") -> str:
    """用户认证并获取令牌

    Args:
        client: 测试客户端
        username: 用户名
        password: 密码
        role_name: 角色名称（用于错误消息）

    Returns:
        str: 访问令牌

    Raises:
        Exception: 登录失败时抛出异常
    """
    response = client.post("/api/auth/token", data={"username": username, "password": password})

    if response.status_code != 200:
        raise Exception(f"{role_name}登录失败: {response.status_code} - {response.text}")

    return _extract_token_from_response(response.json())


if _app_available:  # noqa: C901

    @pytest.fixture(scope="function")
    def client():
        """创建未认证的测试客户端"""
        with TestClient(app) as test_client:
            app.dependency_overrides[get_db] = override_get_db
            try:
                yield test_client
            finally:
                _cleanup_db_override()

    @pytest.fixture(scope="function")
    def authenticated_client(test_user, test_db):
        """创建已认证的测试客户端"""
        with TestClient(app) as client:
            app.dependency_overrides[get_db] = override_get_db
            try:
                test_db.refresh(test_user)
                token = _authenticate_user(client, test_user.username, "testpassword123")
                client.headers.update({"Authorization": f"Bearer {token}"})
                yield client
            finally:
                _cleanup_db_override()

    @pytest.fixture(scope="function")
    def admin_client(admin_user, test_db):
        """创建已认证的管理员测试客户端"""
        with TestClient(app) as client:
            app.dependency_overrides[get_db] = override_get_db
            try:
                test_db.refresh(admin_user)
                token = _authenticate_user(client, admin_user.username, "adminpassword123", "管理员")
                client.headers.update({"Authorization": f"Bearer {token}"})
                yield client
            finally:
                _cleanup_db_override()

    @pytest.fixture(scope="function")
    def moderator_client(moderator_user, test_db):
        """创建已认证的审核员测试客户端"""
        with TestClient(app) as client:
            app.dependency_overrides[get_db] = override_get_db
            try:
                test_db.refresh(moderator_user)
                token = _authenticate_user(client, moderator_user.username, "moderatorpassword123", "审核员")
                client.headers.update({"Authorization": f"Bearer {token}"})
                yield client
            finally:
                _cleanup_db_override()

    @pytest.fixture(scope="function")
    def super_admin_client(super_admin_user, test_db):
        """创建已认证的超级管理员测试客户端"""
        with TestClient(app) as client:
            app.dependency_overrides[get_db] = override_get_db
            try:
                test_db.refresh(super_admin_user)
                token = _authenticate_user(client, super_admin_user.username, "superadminpassword123", "超级管理员")
                client.headers.update({"Authorization": f"Bearer {token}"})
                yield client
            finally:
                _cleanup_db_override()


# 用于检查错误响应的辅助函数
def assert_error_response(response, expected_status_codes, expected_message_keywords):
    """
    用于检查 API 错误响应的辅助函数。
    处理 FastAPI 验证错误（422 带 'detail'）和自定义 API 错误（带 'error'）。

    参数：
        response: 来自 TestClient 的响应对象
        expected_status_codes: 预期状态码的整数或整数列表
        expected_message_keywords: 字符串或字符串列表 - 应出现在错误消息中的关键字
    """
    # 将输入规范化为列表
    if isinstance(expected_status_codes, int):
        expected_status_codes = [expected_status_codes]
    if isinstance(expected_message_keywords, str):
        expected_message_keywords = [expected_message_keywords]

    # 检查状态码
    assert (
        response.status_code in expected_status_codes
    ), f"预期状态码在 {expected_status_codes} 中，得到 {response.status_code}"

    data = response.json()

    # 处理 FastAPI 验证错误（422）
    if "detail" in data:
        # FastAPI 验证错误格式：{"detail": [...]}
        detail = data["detail"]
        if isinstance(detail, list):
            # 提取所有错误消息
            error_messages = []
            for error in detail:
                if isinstance(error, dict):
                    error_messages.append(error.get("msg", ""))
                    error_messages.append(str(error.get("loc", "")))
            combined_message = " ".join(error_messages).lower()
        else:
            combined_message = str(detail).lower()

        # 检查是否有任何关键字匹配
        keyword_found = any(keyword.lower() in combined_message for keyword in expected_message_keywords)

        assert keyword_found, f"预期 {expected_message_keywords} 中的一个在错误消息中，得到：{data}"

    # 处理自定义 API 错误
    elif "error" in data:
        # 自定义错误格式：{"success": False, "error": {"message": "..."}}
        error_message = data["error"].get("message", "").lower()

        # 检查是否有任何关键字匹配
        keyword_found = any(keyword.lower() in error_message for keyword in expected_message_keywords)

        assert keyword_found, f"预期 {expected_message_keywords} 中的一个在错误消息中，得到：{error_message}"

    else:
        # 未知错误格式
        raise AssertionError(f"未知的错误响应格式：{data}")


# ============================================================================
# Boundary Testing Helper Functions and Decorators
# ============================================================================


def with_boundary_values(param_type: str, **kwargs):
    """
    装饰器：使用边界值自动参数化测试函数

    这个装饰器会自动生成边界值并将测试函数参数化，
    使得测试函数可以针对所有边界值运行。

    Args:
        param_type: 参数类型 ("string", "integer", "float", "list", "dict", etc.)
        **kwargs: 传递给边界值生成器的额外参数（如 max_length, min_value 等）

    Example:
        @with_boundary_values("string", max_length=50)
        def test_username_validation(boundary_value):
            if boundary_value.expected_behavior == "raise_exception":
                with pytest.raises(ValueError):
                    validate_username(boundary_value.value)
            else:
                result = validate_username(boundary_value.value)
                assert isinstance(result, str)
    """

    def decorator(test_func):
        generator = BoundaryValueGenerator()

        # 根据类型生成边界值
        if param_type == "string":
            boundaries = generator.generate_string_boundaries(**kwargs)
        elif param_type == "integer":
            boundaries = generator.generate_integer_boundaries(**kwargs)
        elif param_type == "float":
            boundaries = generator.generate_float_boundaries(**kwargs)
        elif param_type == "list":
            boundaries = generator.generate_list_boundaries(**kwargs)
        elif param_type == "dict":
            boundaries = generator.generate_dict_boundaries(**kwargs)
        elif param_type == "null":
            boundaries = generator.generate_null_values()
        else:
            raise ValueError(f"Unsupported parameter type: {param_type}")

        # 使用 pytest.mark.parametrize 参数化测试
        return pytest.mark.parametrize("boundary_value", boundaries, ids=[bv.description for bv in boundaries])(
            test_func
        )

    return decorator


def assert_boundary_behavior(boundary_value, test_func, *args, **kwargs):
    """
    辅助函数：根据边界值的预期行为执行测试并进行断言

    这个函数会根据 boundary_value.expected_behavior 自动选择正确的断言方式：
    - "handle_gracefully": 期望函数正常执行，不抛出异常
    - "raise_exception": 期望函数抛出异常
    - "return_none": 期望函数返回 None

    Args:
        boundary_value: BoundaryValue 实例
        test_func: 要测试的函数
        *args: 传递给测试函数的位置参数
        **kwargs: 传递给测试函数的关键字参数

    Returns:
        函数的返回值（如果成功执行）

    Example:
        def test_process_data(boundary_generator):
            boundaries = boundary_generator.generate_string_boundaries()
            for boundary in boundaries:
                result = assert_boundary_behavior(
                    boundary,
                    process_data,
                    boundary.value
                )
                if result is not None:
                    assert isinstance(result, dict)
    """
    if boundary_value.expected_behavior == "raise_exception":
        # 期望抛出异常
        with pytest.raises(Exception):
            test_func(*args, **kwargs)
        return None

    elif boundary_value.expected_behavior == "return_none":
        # 期望返回 None
        result = test_func(*args, **kwargs)
        assert result is None, f"Expected None for {boundary_value.description}, got {result}"
        return result

    else:  # "handle_gracefully"
        # 期望正常处理
        try:
            result = test_func(*args, **kwargs)
            return result
        except Exception as e:
            pytest.fail(
                f"Function should handle {boundary_value.description} gracefully, "
                f"but raised {type(e).__name__}: {e}"
            )


def generate_null_test_cases(function: Callable, param_name: str, include_nested: bool = True):
    """
    便捷函数：为指定函数和参数生成空值测试用例

    这是 BoundaryValueGenerator.generate_null_test_cases 的便捷包装器，
    可以直接在测试中使用而无需创建生成器实例。

    Args:
        function: 要测试的函数
        param_name: 参数名称
        include_nested: 是否包含嵌套结构中的空值测试

    Returns:
        List[Dict[str, Any]]: 空值测试用例列表

    Example:
        def test_user_creation():
            def create_user(username, email):
                return {"username": username, "email": email}

            test_cases = generate_null_test_cases(create_user, "username")
            for test_case in test_cases:
                result = create_user(test_case["param_value"], "test@example.com")
                # 验证逻辑
    """
    generator = BoundaryValueGenerator()
    return generator.generate_null_test_cases(function, param_name, include_nested)


def generate_max_value_test_cases(
    function: Callable, param_name: str, param_type: str, max_value: Optional[Union[int, float, str]] = None, **kwargs
):
    """
    便捷函数：为指定函数和参数生成最大值测试用例

    这是 BoundaryValueGenerator.generate_max_value_test_cases 的便捷包装器。

    Args:
        function: 要测试的函数
        param_name: 参数名称
        param_type: 参数类型 ("string", "integer", "float", "list", "dict")
        max_value: 最大值限制
        **kwargs: 额外参数

    Returns:
        List[Dict[str, Any]]: 最大值测试用例列表

    Example:
        def test_age_validation():
            def validate_age(age):
                return 0 <= age <= 150

            test_cases = generate_max_value_test_cases(
                validate_age, "age", "integer", max_value=150
            )
            for test_case in test_cases:
                result = validate_age(test_case["param_value"])
                # 验证逻辑
    """
    generator = BoundaryValueGenerator()
    return generator.generate_max_value_test_cases(function, param_name, param_type, max_value, **kwargs)


def generate_concurrent_test_cases(
    function: Callable,
    num_threads: Optional[Union[int, List[int]]] = None,
    num_operations: Optional[Union[int, List[int]]] = None,
    operation_type: str = "mixed",
):
    """
    便捷函数：为指定函数生成并发测试用例

    这是 BoundaryValueGenerator.generate_concurrent_test_cases 的便捷包装器。

    Args:
        function: 要测试的函数
        num_threads: 并发线程数
        num_operations: 每个线程的操作次数
        operation_type: 操作类型 ("read", "write", "mixed", etc.)

    Returns:
        List[Dict[str, Any]]: 并发测试用例列表

    Example:
        def test_concurrent_counter():
            def increment(counter):
                counter["value"] += 1

            test_cases = generate_concurrent_test_cases(
                increment, num_threads=[2, 10], operation_type="write"
            )
            for test_case in test_cases:
                # 设置并发测试
                pass
    """
    generator = BoundaryValueGenerator()
    return generator.generate_concurrent_test_cases(function, num_threads, num_operations, operation_type)
