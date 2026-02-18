import pytest
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic.config import Config
from alembic import command

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

base_dir = Path(__file__).resolve().parents[1]
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

alembic_cfg = Config(str(base_dir / "alembic.ini"))
command.upgrade(alembic_cfg, "head")

from main import app
from database_models import Base, get_db
from user_management import UserManager
from models import UserCreate

SQLALCHEMY_DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    connection = engine.connect()
    trans = connection.begin()
    yield
    trans.rollback()
    connection.close()

@pytest.fixture(scope="function")
def test_user():
    """创建测试用户"""
    user_manager = UserManager()
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="testpassword123"
    )
    user = user_manager.create_user(user_data)
    return user

@pytest.fixture(scope="function")
def authenticated_client(test_user):
    """创建已认证的测试客户端"""
    # 登录获取token
    response = client.post(
        "/api/token",
        data={"username": "testuser", "password": "testpassword123"}
    )
    resp_data = response.json()
    token = resp_data["data"]["access_token"]
    
    # 创建带有认证头的客户端
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client
    
    # 清理认证头
    client.headers.pop("Authorization", None)
