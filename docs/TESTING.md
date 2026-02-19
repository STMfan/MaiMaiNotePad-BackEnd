# 测试与文档指南

## 概述

本文档描述了 MaiMaiNotePad 后端项目的测试策略、测试运行方法和开发指南。项目采用 pytest 作为测试框架，支持单元测试和集成测试。

## 项目结构

测试文件组织在 `tests/` 目录下，镜像 `app/` 的目录结构：

```
tests/
├── __init__.py
├── conftest.py               # 测试配置和 fixtures
├── test_auth.py              # 认证相关测试
├── test_users.py             # 用户相关测试
├── test_knowledge.py         # 知识库相关测试
├── test_persona.py           # 人设卡相关测试
└── services/                 # 服务层测试
    ├── test_user_service.py
    ├── test_auth_service.py
    ├── test_knowledge_service.py
    └── test_persona_service.py
```

## 测试

### 运行所有测试

```bash
# 使用 pytest 运行所有测试
pytest tests/ -v

# 或使用项目提供的测试脚本
python run_tests.py
```

### 运行特定测试

```bash
# 只运行认证相关测试
pytest tests/test_auth.py -v

# 只运行知识库相关测试
pytest tests/test_knowledge.py -v

# 运行特定测试函数
pytest tests/test_auth.py::test_login -v

# 运行服务层测试
pytest tests/services/ -v
```

### 测试覆盖率

```bash
# 生成覆盖率报告
pytest tests/ --cov=app --cov-report=html

# 查看覆盖率报告
# 报告将生成在 htmlcov/index.html
```

测试覆盖率目标：
- 服务层代码覆盖率 > 80%
- 工具函数代码覆盖率 > 90%
- API 路由代码覆盖率 > 70%

### 测试配置

测试配置位于 `tests/conftest.py`，提供了常用的 fixtures：

```python
@pytest.fixture
def db_session():
    """提供测试数据库会话"""
    # 创建测试数据库
    # 返回数据库会话
    # 测试结束后清理

@pytest.fixture
def test_client():
    """提供 FastAPI 测试客户端"""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)

@pytest.fixture
def test_user(db_session):
    """创建测试用户"""
    # 创建并返回测试用户
```

## 测试类型

### 1. 单元测试

单元测试专注于测试单个函数或方法的功能，使用 mock 隔离外部依赖。

**示例**：测试服务层方法

```python
# tests/services/test_user_service.py
import pytest
from app.services.user_service import UserService

def test_create_user(db_session):
    """测试创建用户"""
    service = UserService(db_session)
    user = service.create_user(
        username="testuser",
        email="test@example.com",
        password="password123"
    )
    
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.hashed_password != "password123"  # 密码应该被哈希

def test_get_user_by_username(db_session, test_user):
    """测试根据用户名获取用户"""
    service = UserService(db_session)
    user = service.get_user_by_username(test_user.username)
    
    assert user is not None
    assert user.id == test_user.id
```

### 2. 集成测试

集成测试测试完整的 API 端点流程，包括请求验证、业务逻辑和响应格式化。

**示例**：测试 API 端点

```python
# tests/test_auth.py
def test_login(test_client):
    """测试用户登录"""
    response = test_client.post(
        "/api/token",
        data={
            "username": "testuser",
            "password": "password123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_get_current_user(test_client, auth_headers):
    """测试获取当前用户信息"""
    response = test_client.get(
        "/api/users/me",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "username" in data
    assert "email" in data
```

### 3. 测试数据准备

使用 fixtures 准备测试数据：

```python
# tests/conftest.py
@pytest.fixture
def test_user(db_session):
    """创建测试用户"""
    from app.services.user_service import UserService
    
    service = UserService(db_session)
    user = service.create_user(
        username="testuser",
        email="test@example.com",
        password="password123"
    )
    return user

@pytest.fixture
def auth_headers(test_client, test_user):
    """获取认证头"""
    response = test_client.post(
        "/api/token",
        data={
            "username": test_user.username,
            "password": "password123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_knowledge_base(db_session, test_user):
    """创建测试知识库"""
    from app.services.knowledge_service import KnowledgeService
    
    service = KnowledgeService(db_session)
    kb = service.create_knowledge_base(
        name="测试知识库",
        description="这是一个测试知识库",
        uploader_id=test_user.id
    )
    return kb
```

