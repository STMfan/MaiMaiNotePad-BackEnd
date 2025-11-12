# API 文档

## 概述

本文档描述了 MaiMNP 后端 API 的接口规范。API 基于 FastAPI 框架构建，提供用户管理、知识库管理、人设卡管理等功能。

## 基础信息

- **基础URL**: `http://localhost:8000`
- **API版本**: v1
- **认证方式**: Bearer Token (JWT)

## 认证

### 注册用户

```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

**响应示例**:
```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "created_at": "2023-01-01T00:00:00.000Z"
}
```

### 用户登录

```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=string&password=string
```

**响应示例**:
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

### 获取当前用户信息

```http
GET /api/users/me
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "created_at": "2023-01-01T00:00:00.000Z"
}
```

## 知识库管理

### 上传知识库

```http
POST /api/knowledge/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: 文件
name: 知识库名称
description: 知识库描述
is_public: 是否公开 (true/false)
```

**响应示例**:
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "is_public": true,
  "file_path": "string",
  "user_id": "string",
  "created_at": "2023-01-01T00:00:00.000Z"
}
```

### 获取公开知识库列表

```http
GET /api/knowledge/public
```

**响应示例**:
```json
[
  {
    "id": "string",
    "name": "string",
    "description": "string",
    "is_public": true,
    "user_id": "string",
    "created_at": "2023-01-01T00:00:00.000Z"
  }
]
```

### 获取知识库详情

```http
GET /api/knowledge/{kb_id}
```

**响应示例**:
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "is_public": true,
  "file_path": "string",
  "user_id": "string",
  "created_at": "2023-01-01T00:00:00.000Z"
}
```

### 获取用户的知识库列表

```http
GET /api/knowledge/user/{user_id}
```

**响应示例**:
```json
[
  {
    "id": "string",
    "name": "string",
    "description": "string",
    "is_public": true,
    "file_path": "string",
    "user_id": "string",
    "created_at": "2023-01-01T00:00:00.000Z"
  }
]
```

## Star 功能

### Star 知识库

```http
POST /api/star/knowledge/{kb_id}
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "message": "Star成功"
}
```

### 取消 Star 知识库

```http
DELETE /api/star/knowledge/{kb_id}
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "message": "取消Star成功"
}
```

### 获取用户的 Star 记录

```http
GET /api/stars/user
Authorization: Bearer {token}
```

**响应示例**:
```json
[
  {
    "id": "string",
    "target_type": "knowledge",
    "target_id": "string",
    "target_name": "string",
    "created_at": "2023-01-01T00:00:00.000Z"
  }
]
```

## 错误响应

所有错误响应都遵循以下格式：

```json
{
  "detail": "错误描述",
  "error_code": "错误代码"
}
```

### 常见错误代码

- `400`: 请求参数错误
- `401`: 未授权访问
- `403`: 禁止访问
- `404`: 资源不存在
- `409`: 资源冲突
- `500`: 服务器内部错误

## 限流

API 实施了请求限流，每个 IP 地址每分钟最多可以请求 100 次。

## 版本控制

API 版本通过 URL 路径进行控制，当前版本为 v1。未来版本将保持向后兼容性。

## 开发工具

### 在线文档

启动服务器后，可以通过以下地址访问交互式 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 测试

项目包含完整的测试套件，位于 `tests` 目录。运行测试：

```bash
pytest tests/
```

## 数据模型

### 用户模型

```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "password_hash": "string",
  "created_at": "datetime"
}
```

### 知识库模型

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "is_public": "boolean",
  "file_path": "string",
  "user_id": "string",
  "created_at": "datetime"
}
```

### Star 模型

```json
{
  "id": "string",
  "user_id": "string",
  "target_id": "string",
  "target_type": "string",
  "created_at": "datetime"
}
```