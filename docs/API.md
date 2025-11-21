# API 文档

## 概述

本文档描述了 MaiMNP 后端 API 的接口规范。API 基于 FastAPI 框架构建，提供用户管理、知识库管理、人设卡管理、审核管理、消息管理、邮件服务等功能。

## 基础信息

- **基础URL**: `http://0.0.0.0:9278`（本地可通过 `http://localhost:9278` 访问）
- **API版本**: v1
- **认证方式**: Bearer Token (JWT)
- **Content-Type**: 支持 `application/json` 和 `application/x-www-form-urlencoded`

## 系统级接口

### 欢迎页
返回固定欢迎文案，可用于快速验证服务是否在线。

```http
GET /
```

**响应示例**:
```json
{
  "message": "Welcome to MaiMaiNotePad"
}
```

### 健康检查
提供健康检查接口，返回静态状态。

```http
GET /health
```

**响应示例**:
```json
{ "status": "healthy" }
```

## 认证相关接口

### 用户登录
获取访问令牌，支持 JSON 和表单数据格式。

```http
POST /api/token
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}
```

或

```http
POST /api/token
Content-Type: application/x-www-form-urlencoded

username=string&password=string
```

**参数说明**:
- `username` (必填): 用户名
- `password` (必填): 密码

**响应示例**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**错误响应**:
- `400`: 用户名或密码为空
- `401`: 用户名或密码错误

### 发送验证码
向指定邮箱发送验证码，用于注册验证。

```http
POST /api/send_verification_code
Content-Type: application/x-www-form-urlencoded

email=user@example.com
```

**参数说明**:
- `email` (必填): 接收验证码的邮箱地址

**响应示例**:
```json
{
  "message": "验证码已发送"
}
```

**错误响应**:
- `400`: 邮箱格式无效
- `429`: 请求发送验证码过于频繁
- `500`: 发送验证码失败

### 用户注册
使用邮箱验证码注册新用户。

```http
POST /api/user/register
Content-Type: application/x-www-form-urlencoded

username=newuser&password=pass123&email=user@example.com&verification_code=123456
```

**参数说明**:
- `username` (必填): 用户名，需唯一
- `password` (必填): 密码
- `email` (必填): 邮箱地址
- `verification_code` (必填): 邮箱验证码

**响应示例**:
```json
{
  "success": true,
  "message": "注册成功"
}
```

**错误响应**:
- `400`: 有未填写的字段、验证码错误或已失效、用户名/邮箱已存在
- `500`: 注册失败，系统错误

### 发送重置密码验证码
向已注册邮箱发送密码重置验证码，触发频率受限。

```http
POST /api/send_reset_password_code
Content-Type: application/x-www-form-urlencoded

email=user@example.com
```

**参数说明**:
- `email` (必填): 接收验证码的邮箱地址，必须已注册

**响应示例**:
```json
{
  "message": "验证码已发送"
}
```

**错误响应**:
- `400`: 邮箱格式无效或邮箱未注册
- `429`: 请求过于频繁
- `500`: 发送验证码失败

### 重置密码
使用邮箱验证码重置账号密码。

```http
POST /api/reset_password
Content-Type: application/x-www-form-urlencoded

email=user@example.com&verification_code=123456&new_password=newPass
```

**参数说明**:
- `email` (必填): 邮箱地址
- `verification_code` (必填): 邮件收到的验证码
- `new_password` (必填): 新密码

**响应示例**:
```json
{
  "message": "密码重置成功"
}
```

**错误响应**:
- `400`: 参数缺失或验证码错误/失效
- `500`: 重置失败

### 获取当前用户信息
获取当前登录用户的基本信息。

```http
GET /api/users/me
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "id": "user123",
  "username": "testuser",
  "email": "user@example.com",
  "role": "user"
}
```

**错误响应**:
- `401`: 未授权访问
- `500`: 获取用户信息失败

## 知识库管理接口

### 上传知识库
上传知识库文件，支持多个文件同时上传。

```http
POST /api/knowledge/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

files: [文件1, 文件2, ...]
name: 知识库名称
description: 知识库描述
copyright_owner: 版权所有者（可选）
```

**参数说明**:
- `files` (必填): 知识库文件列表，至少需要上传一个文件
- `name` (必填): 知识库名称
- `description` (必填): 知识库描述
- `copyright_owner` (可选): 版权所有者信息

