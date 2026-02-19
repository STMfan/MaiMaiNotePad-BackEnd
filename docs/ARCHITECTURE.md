# 架构文档

## 概述

本文档描述 MaiMaiNotePad 后端项目的架构设计。项目基于 FastAPI 框架构建，采用标准的三层架构模式，按功能模块和职责清晰划分代码，提供用户认证、知识库管理、人设卡管理、消息系统等功能。

## 目录结构

```
MaiMaiNotePad-BackEnd/
├── app/                          # 应用主目录
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口
│   ├── api/                      # API 路由层
│   │   ├── __init__.py           # 路由注册
│   │   ├── deps.py               # 依赖注入（认证、权限）
│   │   ├── websocket.py          # WebSocket 处理
│   │   └── routes/               # 路由模块
│   │       ├── __init__.py
│   │       ├── auth.py           # 认证路由（登录、注册、密码重置）
│   │       ├── users.py          # 用户路由（个人信息、头像）
│   │       ├── knowledge.py      # 知识库路由
│   │       ├── persona.py        # 人设卡路由
│   │       ├── messages.py       # 消息路由
│   │       ├── admin.py          # 管理员路由
│   │       ├── review.py         # 审核路由
│   │       ├── dictionary.py     # 字典路由
│   │       └── comments.py       # 评论路由
│   ├── core/                     # 核心配置和依赖
│   │   ├── __init__.py
│   │   ├── config.py             # 配置管理（Pydantic Settings）
│   │   ├── security.py           # 安全相关（JWT、密码哈希）
│   │   ├── database.py           # 数据库连接和会话管理
│   │   ├── middleware.py         # 中间件配置
│   │   └── logging.py            # 日志配置
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   ├── database.py           # SQLAlchemy 数据库模型
│   │   └── schemas.py            # Pydantic API 模型
│   ├── services/                 # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── user_service.py       # 用户服务
│   │   ├── auth_service.py       # 认证服务
│   │   ├── knowledge_service.py  # 知识库服务
│   │   ├── persona_service.py    # 人设卡服务
│   │   ├── message_service.py    # 消息服务
│   │   ├── email_service.py      # 邮件服务
│   │   └── file_service.py       # 文件服务
│   └── utils/                    # 工具函数
│       ├── __init__.py
│       ├── file.py               # 文件处理工具
│       ├── avatar.py             # 头像处理工具
│       └── websocket.py          # WebSocket 管理器
├── tests/                        # 测试目录
│   ├── __init__.py
│   ├── conftest.py               # 测试配置
│   ├── test_auth.py              # 认证测试
│   ├── test_users.py             # 用户测试
│   ├── test_knowledge.py         # 知识库测试
│   └── test_persona.py           # 人设卡测试
├── alembic/                      # 数据库迁移
│   ├── versions/                 # 迁移版本
│   └── env.py                    # Alembic 环境配置
├── scripts/                      # 辅助脚本
│   ├── prepare_test_data.py      # 准备测试数据
│   └── reset_security_env.py     # 清档脚本
├── docs/                         # 文档目录
├── uploads/                      # 上传文件存储
├── data/                         # 数据库文件
├── logs/                         # 日志文件
├── .env                          # 环境变量配置
├── .env.template                 # 环境变量模板
├── requirements.txt              # Python 依赖
├── alembic.ini                   # Alembic 配置
├── pytest.ini                    # Pytest 配置
├── start_backend.sh              # 启动脚本
└── README.md                     # 项目文档
```

## 分层架构

