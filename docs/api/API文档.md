# API 文档

## 概述

本文档描述了 MaiMNP 后端 API 的接口规范。API 基于 FastAPI 框架构建，提供用户管理、知识库管理、人设卡管理、审核管理、消息管理、评论管理等功能。

## 基础信息

- **基础URL**: `http://localhost:9278`
- **API版本**: v1
- **认证方式**: Bearer Token (JWT)
- **Content-Type**: `application/json`

## 项目架构

项目采用标准的 FastAPI 分层架构：

```
app/
├── api/                      # API 路由层
│   ├── deps.py               # 依赖注入（认证、权限）
│   ├── websocket.py          # WebSocket 处理
│   └── routes/               # 路由模块
│       ├── auth.py           # 认证路由
│       ├── users.py          # 用户路由
│       ├── knowledge.py      # 知识库路由
│       ├── persona.py        # 人设卡路由
│       ├── messages.py       # 消息路由
│       ├── admin.py          # 管理员路由
│       ├── review.py         # 审核路由
│       ├── dictionary.py     # 字典路由
│       └── comments.py       # 评论路由
├── core/                     # 核心配置
│   ├── config.py             # 配置管理
│   ├── security.py           # JWT 和密码安全
│   ├── database.py           # 数据库连接
│   ├── middleware.py         # 中间件
│   └── logging.py            # 日志配置
├── models/                   # 数据模型
│   ├── database.py           # SQLAlchemy 模型
│   └── schemas.py            # Pydantic 模型
├── services/                 # 业务逻辑层
│   ├── user_service.py       # 用户服务
│   ├── auth_service.py       # 认证服务
│   ├── knowledge_service.py  # 知识库服务
│   ├── persona_service.py    # 人设卡服务
│   ├── message_service.py    # 消息服务
│   ├── email_service.py      # 邮件服务
│   └── file_service.py       # 文件服务
└── utils/                    # 工具函数
    ├── file.py               # 文件处理
    ├── avatar.py             # 头像处理
    └── websocket.py          # WebSocket 管理
```

### 分层说明

- **API 层** (`app/api/`): 处理 HTTP 请求和响应，进行请求验证、权限检查和响应格式化
- **服务层** (`app/services/`): 封装业务逻辑，处理数据转换和事务管理
- **数据层** (`app/models/`): 定义数据库模型和 API 模型
- **核心模块** (`app/core/`): 提供配置、安全、数据库等核心功能
- **工具模块** (`app/utils/`): 提供通用工具函数

详细的架构说明请参考 [架构文档](../architecture/架构文档.md)。

---

## 系统级接口

### 欢迎页
```http
GET /
```

**响应示例**:
```json
{
  "message": "MaiMNP Backend API"
}
```

### 健康检查
```http
GET /health
```

**响应示例**:
```json
{
  "status": "healthy"
}
```

---

## 认证接口 (`/api/auth`)

### 用户登录
```http
POST /api/auth/login
```

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

**响应示例** (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "username": "string",
    "email": "string",
    "is_admin": false,
    "is_moderator": false,
    "is_super_admin": false
  }
}
```

### 用户注册
```http
POST /api/auth/register
```

**请求体**:
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "verification_code": "string"
}
```

**响应示例** (201):
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "is_active": true,
  "created_at": "2025-02-20T00:00:00"
}
```

### 发送验证码
```http
POST /api/auth/send-verification-code
```

**请求体**:
```json
{
  "email": "string"
}
```

**响应示例** (200):
```json
{
  "message": "验证码已发送"
}
```

### 验证邮箱
```http
POST /api/auth/verify-email
```

**请求体**:
```json
{
  "email": "string",
  "code": "string"
}
```

**响应示例** (200):
```json
{
  "message": "邮箱验证成功"
}
```

### 重置密码
```http
POST /api/auth/reset-password
```

**请求体**:
```json
{
  "email": "string",
  "verification_code": "string",
  "new_password": "string"
}
```

**响应示例** (200):
```json
{
  "message": "密码重置成功"
}
```

---

## 用户接口 (`/api/users`)

### 获取当前用户信息
```http
GET /api/users/me
```

**认证**: 需要 Bearer Token

**响应示例** (200):
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "is_active": true,
  "is_admin": false,
  "is_moderator": false,
  "is_super_admin": false,
  "avatar_path": "string or null",
  "created_at": "2025-02-20T00:00:00"
}
```

### 更新用户信息
```http
PUT /api/users/me
```

**认证**: 需要 Bearer Token

**请求体**:
```json
{
  "username": "string (optional)",
  "email": "string (optional)"
}
```

