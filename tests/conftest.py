import pytest
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from hypothesis import settings, Verbosity, HealthCheck

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从 .test_env 或 .test_env.template 加载测试配置
from tests.test_config import test_config

# 配置 hypothesis 配置文件用于基于属性的测试
# CI 配置文件：100 次迭代，详细输出以获得详细的测试结果
settings.register_profile(
    "ci",
    max_examples=100,
    verbosity=Verbosity.verbose,
    deadline=None,  # 禁用截止时间以避免 CI 中的不稳定测试
    suppress_health_check=[HealthCheck.too_slow]
)

# 开发配置文件：10 次迭代，在开发过程中获得更快的反馈
settings.register_profile(
    "dev",
    max_examples=10,
    verbosity=Verbosity.normal,
    deadline=None
)

# 默认配置文件：使用 CI 配置文件以确保至少 100 次迭代
# 可以通过 HYPOTHESIS_PROFILE 环境变量覆盖
settings.load_profile(test_config.get("HYPOTHESIS_PROFILE", "ci"))

# 设置环境变量后导入
from app.models.database import (
    Base, User, EmailVerification, KnowledgeBase, KnowledgeBaseFile,
    PersonaCard, PersonaCardFile, Message, StarRecord, UploadRecord,
    DownloadRecord, Comment, CommentReaction
)
from app.core.database import get_db
from app.core.security import get_password_hash
from tests.test_data_factory import TestDataFactory

SQLALCHEMY_DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有表
Base.metadata.create_all(bind=engine)