## 测试最佳实践

### 1. 测试命名

- 测试文件以 `test_` 开头
- 测试函数以 `test_` 开头
- 使用描述性的测试名称

```python
# 好的命名
def test_create_user_with_valid_data():
    pass

def test_create_user_with_duplicate_username_raises_error():
    pass

# 不好的命名
def test_user():
    pass

def test_1():
    pass
```

### 2. 测试隔离

- 每个测试应该独立运行
- 使用 fixtures 准备测试数据
- 测试结束后清理数据

```python
@pytest.fixture
def db_session():
    # 创建测试数据库
    session = create_test_session()
    yield session
    # 清理数据
    session.rollback()
    session.close()
```

### 3. 使用 Mock

对于外部依赖（如邮件服务、文件系统），使用 mock 进行隔离：

```python
from unittest.mock import patch

def test_send_verification_email(db_session):
    with patch('app.services.email_service.EmailService.send_email') as mock_send:
        mock_send.return_value = True
        
        # 测试代码
        service = AuthService(db_session)
        result = service.send_verification_code("test@example.com")
        
        assert result is True
        mock_send.assert_called_once()
```

### 4. 测试边界条件

- 测试正常情况
- 测试边界值
- 测试异常情况

```python
def test_create_user_with_empty_username():
    """测试空用户名"""
    with pytest.raises(ValueError):
        service.create_user(username="", email="test@example.com", password="pass")

def test_create_user_with_short_password():
    """测试过短的密码"""
    with pytest.raises(ValueError):
        service.create_user(username="user", email="test@example.com", password="123")

def test_create_user_with_invalid_email():
    """测试无效的邮箱"""
    with pytest.raises(ValueError):
        service.create_user(username="user", email="invalid", password="password")
```

## 测试工具

### pytest

主要测试框架，提供：
- 测试发现和运行
- Fixtures 支持
- 参数化测试
- 插件系统

### pytest-cov

测试覆盖率工具：

```bash
# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 只显示未覆盖的代码
pytest --cov=app --cov-report=term-missing
```

### pytest-mock

Mock 工具，简化 mock 的使用：

```python
def test_with_mocker(mocker):
    mock_send = mocker.patch('app.services.email_service.EmailService.send_email')
    mock_send.return_value = True
    # 测试代码
```

### TestClient

FastAPI 提供的测试客户端，用于测试 API 端点：

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.get("/api/users/me")
```

## 持续集成

### GitHub Actions

项目使用 GitHub Actions 进行持续集成，配置文件位于 `.github/workflows/test.yml`：

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest tests/ --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## API文档

### 在线文档

启动服务器后，可以通过以下地址访问交互式API文档：

- **Swagger UI**: `http://localhost:9278/docs`  
  提供交互式 API 测试界面，可以直接在浏览器中测试所有接口
  
- **ReDoc**: `http://localhost:9278/redoc`  
  提供更友好的 API 文档阅读界面

### Postman集合

我们提供了Postman集合文件，方便测试API：