项目采用经典的三层架构设计，各层职责清晰，降低耦合度：

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)         │
│    app/api/routes/*.py              │
│    - 请求验证                        │
│    - 响应格式化                      │
│    - 权限检查                        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│       Service Layer (Business)      │
│    app/services/*.py                │
│    - 业务逻辑                        │
│    - 数据转换                        │
│    - 事务管理                        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Data Layer (SQLAlchemy)        │
│    app/models/database.py           │
│    - 数据库操作                      │
│    - ORM 映射                        │
│    - 查询构建                        │
└─────────────────────────────────────┘
```

### 1. API 层 (app/api/)

**职责**：
- 定义 HTTP 端点和路由
- 验证请求数据（使用 Pydantic 模型）
- 执行权限检查（通过依赖注入）
- 格式化响应数据
- 处理 HTTP 异常

**关键组件**：
- `routes/`: 各功能模块的路由定义
- `deps.py`: 依赖注入函数（认证、权限检查）
- `websocket.py`: WebSocket 连接处理

**示例**：
```python
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_service = UserService(db)
    return user_service.get_user_by_id(current_user["id"])
```

### 2. 服务层 (app/services/)

**职责**：
- 实现核心业务逻辑
- 处理数据转换（数据库模型 ↔ API 模型）
- 管理数据库事务
- 协调多个数据模型的操作
- 提供可复用的业务方法

**设计原则**：
- 服务类不依赖 FastAPI 特定类型（Request、Response 等）
- 每个服务类专注于单一领域
- 通过构造函数注入数据库会话
- 易于单元测试

**示例**：
```python
from sqlalchemy.orm import Session
from app.models.database import User
from app.core.security import get_password_hash

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: str):
        return self.db.query(User).filter(User.id == user_id).first()
    
    def create_user(self, username: str, email: str, password: str):
        hashed_password = get_password_hash(password)
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
```

### 3. 数据层 (app/models/)

**职责**：
- 定义数据库表结构（SQLAlchemy 模型）
- 定义 API 请求/响应模型（Pydantic 模型）
- 提供数据验证规则
- 定义表关系和索引

**关键文件**：
- `database.py`: SQLAlchemy ORM 模型，映射数据库表
- `schemas.py`: Pydantic 模型，用于 API 数据验证和序列化

**示例**：
```python
# database.py - SQLAlchemy 模型
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False)

# schemas.py - Pydantic 模型
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    
    class Config:
        from_attributes = True
```

## 核心模块

### 1. 配置管理 (app/core/config.py)

使用 Pydantic Settings 管理所有配置，支持从环境变量加载：

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "MaiMNP Backend"
    HOST: str = "0.0.0.0"
    PORT: int = 9278
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/maimnp.db"
    
    # JWT 配置
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    
    # 邮件配置
    MAIL_HOST: str = "smtp.qq.com"
    MAIL_PORT: int = 465
    MAIL_USER: str
    MAIL_PWD: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 2. 安全模块 (app/core/security.py)

集中管理 JWT 和密码相关功能：

**功能**：
- JWT 令牌创建和验证
- 密码哈希和验证（使用 bcrypt）
- 密码版本机制（防止令牌重放）

**关键函数**：
- `create_access_token()`: 创建访问令牌
- `create_refresh_token()`: 创建刷新令牌
- `verify_token()`: 验证令牌
- `get_password_hash()`: 生成密码哈希
- `verify_password()`: 验证密码

### 3. 数据库连接 (app/core/database.py)

管理数据库连接和会话：

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI 依赖注入函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 4. 依赖注入 (app/api/deps.py)

定义常用的 FastAPI 依赖：

**认证依赖**：
- `get_current_user()`: 获取当前认证用户
- `get_admin_user()`: 获取管理员用户
- `get_moderator_user()`: 获取版主或管理员用户
- `get_current_user_optional()`: 可选认证（允许匿名访问）

**示例**：
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.core.security import verify_token

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    # 验证用户和密码版本
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return {
        "id": user.id,
        "username": user.username,
        "is_admin": user.is_admin
    }
```

## 数据模型

### 主要数据表

#### 1. User（用户表）
- 存储用户基本信息
- 包含认证信息（密码哈希、密码版本）
- 包含角色信息（admin、moderator）
- 包含账户状态（激活、锁定）

#### 2. KnowledgeBase（知识库表）
- 存储知识库元信息
- 关联上传者（User）
- 包含审核状态（is_public、is_pending）
- 包含统计信息（star_count、downloads）

#### 3. PersonaCard（人设卡表）
- 存储人设卡元信息
- 结构类似知识库表
- 支持标签和分类

#### 4. Message（消息表）
- 存储站内消息
- 支持私信和公告
- 包含已读状态

#### 5. StarRecord（收藏记录表）
- 记录用户的 Star 操作
- 关联用户和目标资源（知识库或人设卡）
- 支持按类型查询

#### 6. UploadRecord（上传记录表）
- 记录文件上传历史
- 包含上传状态和文件信息
- 用于统计和审计

### 模型关系

```
User ──┬─── KnowledgeBase (uploader_id)
       ├─── PersonaCard (uploader_id)
       ├─── Message (sender_id / recipient_id)
       ├─── StarRecord (user_id)
       └─── UploadRecord (user_id)

KnowledgeBase ─── StarRecord (target_id, target_type='knowledge')
PersonaCard ─── StarRecord (target_id, target_type='persona')
```

## 认证和授权

### 认证流程

1. **用户登录**：
   - 用户提交用户名和密码
   - 系统验证凭据
   - 生成 JWT 访问令牌和刷新令牌
   - 返回令牌给客户端

2. **令牌验证**：
   - 客户端在请求头中携带令牌
   - 系统验证令牌签名和有效期
   - 验证密码版本（防止令牌重放）
   - 提取用户信息

3. **令牌刷新**：
   - 访问令牌过期后，使用刷新令牌获取新的访问令牌
   - 刷新令牌有效期更长（7天）

### 权限控制

**角色定义**：
- **user**: 普通用户，可以上传和查看内容
- **moderator**: 审核员，可以审核内容
- **admin**: 管理员，拥有所有权限
- **super_admin**: 超级管理员，系统最高权限

**权限检查**：
- 通过依赖注入实现权限检查
- 在路由层使用 `Depends(get_admin_user)` 等依赖
- 服务层不直接处理权限，由 API 层负责

## 文件存储

### 存储结构

```
uploads/
├── knowledge/              # 知识库文件
│   └── {user_id}/          # 按用户ID分类
│       └── {kb_id}/        # 按知识库ID分类
│           ├── file1.txt
│           └── file2.pdf
├── persona/                # 人设卡文件
│   └── {user_id}/          # 按用户ID分类
│       └── {pc_id}/        # 按人设卡ID分类
│           └── card.json
└── avatars/                # 用户头像
    └── {user_id}.jpg
```

### 文件处理

**上传流程**：
1. 验证文件类型和大小
2. 生成唯一文件名
3. 保存到对应目录
4. 记录文件信息到数据库

**下载流程**：
1. 验证用户权限
2. 检查文件是否存在
3. 返回文件流或 ZIP 压缩包

**删除流程**：
1. 验证用户权限
2. 从文件系统删除文件
3. 从数据库删除记录

## 错误处理

### 错误响应格式

```json
{
    "detail": "错误描述信息",
    "error_code": "ERROR_CODE",
    "timestamp": "2024-01-01T00:00:00Z"
}
```

### 错误类型

- **400 Bad Request**: 请求参数错误
- **401 Unauthorized**: 未认证或令牌无效
- **403 Forbidden**: 权限不足
- **404 Not Found**: 资源不存在
- **500 Internal Server Error**: 服务器内部错误

### 错误处理策略

1. **配置错误**: 在应用启动时验证配置，缺失时抛出明确错误
2. **导入错误**: 使用绝对导入路径，避免循环依赖
3. **数据库错误**: 在服务层捕获异常，转换为业务异常
4. **认证错误**: 统一使用 HTTPException 返回标准错误响应

## 日志系统

### 日志配置

- 使用 Python 标准 logging 模块
- 支持控制台和文件输出
- 可配置日志级别（DEBUG、INFO、WARNING、ERROR）
- 日志文件按日期轮转

### 日志格式

```
[2024-01-01 12:00:00] [INFO] [module_name] 日志消息
```

### 日志记录点

- 用户认证和授权
- 文件上传和下载
- 数据库操作异常
- 外部服务调用（邮件发送）
- 关键业务操作

## 性能优化

### 数据库优化

1. **索引优化**：
   - 为常用查询字段添加索引
   - 复合索引优化多字段查询

2. **查询优化**：
   - 使用分页避免大量数据加载
   - 使用 eager loading 避免 N+1 查询
   - 合理使用数据库连接池

3. **缓存策略**：
   - 缓存配置信息
   - 缓存常用查询结果
   - 使用 Redis 缓存会话数据（未来）

### API 优化

1. **响应压缩**: 启用 gzip 压缩
2. **异步处理**: 使用 FastAPI 的异步特性
3. **限流**: 防止 API 滥用
4. **CDN**: 静态文件使用 CDN（生产环境）

## 安全考虑

### 密码安全

- 使用 bcrypt 哈希算法
- 限制密码长度为 72 字节（bcrypt 限制）
- 实施密码版本机制防止令牌重放

### JWT 安全

- 使用强随机密钥（32+ 字符）
- 设置合理的过期时间（访问令牌 15 分钟，刷新令牌 7 天）
- 验证密码版本防止旧令牌使用

### 输入验证

- 使用 Pydantic 模型验证所有输入
- 防止 SQL 注入（使用 ORM）
- 防止路径遍历攻击
- 文件上传类型和大小限制

### CORS 配置

- 配置允许的源
- 限制允许的 HTTP 方法
- 设置凭据策略

## 测试策略

### 单元测试

- 测试服务层业务逻辑
- 测试工具函数
- 使用 mock 隔离依赖
- 目标覆盖率：服务层 > 80%

### 集成测试

- 测试 API 端点完整流程
- 测试数据库操作
- 使用测试数据库隔离数据
- 目标覆盖率：API 层 > 70%

### 测试工具

- pytest: 测试框架
- pytest-cov: 覆盖率报告
- pytest-mock: Mock 工具
- TestClient: FastAPI 测试客户端

## 部署架构

### 开发环境

```
Developer Machine
├── Python 3.8+
├── SQLite Database
├── Local File Storage
└── Uvicorn (--reload)
```

### 生产环境（推荐）

```
Load Balancer
    │
    ├─── Application Server 1
    │    ├── Gunicorn + Uvicorn Workers
    │    ├── FastAPI Application
    │    └── Logs
    │
    ├─── Application Server 2
    │    └── ...
    │
    ├─── Database Server
    │    └── PostgreSQL / MySQL
    │
    ├─── File Storage
    │    └── S3 / MinIO
    │
    └─── Cache Server
         └── Redis
```

### 容器化部署

```dockerfile
FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9278"]
```

## 监控和维护

### 健康检查

- `/health`: 基本健康检查
- `/ready`: 就绪检查（数据库连接等）

### 监控指标

- API 响应时间
- 错误率
- 数据库连接池状态
- 文件存储使用量
- 用户活跃度

### 日志分析

- 错误日志聚合
- 性能瓶颈分析
- 用户行为分析
- 安全事件监控

## 未来改进

### 短期改进

1. 添加 Redis 缓存
2. 实现异步任务队列（Celery）
3. 添加更多单元测试
4. 优化数据库查询性能

### 长期改进

1. 微服务架构拆分
2. 使用 PostgreSQL 替代 SQLite
3. 实现分布式文件存储
4. 添加全文搜索（Elasticsearch）
5. 实现实时通知（WebSocket）
6. 添加 API 版本控制

## 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [Alembic 文档](https://alembic.sqlalchemy.org/)
- [JWT 规范](https://jwt.io/)