def override_get_db():
    """覆盖数据库依赖用于测试"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_db() -> Session:
    """创建测试数据库会话"""
    # 使用简单的会话，不使用事务隔离，用于集成测试
    session = TestingSessionLocal()
    
    yield session
    
    # 测试后清理所有数据（按外键依赖的相反顺序）
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
    session.close()


@pytest.fixture(scope="function")
def factory(test_db: Session):
    """创建 TestDataFactory 实例"""
    return TestDataFactory(test_db)


@pytest.fixture(scope="function")
def test_user(test_db: Session):
    """创建具有唯一邮箱的测试用户"""
    # 生成唯一邮箱以避免 UNIQUE 约束失败
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        id=str(uuid.uuid4()),
        username=f"testuser_{unique_id}",
        email=f"test_{unique_id}@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_admin=False,
        is_moderator=False,
        is_super_admin=False,
        created_at=datetime.now(),
        password_version=0
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
        hashed_password=get_password_hash("adminpassword123"),
        is_active=True,
        is_admin=True,
        is_moderator=False,
        is_super_admin=False,
        created_at=datetime.now(),
        password_version=0
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
        hashed_password=get_password_hash("moderatorpassword123"),
        is_active=True,
        is_admin=False,
        is_moderator=True,
        is_super_admin=False,
        created_at=datetime.now(),
        password_version=0
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def super_admin_user(test_db: Session):
    """创建测试超级管理员用户"""
    user = User(
        id=str(uuid.uuid4()),
        username="superadminuser",
        email="superadmin@example.com",
        hashed_password=get_password_hash("superadminpassword123"),
        is_active=True,
        is_admin=True,
        is_moderator=True,
        is_super_admin=True,
        created_at=datetime.now(),
        password_version=0
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


# 仅在应用存在时导入（用于集成测试）
try:
    from app.main import app
    
    app.dependency_overrides[get_db] = override_get_db
    _test_client = TestClient(app)
    
    @pytest.fixture(scope="function")
    def client():
        """创建未认证的测试客户端"""
        return TestClient(app)
    
    @pytest.fixture(scope="function")
    def authenticated_client(test_user):
        """创建已认证的测试客户端"""
        # 为此测试创建新客户端
        client = TestClient(app)
        
        # 使用 test_user 的用户名登录以获取令牌
        response = client.post(
            "/api/auth/token",
            data={"username": test_user.username, "password": "testpassword123"}
        )
        
        # 检查登录是否成功
        if response.status_code != 200:
            raise Exception(f"登录失败: {response.status_code} - {response.text}")
        
        resp_data = response.json()
        
        # 处理两种响应格式（有和没有 "data" 包装器）
        if "data" in resp_data:
            token = resp_data["data"]["access_token"]
        else:
            token = resp_data["access_token"]
        
        # 设置认证头
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client
    
    @pytest.fixture(scope="function")
    def admin_client(admin_user):
        """创建已认证的管理员测试客户端"""
        # 为此测试创建新客户端
        client = TestClient(app)
        
        # 使用 admin_user 的用户名登录以获取令牌
        response = client.post(
            "/api/auth/token",
            data={"username": admin_user.username, "password": "adminpassword123"}
        )
        
        # 检查登录是否成功
        if response.status_code != 200:
            raise Exception(f"管理员登录失败: {response.status_code} - {response.text}")
        
        resp_data = response.json()
        
        # 处理两种响应格式（有和没有 "data" 包装器）
        if "data" in resp_data:
            token = resp_data["data"]["access_token"]
        else:
            token = resp_data["access_token"]
        
        # 设置认证头
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client
    
    @pytest.fixture(scope="function")
    def moderator_client(moderator_user):
        """创建已认证的审核员测试客户端"""
        # 为此测试创建新客户端
        client = TestClient(app)
        
        # 使用 moderator_user 的用户名登录以获取令牌
        response = client.post(
            "/api/auth/token",
            data={"username": moderator_user.username, "password": "moderatorpassword123"}
        )
        
        # 检查登录是否成功
        if response.status_code != 200:
            raise Exception(f"审核员登录失败: {response.status_code} - {response.text}")
        
        resp_data = response.json()
        
        # 处理两种响应格式（有和没有 "data" 包装器）
        if "data" in resp_data:
            token = resp_data["data"]["access_token"]
        else:
            token = resp_data["access_token"]
        
        # 设置认证头
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client
    
    @pytest.fixture(scope="function")
    def super_admin_client(super_admin_user):
        """创建已认证的超级管理员测试客户端"""
        # 登录以获取令牌
        response = _test_client.post(
            "/api/auth/token",
            data={"username": "superadminuser", "password": "superadminpassword123"}
        )
        
        # 检查登录是否成功
        if response.status_code != 200:
            raise Exception(f"超级管理员登录失败: {response.status_code} - {response.text}")
        
        resp_data = response.json()
        
        # 处理两种响应格式（有和没有 "data" 包装器）
        if "data" in resp_data:
            token = resp_data["data"]["access_token"]
        else:
            token = resp_data["access_token"]
        
        # 创建带认证头的客户端
        _test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield _test_client
        
        # 清理认证头
        _test_client.headers.pop("Authorization", None)
except ImportError:
    # 应用不可用，跳过集成测试 fixtures
    pass


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
    assert response.status_code in expected_status_codes, \
        f"预期状态码在 {expected_status_codes} 中，得到 {response.status_code}"
    
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
        keyword_found = any(
            keyword.lower() in combined_message 
            for keyword in expected_message_keywords
        )
        
        assert keyword_found, \
            f"预期 {expected_message_keywords} 中的一个在错误消息中，得到：{data}"
    
    # 处理自定义 API 错误
    elif "error" in data:
        # 自定义错误格式：{"success": False, "error": {"message": "..."}}
        error_message = data["error"].get("message", "").lower()
        
        # 检查是否有任何关键字匹配
        keyword_found = any(
            keyword.lower() in error_message 
            for keyword in expected_message_keywords
        )
        
        assert keyword_found, \
            f"预期 {expected_message_keywords} 中的一个在错误消息中，得到：{error_message}"
    
    else:
        # 未知错误格式
        raise AssertionError(f"未知的错误响应格式：{data}")