1. 安装Postman
2. 导入 `docs/MaiMNP_API.postman_collection.json`
3. 设置环境变量：
   - `baseUrl`: API基础URL (默认: http://localhost:9278)
   - `token`: 登录后获取的JWT令牌
   - `kb_id`: 知识库ID
   - `user_id`: 用户ID

### API文档

详细的API文档请参考：
- [API.md](./API.md) - 完整的 API 接口文档
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 架构设计文档

## 开发环境设置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `fastapi`: Web 框架
- `uvicorn`: ASGI 服务器
- `sqlalchemy`: ORM 框架
- `pydantic`: 数据验证
- `pydantic-settings`: 配置管理
- `pytest`: 测试框架
- `pytest-cov`: 覆盖率工具

### 2. 设置环境变量

创建 `.env` 文件：

```bash
cp .env.template .env
```

必须配置的关键项：
```env
# JWT 配置
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

# 数据库配置
DATABASE_URL=sqlite:///./data/maimnp.db

# 邮件配置
MAIL_HOST=smtp.qq.com
MAIL_PORT=465
MAIL_USER=your_email@qq.com
MAIL_PWD=your_email_authorization_code

# 管理员配置
SUPERADMIN_USERNAME=superadmin
SUPERADMIN_PWD=admin123456
HIGHEST_PASSWORD=your_highest_password

# 外部域名
EXTERNAL_DOMAIN=example.com
```

### 3. 初始化数据库

```bash
# 创建数据库并执行迁移
alembic upgrade head
```

### 4. 启动服务器

```bash
# 开发模式（自动重载）
./start_backend.sh

# 或使用 uvicorn 直接启动
python -m uvicorn app.main:app --host 0.0.0.0 --port 9278 --reload
```

## 代码规范

项目遵循以下代码规范：

### 1. 导入规范

- 使用绝对导入（从 `app` 开始）
- 避免循环依赖
- 按标准库、第三方库、本地模块的顺序组织导入

```python
# 标准库
from typing import Optional, List
from datetime import datetime

# 第三方库
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# 本地模块
from app.core.database import get_db
from app.services.user_service import UserService
from app.models.schemas import UserResponse
```

### 2. 类型注解

- 所有函数参数和返回值都应该有类型注解
- 使用 `typing` 模块提供的类型

```python
from typing import Optional, List

def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100
) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()
```

### 3. 文档字符串

- 所有公共函数都应该有 docstring
- 使用 Google 风格的 docstring

```python
def create_user(username: str, email: str, password: str) -> User:
    """创建新用户
    
    Args:
        username: 用户名
        email: 邮箱地址
        password: 密码（明文）
    
    Returns:
        创建的用户对象
    
    Raises:
        ValueError: 用户名或邮箱已存在
    """
    pass
```

### 4. 代码格式化

使用 Black 进行代码格式化：

```bash
# 格式化所有代码
black .

# 检查代码格式
black --check .
```

### 5. 代码检查

使用 flake8 进行代码检查：

```bash
# 检查代码
flake8 .

# 忽略特定错误
flake8 --ignore=E501,W503 .
```

### 6. 类型检查

使用 mypy 进行类型检查：

```bash
# 类型检查
mypy app/

# 严格模式
mypy --strict app/
```

## 贡献指南

### 1. 开发流程

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 2. 提交规范

使用语义化的提交信息：

- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建或辅助工具的变动

示例：
```
feat: 添加用户头像上传功能
fix: 修复知识库下载时的文件名编码问题
docs: 更新 API 文档
test: 添加用户服务的单元测试
```

### 3. Pull Request 要求

- 确保所有测试通过
- 添加适当的测试用例
- 更新相关文档
- 代码符合项目规范
- 提供清晰的 PR 描述

## 常见问题

### Q: 测试数据库如何隔离？

A: 使用 pytest fixtures 创建独立的测试数据库会话，每个测试结束后回滚事务：

```python
@pytest.fixture
def db_session():
    session = create_test_session()
    yield session
    session.rollback()
    session.close()
```

### Q: 如何测试需要认证的接口？

A: 使用 fixture 创建认证头：

```python
@pytest.fixture
def auth_headers(test_client, test_user):
    response = test_client.post("/api/token", data={
        "username": test_user.username,
        "password": "password123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### Q: 如何测试文件上传？

A: 使用 TestClient 的 files 参数：

```python
def test_upload_file(test_client, auth_headers):
    files = {"file": ("test.txt", b"test content", "text/plain")}
    response = test_client.post(
        "/api/knowledge/upload",
        files=files,
        data={"name": "Test", "description": "Test"},
        headers=auth_headers
    )
    assert response.status_code == 200
```

### Q: 如何 mock 外部服务？

A: 使用 pytest-mock 或 unittest.mock：

```python
def test_send_email(mocker):
    mock_send = mocker.patch('app.services.email_service.EmailService.send_email')
    mock_send.return_value = True
    # 测试代码
```

## 相关文档

- [API 文档](./API.md) - 完整的 API 接口文档
- [架构文档](./ARCHITECTURE.md) - 项目架构和设计说明
- [README.md](../README.md) - 项目概述和快速开始

---

**文档版本**: 2.0  
**最后更新**: 2025-01-XX  
**维护者**: 开发团队