**响应示例** (200):
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string"
}
```

### 修改密码
```http
POST /api/users/change-password
```

**认证**: 需要 Bearer Token

**请求体**:
```json
{
  "old_password": "string",
  "new_password": "string"
}
```

**响应示例** (200):
```json
{
  "message": "密码修改成功"
}
```

### 上传头像
```http
POST /api/users/avatar
```

**认证**: 需要 Bearer Token

**请求**: multipart/form-data
- `file`: 图片文件

**响应示例** (200):
```json
{
  "avatar_path": "string",
  "message": "头像上传成功"
}
```

### 获取用户收藏
```http
GET /api/user/stars
```

**认证**: 需要 Bearer Token

**查询参数**:
- `skip`: 分页偏移 (默认: 0)
- `limit`: 分页大小 (默认: 10)

**响应示例** (200):
```json
{
  "total": 10,
  "items": [
    {
      "id": "uuid",
      "target_id": "uuid",
      "target_type": "knowledge or persona",
      "created_at": "2025-02-20T00:00:00"
    }
  ]
}
```

---

## 知识库接口 (`/api/knowledge`)

### 创建知识库
```http
POST /api/knowledge
```

**认证**: 需要 Bearer Token

**请求体**:
```json
{
  "name": "string",
  "description": "string",
  "copyright_owner": "string (optional)",
  "tags": "string (optional, 逗号分隔)",
  "is_public": false
}
```

**响应示例** (201):
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "uploader_id": "uuid",
  "is_public": false,
  "is_pending": true,
  "created_at": "2025-02-20T00:00:00"
}
```

### 获取知识库列表
```http
GET /api/knowledge
```

**查询参数**:
- `skip`: 分页偏移 (默认: 0)
- `limit`: 分页大小 (默认: 10)
- `is_public`: 仅获取公开知识库 (可选)
- `search`: 搜索关键词 (可选)

**响应示例** (200):
```json
{
  "total": 100,
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "description": "string",
      "uploader_id": "uuid",
      "author": "string",
      "star_count": 10,
      "downloads": 5,
      "is_public": true,
      "is_pending": false,
      "created_at": "2025-02-20T00:00:00"
    }
  ]
}
```

### 获取知识库详情
```http
GET /api/knowledge/{knowledge_id}
```

**响应示例** (200):
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "content": "string (optional)",
  "uploader_id": "uuid",
  "author": "string",
  "star_count": 10,
  "downloads": 5,
  "tags": "string",
  "is_public": true,
  "is_pending": false,
  "created_at": "2025-02-20T00:00:00",
  "updated_at": "2025-02-20T00:00:00"
}
```

### 更新知识库
```http
PUT /api/knowledge/{knowledge_id}
```

**认证**: 需要 Bearer Token（仅所有者可更新）

**请求体**:
```json
{
  "name": "string (optional)",
  "description": "string (optional)",
  "content": "string (optional)",
  "tags": "string (optional)",
  "is_public": false
}
```

**响应示例** (200):
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string"
}
```

### 删除知识库
```http
DELETE /api/knowledge/{knowledge_id}
```

**认证**: 需要 Bearer Token（仅所有者可删除）

**响应示例** (200):
```json
{
  "message": "知识库删除成功"
}
```

### 上传知识库文件
```http
POST /api/knowledge/{knowledge_id}/files
```

**认证**: 需要 Bearer Token

**请求**: multipart/form-data
- `files`: 文件列表

**响应示例** (200):
```json
{
  "message": "文件上传成功",
  "files": [
    {
      "id": "uuid",
      "file_name": "string",
      "original_name": "string",
      "file_size": 1024,
      "file_type": "string"
    }
  ]
}
```

### 下载知识库
```http
GET /api/knowledge/{knowledge_id}/download
```

**响应**: 文件下载

---

## 人设卡接口 (`/api/persona`)

### 创建人设卡
```http
POST /api/persona
```

**认证**: 需要 Bearer Token

**请求体**:
```json
{
  "name": "string",
  "description": "string",
  "copyright_owner": "string (optional)",
  "tags": "string (optional)",
  "is_public": false
}
```

**响应示例** (201):
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "uploader_id": "uuid",
  "is_public": false,
  "is_pending": true,
  "created_at": "2025-02-20T00:00:00"
}
```

### 获取人设卡列表
```http
GET /api/persona
```

**查询参数**:
- `skip`: 分页偏移 (默认: 0)
- `limit`: 分页大小 (默认: 10)
- `is_public`: 仅获取公开人设卡 (可选)
- `search`: 搜索关键词 (可选)

**响应示例** (200):
```json
{
  "total": 50,
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "description": "string",
      "uploader_id": "uuid",
      "author": "string",
      "star_count": 5,
      "downloads": 2,
      "is_public": true,
      "is_pending": false,
      "created_at": "2025-02-20T00:00:00"
    }
  ]
}
```

### 获取人设卡详情
```http
GET /api/persona/{persona_id}
```

**响应示例** (200):
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "content": "string (optional)",
  "uploader_id": "uuid",
  "author": "string",
  "star_count": 5,
  "downloads": 2,
  "tags": "string",
  "is_public": true,
  "is_pending": false,
  "created_at": "2025-02-20T00:00:00"
}
```