**响应示例**:
```json
{
  "id": "kb123",
  "name": "我的知识库",
  "description": "这是一个测试知识库",
  "uploader_id": "user123",
  "copyright_owner": "版权所有者",
  "star_count": 0,
  "is_public": false,
  "is_pending": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**错误响应**:
- `400`: 名称和描述不能为空、至少需要上传一个文件
- `401`: 未授权访问
- `500`: 上传知识库失败

### 获取公开知识库列表
获取所有已审核通过的公开知识库列表。

```http
GET /api/knowledge/public
```

**响应示例**:
```json
[
  {
    "id": "kb123",
    "name": "公开知识库",
    "description": "这是一个公开的知识库",
    "uploader_id": "user123",
    "copyright_owner": "版权所有者",
    "star_count": 10,
    "is_public": true,
    "is_pending": false,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

**错误响应**:
- `500`: 获取公开知识库失败

### 获取知识库内容
获取指定知识库的详细内容。

```http
GET /api/knowledge/{kb_id}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID

**响应示例**:
```json
{
  "content": "知识库内容...",
  "metadata": {
    "file_count": 2,
    "total_size": 1024
  }
}
```

**错误响应**:
- `404`: 知识库不存在
- `500`: 获取知识库内容失败

### 获取用户的知识库列表
获取指定用户上传的所有知识库。

```http
GET /api/knowledge/user/{user_id}
Authorization: Bearer {token}
```

**参数说明**:
- `user_id` (路径参数): 用户ID

**响应示例**:
```json
[
  {
    "id": "kb123",
    "name": "我的知识库",
    "description": "用户知识库描述",
    "uploader_id": "user123",
    "copyright_owner": "版权所有者",
    "star_count": 5,
    "is_public": false,
    "is_pending": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

**错误响应**:
- `403`: 没有权限查看其他用户的上传记录
- `401`: 未授权访问
- `500`: 获取用户知识库失败

### 更新知识库信息
更新知识库元信息，仅限上传者、管理员或审核员。

```http
PUT /api/knowledge/{kb_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "新的名称",
  "description": "新的描述",
  "copyright_owner": "新的版权所有者"
}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID
- `name`/`description` (可选): 为空则不更新
- `copyright_owner` (可选)

**错误响应**:
- `401`: 未授权访问
- `403`: 权限不足
- `404`: 知识库不存在
- `500`: 更新失败

### 添加知识库文件
为知识库追加文件。

```http
POST /api/knowledge/{kb_id}/files
Authorization: Bearer {token}
Content-Type: multipart/form-data

files: [文件1, 文件2, ...]
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID
- `files` (必填): 至少一个文件

**错误响应**:
- `400`: 未上传文件
- `401`: 未授权访问
- `403`: 权限不足
- `404`: 知识库不存在
- `500`: 上传失败

### 删除知识库文件
按文件ID删除知识库中文件。

```http
DELETE /api/knowledge/{kb_id}/{file_id}
Authorization: Bearer {token}
```

**参数说明**:
- `kb_id`: 知识库ID
- `file_id`: 文件ID

**错误响应**:
- `401`: 未授权访问
- `403`: 权限不足
- `404`: 文件或知识库不存在
- `500`: 删除失败

### 下载知识库全部文件
以 ZIP 形式下载知识库全部文件。

```http
GET /api/knowledge/{kb_id}/download
Authorization: Bearer {token}
```

**说明**: 对私有知识库仅上传者或管理员可下载。

**错误响应**:
- `401`: 未授权访问
- `403`: 无权下载
- `404`: 知识库不存在
- `500`: 打包失败

### 下载单个知识库文件
下载指定文件。

```http
GET /api/knowledge/{kb_id}/file/{file_id}
Authorization: Bearer {token}
```

**说明**: 私有知识库文件仅上传者或管理员可访问。

**错误响应**:
- `401`: 未授权访问
- `403`: 无权下载
- `404`: 文件不存在
- `500`: 下载失败

### 删除知识库
删除整个知识库及其文件。

```http
DELETE /api/knowledge/{kb_id}
Authorization: Bearer {token}
```

**错误响应**:
- `401`: 未授权访问
- `403`: 权限不足
- `404`: 知识库不存在
- `500`: 删除失败

### Star/取消Star知识库
对知识库进行Star或取消Star操作，接口会根据当前状态自动切换。

```http
POST /api/knowledge/{kb_id}/star
Authorization: Bearer {token}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID

**响应示例**:
```json
{
  "message": "Star成功"
}
```

或

```json
{
  "message": "取消Star成功"
}
```

**错误响应**:
- `404`: 知识库不存在
- `401`: 未授权访问
- `500`: Star知识库失败

### 取消Star知识库（独立接口）
专门用于取消Star知识库。

```http
DELETE /api/knowledge/{kb_id}/star
Authorization: Bearer {token}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID

**响应示例**:
```json
{
  "message": "取消Star成功"
}
```

**错误响应**:
- `404`: 知识库不存在或未找到Star记录
- `401`: 未授权访问
- `500`: 取消Star知识库失败

## 人设卡管理接口

### 上传人设卡
上传人设卡文件，支持多个文件同时上传。

```http
POST /api/persona/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

files: [文件1, 文件2, ...]
name: 人设卡名称
description: 人设卡描述
copyright_owner: 版权所有者（可选）
```

**参数说明**:
- `files` (必填): 人设卡文件列表，至少需要上传一个文件
- `name` (必填): 人设卡名称
- `description` (必填): 人设卡描述
- `copyright_owner` (可选): 版权所有者信息

**响应示例**:
```json
{
  "id": "pc123",
  "name": "我的人设卡",
  "description": "这是一个测试人设卡",
  "uploader_id": "user123",
  "copyright_owner": "版权所有者",
  "star_count": 0,
  "is_public": false,
  "is_pending": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**错误响应**:
- `400`: 名称和描述不能为空、至少需要上传一个文件
- `401`: 未授权访问
- `500`: 上传人设卡失败

### 获取公开人设卡列表
获取所有已审核通过的公开人设卡列表。

```http
GET /api/persona/public
```

**响应示例**:
```json
[
  {
    "id": "pc123",
    "name": "公开人设卡",
    "description": "这是一个公开的人设卡",
    "uploader_id": "user123",
    "copyright_owner": "版权所有者",
    "star_count": 8,
    "is_public": true,
    "is_pending": false,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

**错误响应**:
- `500`: 获取公开人设卡失败

### 获取人设卡内容
获取指定人设卡的详细内容。

```http
GET /api/persona/{pc_id}
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID

**响应示例**:
```json
{
  "content": "人设卡内容...",
  "metadata": {
    "file_count": 1,
    "total_size": 512
  }
}
```

**错误响应**:
- `404`: 人设卡不存在
- `500`: 获取人设卡内容失败

### 获取用户的人设卡列表
获取指定用户上传的所有人设卡。

```http
GET /api/persona/user/{user_id}
Authorization: Bearer {token}
```

**参数说明**:
- `user_id` (路径参数): 用户ID

**响应示例**:
```json
[
  {
    "id": "pc123",
    "name": "我的人设卡",
    "description": "用户人设卡描述",
    "uploader_id": "user123",
    "copyright_owner": "版权所有者",
    "star_count": 3,
    "is_public": false,
    "is_pending": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

**错误响应**:
- `403`: 没有权限查看其他用户的上传记录
- `401`: 未授权访问
- `500`: 获取用户人设卡失败

### 更新人设卡信息
更新人设卡元信息，仅限上传者、管理员或审核员。

```http
PUT /api/persona/{pc_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "新的名称",
  "description": "新的描述",
  "copyright_owner": "新的版权所有者"
}
```

**错误响应**:
- `401`: 未授权访问
- `403`: 权限不足
- `404`: 人设卡不存在
- `500`: 更新失败

### 添加人设卡文件
为人设卡追加文件。

```http
POST /api/persona/{pc_id}/files
Authorization: Bearer {token}
Content-Type: multipart/form-data

files: [文件1, 文件2, ...]
```

**错误响应**:
- `400`: 未上传文件
- `401`: 未授权访问
- `403`: 权限不足
- `404`: 人设卡不存在
- `500`: 上传失败

### 删除人设卡文件

```http
DELETE /api/persona/{pc_id}/{file_id}
Authorization: Bearer {token}
```

**错误响应**:
- `401`: 未授权访问
- `403`: 权限不足
- `404`: 文件或人设卡不存在
- `500`: 删除失败

### 下载人设卡全部文件

```http
GET /api/persona/{pc_id}/download
Authorization: Bearer {token}
```

**说明**: 私有人设卡仅上传者或管理员可下载。

**错误响应**:
- `401`: 未授权访问
- `403`: 无权下载
- `404`: 人设卡不存在
- `500`: 打包失败

### 下载单个人设卡文件

```http
GET /api/persona/{pc_id}/file/{file_id}
Authorization: Bearer {token}
```

**错误响应**:
- `401`: 未授权访问
- `403`: 无权下载
- `404`: 文件不存在
- `500`: 下载失败

### 删除人设卡
删除整个人设卡及其文件。

```http
DELETE /api/persona/{pc_id}
Authorization: Bearer {token}
```

**错误响应**:
- `401`: 未授权访问
- `403`: 权限不足
- `404`: 人设卡不存在
- `500`: 删除失败

### Star/取消Star人设卡
对人设卡进行Star或取消Star操作，接口会根据当前状态自动切换。

```http
POST /api/persona/{pc_id}/star
Authorization: Bearer {token}
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID

**响应示例**:
```json
{
  "message": "Star成功"
}
```

或

```json
{
  "message": "取消Star成功"
}
```

**错误响应**:
- `404`: 人设卡不存在
- `401`: 未授权访问
- `500`: Star人设卡失败

### 取消Star人设卡（独立接口）
专门用于取消Star人设卡。

```http
DELETE /api/persona/{pc_id}/star
Authorization: Bearer {token}
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID

**响应示例**:
```json
{
  "message": "取消Star成功"
}
```

**错误响应**:
- `404`: 人设卡不存在或未找到Star记录
- `401`: 未授权访问
- `500`: 取消Star人设卡失败

## 用户Star记录接口

### 获取用户Star的知识库和人设卡
获取当前用户Star的所有公开知识库和人设卡。

```http
GET /api/user/stars
Authorization: Bearer {token}
```

**响应示例**:
```json
[
  {
    "id": "star123",
    "type": "knowledge",
    "target_id": "kb123",
    "name": "我的知识库",
    "description": "知识库描述",
    "star_count": 10,
    "created_at": "2024-01-01T00:00:00"
  },
  {
    "id": "star456",
    "type": "persona",
    "target_id": "pc123",
    "name": "我的人设卡",
    "description": "人设卡描述",
    "star_count": 5,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

**错误响应**:
- `401`: 未授权访问
- `500`: 获取用户Star记录失败

## 审核管理接口

### 获取待审核知识库
获取所有待审核的知识库列表（需要admin或moderator权限）。

```http
GET /api/review/knowledge/pending
Authorization: Bearer {token}
```

**响应示例**:
```json
[
  {
    "id": "kb123",
    "name": "待审核知识库",
    "description": "待审核的知识库",
    "uploader_id": "user123",
    "copyright_owner": "上传者",
    "star_count": 0,
    "is_public": false,
    "is_pending": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

**错误响应**:
- `403`: 没有审核权限
- `401`: 未授权访问
- `500`: 获取待审核知识库失败

### 获取待审核人设卡
获取所有待审核的人设卡列表（需要admin或moderator权限）。

```http
GET /api/review/persona/pending
Authorization: Bearer {token}
```

**响应示例**:
```json
[
  {
    "id": "pc123",
    "name": "待审核人设卡",
    "description": "待审核的人设卡",
    "uploader_id": "user123",
    "copyright_owner": "上传者",
    "star_count": 0,
    "is_public": false,
    "is_pending": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

**错误响应**:
- `403`: 没有审核权限
- `401`: 未授权访问
- `500`: 获取待审核人设卡失败

### 审核通过知识库
审核通过指定的知识库（需要admin或moderator权限）。

```http
POST /api/review/knowledge/{kb_id}/approve
Authorization: Bearer {token}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID

**响应示例**:
```json
{
  "message": "审核通过"
}
```

**错误响应**:
- `403`: 没有审核权限
- `401`: 未授权访问
- `404`: 知识库不存在
- `500`: 审核知识库失败

### 审核拒绝知识库
审核拒绝指定的知识库，并发送拒绝通知（需要admin或moderator权限）。

```http
POST /api/review/knowledge/{kb_id}/reject
Authorization: Bearer {token}
Content-Type: application/json

{
  "reason": "拒绝原因"
}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID
- `reason` (请求体): 拒绝原因

**响应示例**:
```json
{
  "message": "审核拒绝，已发送通知"
}
```

**错误响应**:
- `403`: 没有审核权限
- `401`: 未授权访问
- `404`: 知识库不存在
- `500`: 审核知识库失败

### 审核通过人设卡
审核通过指定的人设卡（需要admin或moderator权限）。

```http
POST /api/review/persona/{pc_id}/approve
Authorization: Bearer {token}
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID

**响应示例**:
```json
{
  "message": "审核通过"
}
```

**错误响应**:
- `403`: 没有审核权限
- `401`: 未授权访问
- `404`: 人设卡不存在
- `500`: 审核人设卡失败

### 审核拒绝人设卡
审核拒绝指定的人设卡，并发送拒绝通知（需要admin或moderator权限）。

```http
POST /api/review/persona/{pc_id}/reject
Authorization: Bearer {token}
Content-Type: application/json

{
  "reason": "拒绝原因"
}
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID
- `reason` (请求体): 拒绝原因

**响应示例**:
```json
{
  "message": "审核拒绝，已发送通知"
}
```

**错误响应**:
- `403`: 没有审核权限
- `401`: 未授权访问
- `404`: 人设卡不存在
- `500`: 审核人设卡失败

## 消息管理接口

### 发送站内公告/消息
向指定用户发送站内公告或私信（常用于审核通知）。新增原生群发能力，可一次性向多位用户或全体用户推送公告。

```http
POST /api/messages/send
Authorization: Bearer {token}
Content-Type: application/json

{
  "recipient_id": "user456",
  "title": "审核结果通知",
  "content": "你好，这是一条测试消息",
  "message_type": "direct"
}
```

**公告群发示例**:

```json
{
  "title": "系统维护公告",
  "content": "今晚 23:00-23:30 将进行维护，请提前保存进度。",
  "message_type": "announcement",
  "broadcast_scope": "all_users"
}
```

**参数说明**:
- `title` (必填): 消息标题，用于在客户端列表中展示
- `content` (必填): 消息内容
- `message_type` (可选): `direct`（默认）或 `announcement`
- `recipient_id` (可选): 单个接收者用户ID（`direct`时必填）
- `recipient_ids` (可选): 批量接收者ID列表
- `broadcast_scope` (可选): 当前支持 `all_users`，一次向所有活跃用户推送
- `announcement` 类型至少需要 `recipient_ids`、`recipient_id` 之一或 `broadcast_scope=all_users`

**响应示例**:
```json
{
  "message_ids": ["msg123", "msg124"],
  "count": 2,
  "status": "sent"
}
```

**错误响应**:
- `400`: 消息内容/标题不能为空、缺少接收者
- `404`: 接收者不存在
- `401`: 未授权访问
- `500`: 发送消息失败

### 获取消息列表
获取当前用户的消息列表，可指定与特定用户的对话。

```http
GET /api/messages?other_user_id=user456&limit=50&offset=0
Authorization: Bearer {token}
```

**查询参数说明**:
- `other_user_id` (可选): 指定对话用户的ID，不指定则获取所有消息
- `limit` (可选): 返回消息数量限制，默认50，范围1-100
- `offset` (可选): 偏移量，默认0

**响应示例**:
```json
[
  {
    "id": "msg123",
    "sender_id": "user456",
    "recipient_id": "user789",
    "title": "审核结果通知",
    "content": "你好，这是一条测试消息",
    "message_type": "direct",
    "broadcast_scope": null,
    "is_read": false,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

**错误响应**:
- `400`: limit必须在1-100之间、offset不能为负数
- `401`: 未授权访问
- `500`: 获取消息列表失败

### 标记消息为已读
将指定消息标记为已读状态。

```http
POST /api/messages/{message_id}/read
Authorization: Bearer {token}
```

**参数说明**:
- `message_id` (路径参数): 消息ID

**响应示例**:
```json
{
  "status": "success",
  "message": "消息已标记为已读"
}
```

**错误响应**:
- `404`: 消息不存在
- `403`: 没有权限标记此消息为已读（非接收者）
- `401`: 未授权访问
- `500`: 标记消息已读失败

## 邮件服务接口

### 发送邮件（未实现）
发送邮件到指定邮箱（需要管理员权限）。
**状态**：未实现，文档仅提供规划信息，客户端调用将返回 `404` 或 `501`。

```http
POST /api/email/send
Authorization: Bearer {token}
Content-Type: application/json

{
  "receiver": "user@example.com",
  "subject": "测试邮件",
  "content": "这是一封测试邮件"
}
```

**请求参数**:

| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `receiver` | string | 是 | 接收者邮箱地址 |
| `subject` | string | 是 | 邮件主题 |
| `content` | string | 是 | 邮件正文 |

**预期响应**:
```json
{
  "message": "邮件发送成功"
}
```

**错误响应**:
- `403`: 没有权限
- `401`: 未授权访问
- `500`: 邮件发送失败

### 获取邮箱配置（未实现）
获取当前的邮箱服务配置信息（需要管理员权限）。
**状态**：未实现，文档仅提供规划信息，暂未返回真实配置。

```http
GET /api/email/config
Authorization: Bearer {token}
```

**预期响应**:
```json
{
  "mail_host": "smtp.example.com",
  "mail_user": "sender@example.com",
  "mail_port": 587,
  "mail_pwd": "******"
}
```

**错误响应**:
- `403`: 没有权限
- `401`: 未授权访问
- `500`: 获取配置失败

### 更新邮箱配置（未实现）
更新邮箱服务配置（需要管理员权限）。
**状态**：未实现，暂不支持动态更新。

```http
PUT /api/email/config
Authorization: Bearer {token}
Content-Type: application/json

{
  "mail_host": "smtp.newserver.com",
  "mail_user": "newsender@example.com",
  "mail_port": 587,
  "mail_pwd": "newpassword"
}
```

**请求参数**:

| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `mail_host` | string | 是 | SMTP 服务器地址 |
| `mail_user` | string | 是 | 邮箱用户名 |
| `mail_port` | integer | 是 | SMTP 端口 |
| `mail_pwd` | string | 是 | 邮箱密码 |

**预期响应**:
```json
{
  "message": "邮箱配置更新成功"
}
```

**错误响应**:
- `403`: 没有权限
- `401`: 未授权访问
- `500`: 更新配置失败

## 错误响应格式

所有错误响应都遵循以下格式：

```json
{
  "detail": "错误描述信息"
}
```

## 权限要求说明

### 角色权限
- **user**: 普通用户，可以上传、查看自己的内容
- **moderator**: 审核员，可以审核内容
- **admin**: 管理员，拥有所有权限

### 接口权限要求
- **公开接口**: 不需要认证，如 `/api/knowledge/public`
- **用户认证**: 需要登录，如 `/api/users/me`
- **审核权限**: 需要 moderator 或 admin 角色
- **管理权限**: 需要 admin 角色

## 常见错误码

| 状态码 | 描述 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权访问 |
| 403 | 禁止访问（权限不足） |
| 404 | 资源不存在 |
| 409 | 资源冲突（如重复Star） |
| 422 | 请求验证失败 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

## 限流说明

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
  "role": "user|moderator|admin",
  "created_at": "datetime"
}
```

### 知识库模型

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "uploader_id": "string",
  "copyright_owner": "string|null",
  "star_count": "integer",
  "is_public": "boolean",
  "is_pending": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 人设卡模型

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "uploader_id": "string",
  "copyright_owner": "string|null",
  "star_count": "integer",
  "is_public": "boolean",
  "is_pending": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 消息模型

```json
{
  "id": "string",
  "sender_id": "string",
  "recipient_id": "string",
  "title": "string",
  "content": "string",
  "is_read": "boolean",
  "created_at": "datetime"
}
```

### Star 模型

```json
{
  "id": "string",
  "user_id": "string",
  "target_id": "string",
  "target_type": "knowledge|persona",
  "created_at": "datetime"
}
```

### 邮件配置模型

```json
{
  "mail_host": "string",
  "mail_user": "string",
  "mail_port": "integer",
  "mail_pwd": "string"
}
```