### 更新人设卡
```http
PUT /api/persona/{persona_id}
```

**认证**: 需要 Bearer Token（仅所有者可更新）

**请求体**:
```json
{
  "name": "string (optional)",
  "description": "string (optional)",
  "content": "string (optional)",
  "tags": "string (optional)",
  "is_public": false
}
```

**响应示例** (200):
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string"
}
```

### 删除人设卡
```http
DELETE /api/persona/{persona_id}
```

**认证**: 需要 Bearer Token（仅所有者可删除）

**响应示例** (200):
```json
{
  "message": "人设卡删除成功"
}
```

### 上传人设卡文件
```http
POST /api/persona/{persona_id}/files
```

**认证**: 需要 Bearer Token

**请求**: multipart/form-data
- `files`: 文件列表

**响应示例** (200):
```json
{
  "message": "文件上传成功",
  "files": [
    {
      "id": "uuid",
      "file_name": "string",
      "original_name": "string",
      "file_size": 1024,
      "file_type": "string"
    }
  ]
}
```

---

## 消息接口 (`/api/messages`)

### 发送消息
```http
POST /api/messages
```

**认证**: 需要 Bearer Token

**请求体**:
```json
{
  "recipient_id": "uuid",
  "title": "string",
  "content": "string",
  "summary": "string (optional)"
}
```

**响应示例** (201):
```json
{
  "id": "uuid",
  "recipient_id": "uuid",
  "sender_id": "uuid",
  "title": "string",
  "content": "string",
  "is_read": false,
  "created_at": "2025-02-20T00:00:00"
}
```

### 获取收件箱
```http
GET /api/messages/inbox
```

**认证**: 需要 Bearer Token

**查询参数**:
- `skip`: 分页偏移 (默认: 0)
- `limit`: 分页大小 (默认: 10)
- `is_read`: 筛选已读/未读 (可选)

**响应示例** (200):
```json
{
  "total": 20,
  "items": [
    {
      "id": "uuid",
      "sender_id": "uuid",
      "sender_name": "string",
      "title": "string",
      "content": "string",
      "is_read": false,
      "created_at": "2025-02-20T00:00:00"
    }
  ]
}
```

### 获取消息详情
```http
GET /api/messages/{message_id}
```

**认证**: 需要 Bearer Token

**响应示例** (200):
```json
{
  "id": "uuid",
  "recipient_id": "uuid",
  "sender_id": "uuid",
  "sender_name": "string",
  "title": "string",
  "content": "string",
  "summary": "string (optional)",
  "is_read": false,
  "created_at": "2025-02-20T00:00:00"
}
```

### 标记消息为已读
```http
PUT /api/messages/{message_id}/read
```

**认证**: 需要 Bearer Token

**响应示例** (200):
```json
{
  "message": "消息已标记为已读"
}
```

### 删除消息
```http
DELETE /api/messages/{message_id}
```

**认证**: 需要 Bearer Token

**响应示例** (200):
```json
{
  "message": "消息删除成功"
}
```

---

## 评论接口 (`/api/comments`)

### 创建评论
```http
POST /api/comments
```

**认证**: 需要 Bearer Token

**请求体**:
```json
{
  "target_id": "uuid",
  "target_type": "knowledge or persona",
  "content": "string",
  "parent_id": "uuid (optional, 用于回复)"
}
```

**响应示例** (201):
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "target_id": "uuid",
  "target_type": "string",
  "content": "string",
  "like_count": 0,
  "dislike_count": 0,
  "created_at": "2025-02-20T00:00:00"
}
```

### 获取评论列表
```http
GET /api/comments
```

**查询参数**:
- `target_id`: 目标内容 ID (必需)
- `target_type`: 目标类型 (必需)
- `skip`: 分页偏移 (默认: 0)
- `limit`: 分页大小 (默认: 10)

**响应示例** (200):
```json
{
  "total": 15,
  "items": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "user_name": "string",
      "content": "string",
      "like_count": 2,
      "dislike_count": 0,
      "created_at": "2025-02-20T00:00:00"
    }
  ]
}
```

### 点赞评论
```http
POST /api/comments/{comment_id}/like
```

**认证**: 需要 Bearer Token

**响应示例** (200):
```json
{
  "message": "点赞成功",
  "like_count": 3
}
```

### 点踩评论
```http
POST /api/comments/{comment_id}/dislike
```

**认证**: 需要 Bearer Token

**响应示例** (200):
```json
{
  "message": "点踩成功",
  "dislike_count": 1
}
```

### 删除评论
```http
DELETE /api/comments/{comment_id}
```

**认证**: 需要 Bearer Token（仅所有者或管理员可删除）

**响应示例** (200):
```json
{
  "message": "评论删除成功"
}
```

---

## 收藏接口

### 添加收藏
```http
POST /api/users/stars
```

**认证**: 需要 Bearer Token

**请求体**:
```json
{
  "target_id": "uuid",
  "target_type": "knowledge or persona"
}
```

**响应示例** (201):
```json
{
  "message": "收藏成功"
}
```

### 取消收藏
```http
DELETE /api/users/stars/{target_id}
```

**认证**: 需要 Bearer Token

**查询参数**:
- `target_type`: 目标类型 (必需)

**响应示例** (200):
```json
{
  "message": "取消收藏成功"
}
```

---

## 管理员接口 (`/api/admin`)

### 获取待审核内容列表
```http
GET /api/admin/pending-reviews
```

**认证**: 需要 Bearer Token（仅管理员）

**查询参数**:
- `content_type`: knowledge 或 persona (可选)
- `skip`: 分页偏移 (默认: 0)
- `limit`: 分页大小 (默认: 10)

**响应示例** (200):
```json
{
  "total": 5,
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "description": "string",
      "uploader_id": "uuid",
      "uploader_name": "string",
      "type": "knowledge or persona",
      "created_at": "2025-02-20T00:00:00"
    }
  ]
}
```

### 审核通过
```http
POST /api/admin/approve/{content_id}
```

**认证**: 需要 Bearer Token（仅管理员）

**查询参数**:
- `content_type`: knowledge 或 persona (必需)

**响应示例** (200):
```json
{
  "message": "审核通过"
}
```

### 审核驳回
```http
POST /api/admin/reject/{content_id}
```

**认证**: 需要 Bearer Token（仅管理员）

**请求体**:
```json
{
  "reason": "string",
  "content_type": "knowledge or persona"
}
```

**响应示例** (200):
```json
{
  "message": "审核驳回"
}
```

### 广播消息
```http
POST /api/admin/broadcast-messages
```

**认证**: 需要 Bearer Token（仅管理员）

**请求体**:
```json
{
  "title": "string",
  "content": "string",
  "scope": "all_users (optional)"
}
```

**响应示例** (201):
```json
{
  "message": "广播消息发送成功"
}
```

### 禁言用户
```http
POST /api/admin/mute-user/{user_id}
```

**认证**: 需要 Bearer Token（仅管理员）

**请求体**:
```json
{
  "duration_hours": 24,
  "reason": "string (optional)"
}
```

**响应示例** (200):
```json
{
  "message": "用户已禁言"
}
```

### 解除禁言
```http
POST /api/admin/unmute-user/{user_id}
```

**认证**: 需要 Bearer Token（仅管理员）

**响应示例** (200):
```json
{
  "message": "禁言已解除"
}
```

---

## WebSocket 接口

### 实时消息推送
```
WS /api/ws/{token}
```

**连接参数**:
- `token`: JWT 认证令牌

**消息格式**:
```json
{
  "type": "message",
  "data": {
    "id": "uuid",
    "sender_id": "uuid",
    "title": "string",
    "content": "string",
    "created_at": "2025-02-20T00:00:00"
  }
}
```

---

## 错误响应

所有错误响应遵循统一格式：

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误码

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权（缺少或无效的 Token） |
| 403 | 禁止访问（权限不足） |
| 404 | 资源不存在 |
| 409 | 冲突（如用户名已存在） |
| 422 | 验证错误 |
| 500 | 服务器内部错误 |

---

## 认证说明

### JWT Token

所有需要认证的接口都需要在请求头中提供 Bearer Token：

```http
Authorization: Bearer <token>
```

Token 由登录接口返回，有效期为 24 小时。

### 权限级别

- **普通用户**: 可以创建、编辑自己的内容，查看公开内容
- **版主** (`is_moderator`): 可以审核内容、管理评论
- **管理员** (`is_admin`): 可以执行所有管理操作
- **超级管理员** (`is_super_admin`): 拥有最高权限

---

## 相关文档

- [架构文档](../architecture/架构文档.md) - 系统架构设计
- [数据库模型](../database/数据模型.md) - 数据库表结构
- [错误码说明](../development/错误码文档.md) - 详细的错误码列表
- [更新日志](../guides/更新日志.md) - API 变更历史

---

**文档版本**: 4.0  
**最后更新**: 2025-02-20  
**维护者**: cuckoo711
