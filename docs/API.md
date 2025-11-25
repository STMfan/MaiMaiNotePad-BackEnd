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
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "user123",
    "username": "testuser",
    "email": "user@example.com",
    "role": "user"
  }
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

**响应示例**:
```json
{
  "id": "user123",
  "username": "testuser",
  "email": "user@example.com",
  "role": "user",
  "avatar_url": "/uploads/avatars/user123.jpg",
  "avatar_updated_at": "2025-11-22T00:00:00"
}
```

**错误响应**:
- `401`: 未授权访问
- `500`: 获取用户信息失败

### 刷新访问令牌
使用刷新令牌获取新的访问令牌。

```http
POST /api/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

或

```http
POST /api/refresh
Content-Type: application/x-www-form-urlencoded

refresh_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**参数说明**:
- `refresh_token` (必填): 刷新令牌

**响应示例**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**错误响应**:
- `400`: 刷新令牌为空
- `401`: 无效的刷新令牌
- `500`: 刷新令牌失败

### 修改密码
修改当前用户的密码。

```http
PUT /api/users/me/password
Authorization: Bearer {token}
Content-Type: application/json

{
  "current_password": "oldpass123",
  "new_password": "newpass123",
  "confirm_password": "newpass123"
}
```

**参数说明**:
- `current_password` (必填): 当前密码
- `new_password` (必填): 新密码（长度不能少于6位）
- `confirm_password` (必填): 确认新密码

**响应示例**:
```json
{
  "message": "密码修改成功"
}
```

**错误响应**:
- `400`: 有未填写的字段、新密码与确认密码不匹配、密码长度不能少于6位、当前密码错误
- `401`: 未授权访问
- `500`: 修改密码失败

### 上传头像
上传当前用户的头像。

```http
POST /api/users/me/avatar
Authorization: Bearer {token}
Content-Type: multipart/form-data

avatar: [图片文件]
```

**参数说明**:
- `avatar` (必填): 头像图片文件，支持 JPG、JPEG、PNG、GIF、WEBP 格式，最大 2MB，最大尺寸 1024x1024 像素

**响应示例**:
```json
{
  "message": "头像上传成功",
  "avatar_url": "/uploads/avatars/user123.jpg",
  "avatar_updated_at": "2025-11-22T00:00:00"
}
```

**错误响应**:
- `400`: 文件格式不支持、文件大小超过限制、图片处理失败
- `401`: 未授权访问
- `500`: 上传头像失败

### 删除头像
删除当前用户的头像。

```http
DELETE /api/users/me/avatar
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "message": "头像删除成功"
}
```

**错误响应**:
- `401`: 未授权访问
- `500`: 删除头像失败

### 获取用户头像
获取指定用户的头像（如果用户没有上传头像，将返回自动生成的头像）。

```http
GET /api/users/{user_id}/avatar?size=200
```

**参数说明**:
- `user_id` (路径参数): 用户ID
- `size` (查询参数，可选): 头像尺寸，默认200

**响应**:
- 返回图片文件流，Content-Type: `image/jpeg` 或 `image/png`

**错误响应**:
- `404`: 用户不存在
- `500`: 获取头像失败

### 发送重置密码验证码
向指定邮箱发送重置密码验证码。

```http
POST /api/send_reset_password_code
Content-Type: application/x-www-form-urlencoded

email=user@example.com
```

**参数说明**:
- `email` (必填): 接收验证码的邮箱地址（必须是已注册的邮箱）

**响应示例**:
```json
{
  "message": "重置密码验证码已发送"
}
```

**错误响应**:
- `400`: 邮箱格式无效、该邮箱未注册
- `429`: 请求发送验证码过于频繁
- `500`: 发送验证码失败

### 重置密码
通过邮箱验证码重置密码。

```http
POST /api/reset_password
Content-Type: application/x-www-form-urlencoded

email=user@example.com&verification_code=123456&new_password=newpass123
```

**参数说明**:
- `email` (必填): 邮箱地址
- `verification_code` (必填): 邮箱验证码
- `new_password` (必填): 新密码（长度不能少于6位）

**响应示例**:
```json
{
  "success": true,
  "message": "密码重置成功"
}
```

**错误响应**:
- `400`: 有未填写的字段、密码长度不能少于6位、验证码错误或已失效
- `500`: 重置密码失败

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
content: 知识库正文（可选）
tags: 标签，逗号分隔或多值（可选）
```

**参数说明**:
- `files` (必填): 知识库文件列表，至少需要上传一个文件
- `name` (必填): 知识库名称
- `description` (必填): 知识库描述
- `copyright_owner` (可选): 版权所有者信息
- `content` (可选): 正文内容，用于直接存储在数据库中
- `tags` (可选): 标签，逗号分隔字符串或多值提交，接口会落库为逗号分隔

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
  "created_at": "2025-11-22T00:00:00",
  "updated_at": "2025-11-22T00:00:00"
}
```

**错误响应**:
- `400`: 名称和描述不能为空、至少需要上传一个文件
- `401`: 未授权访问
- `500`: 上传知识库失败

### 获取公开知识库列表
获取所有已审核通过的公开知识库列表，支持分页、搜索、筛选和排序。

```http
GET /api/knowledge/public?page=1&page_size=20&name=&uploader_id=&sort_by=created_at&sort_order=desc
```

**查询参数说明**:
- `page` (可选): 页码，从1开始，默认为1
- `page_size` (可选): 每页数量，范围1-100，默认为20
- `name` (可选): 按名称搜索，支持模糊匹配
- `uploader_id` (可选): 按上传者ID筛选
- `sort_by` (可选): 排序字段，可选值：`created_at`、`updated_at`、`star_count`，默认为 `created_at`
- `sort_order` (可选): 排序顺序，可选值：`asc`、`desc`，默认为 `desc`

**响应示例**:
```json
{
  "items": [
    {
      "id": "kb123",
      "name": "公开知识库",
      "description": "这是一个公开的知识库",
      "uploader_id": "user123",
      "copyright_owner": "版权所有者",
      "star_count": 10,
      "is_public": true,
      "is_pending": false,
      "created_at": "2025-11-22T00:00:00",
      "updated_at": "2025-11-22T00:00:00",
      "files": [
        {
          "file_id": "file123",
          "original_name": "数据集.txt",
          "file_size": 2048
        }
      ],
      "size": 2048,
      "download_url": "/api/knowledge/kb123/download",
      "tags": [],
      "author": "版权所有者",
      "author_id": "user123"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

**错误响应**:
- `400`: 查询参数无效（如page_size超出范围）
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
  "id": "kb123",
  "name": "我的知识库",
  "description": "详细描述……",
  "uploader_id": "user123",
  "copyright_owner": "版权所有者",
  "star_count": 5,
  "is_public": false,
  "is_pending": false,
  "created_at": "2025-11-22T00:00:00",
  "updated_at": "2025-11-24T10:00:00",
  "files": [
    {
      "file_id": "file123",
      "original_name": "数据集A.txt",
      "file_size": 2048
    },
    {
      "file_id": "file456",
      "original_name": "配置B.json",
      "file_size": 1024
    }
  ],
  "size": 3072,
  "download_url": "/api/knowledge/kb123/download",
  "content": "扩展内容（可选）",
  "tags": ["测试", "样例"],
  "downloads": 12,
  "preview_url": null,
  "version": "v1.0.0",
  "author": "版权所有者",
  "author_id": "user123"
}
```

**字段说明**:
- `files`: 文件数组，每项包含 `file_id`（用于单文件下载/删除）、`original_name`（展示用文件名）、`file_size`（字节）。
- `size`: 所有文件大小总和（字节）。
- `download_url`: 整包下载地址，已登录用户可直接使用。

**错误响应**:
- `404`: 知识库不存在
- `500`: 获取知识库内容失败

### 获取用户的知识库列表
获取指定用户上传的知识库，支持分页/筛选/排序；管理员和审核员可以查看他人记录。

```http
GET /api/knowledge/user/{user_id}?page=1&page_size=20&name=&tag=&status=all&sort_by=created_at&sort_order=desc
Authorization: Bearer {token}
```

**查询参数说明**:
- `user_id` (路径参数): 用户ID
- `page` / `page_size` (可选): 分页参数，默认 `1 / 20`，`page_size` 最大 100
- `name` (可选): 按名称模糊搜索
- `tag` (可选): 按标签模糊搜索
- `status` (可选): `all/pending/approved/rejected`
- `sort_by` (可选): `created_at/updated_at/name/downloads/star_count`
- `sort_order` (可选): `asc/desc`

**响应示例**:
```json
{
  "items": [
    {
      "id": "kb123",
      "name": "我的知识库",
      "description": "用户知识库描述",
      "uploader_id": "user123",
      "copyright_owner": "版权所有者",
      "content": "正文内容",
      "tags": ["测试", "样例"],
      "star_count": 5,
      "downloads": 12,
      "is_public": false,
      "is_pending": true,
      "created_at": "2025-11-22T00:00:00",
      "updated_at": "2025-11-22T00:00:00"
    }
  ],
  "total": 32,
  "page": 1,
  "page_size": 20
}
```

**错误响应**:
- `403`: 没有权限查看其他用户的上传记录（非管理员/审核员）
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

**响应示例**:
```json
{
  "message": "文件删除成功",
  "knowledge_deleted": false
}
```

**特殊说明**: 当删除最后一个文件时，`knowledge_deleted` 为 `true`，系统会自动清理整条知识库记录及其上传记录，等价于调用 `DELETE /api/knowledge/{kb_id}`。

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

### 检查知识库Star状态
检查指定知识库是否已被当前用户Star。

```http
GET /api/knowledge/{kb_id}/starred
Authorization: Bearer {token}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID

**响应示例**:
```json
{
  "starred": true
}
```

**错误响应**:
- `401`: 未授权访问
- `404`: 知识库不存在
- `500`: 检查Star状态失败

### 更新知识库信息
修改知识库的基本信息（名称、描述、版权所有者等）。

```http
PUT /api/knowledge/{kb_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "更新后的知识库名称",
  "description": "更新后的描述",
  "copyright_owner": "版权所有者"
}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID
- `name` (可选): 知识库名称
- `description` (可选): 知识库描述
- `copyright_owner` (可选): 版权所有者

**响应示例**:
```json
{
  "id": "kb123",
  "name": "更新后的知识库名称",
  "description": "更新后的描述",
  "uploader_id": "user123",
  "copyright_owner": "版权所有者",
  "star_count": 5,
  "is_public": true,
  "is_pending": false,
  "created_at": "2025-11-22T00:00:00",
  "updated_at": "2025-11-22T01:00:00"
}
```

**错误响应**:
- `400`: 没有提供要更新的字段
- `401`: 未授权访问
- `403`: 没有权限修改此知识库（只有上传者和管理员可以修改）
- `404`: 知识库不存在
- `500`: 修改知识库失败

### 添加知识库文件
向已存在的知识库添加新文件。

```http
POST /api/knowledge/{kb_id}/files
Authorization: Bearer {token}
Content-Type: multipart/form-data

files: [文件1, 文件2, ...]
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID
- `files` (必填): 要添加的文件列表，至少需要上传一个文件

**响应示例**:
```json
{
  "message": "文件添加成功"
}
```

**错误响应**:
- `400`: 至少需要上传一个文件
- `401`: 未授权访问
- `403`: 没有权限向此知识库添加文件（只有上传者和管理员可以添加）
- `404`: 知识库不存在
- `500`: 添加文件失败

### 删除知识库文件
删除知识库中的指定文件。

```http
DELETE /api/knowledge/{kb_id}/{file_id}
Authorization: Bearer {token}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID
- `file_id` (路径参数): 要删除的文件ID

**响应示例**:
```json
{
  "message": "文件删除成功"
}
```

**错误响应**:
- `401`: 未授权访问
- `403`: 没有权限删除此知识库的文件（只有上传者和管理员可以删除）
- `404`: 知识库不存在
- `500`: 删除文件失败

### 下载知识库压缩包
下载知识库的所有文件压缩包（ZIP格式）。

```http
GET /api/knowledge/{kb_id}/download
Authorization: Bearer {token}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID

**响应**:
- 返回ZIP文件流，Content-Type: `application/zip`

**错误响应**:
- `401`: 未授权访问
- `404`: 知识库不存在
- `500`: 下载失败

### 下载知识库单个文件
下载知识库中的指定文件。

```http
GET /api/knowledge/{kb_id}/file/{file_id}
Authorization: Bearer {token}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID
- `file_id` (路径参数): 文件ID

**响应**:
- 返回文件流，Content-Type: `application/octet-stream`

**错误响应**:
- `401`: 未授权访问
- `403`: 没有权限下载此知识库（私有知识库只有上传者和管理员可以下载）
- `404`: 知识库或文件不存在
- `500`: 下载文件失败

### 删除知识库
删除整个知识库及其所有文件。

```http
DELETE /api/knowledge/{kb_id}
Authorization: Bearer {token}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID

**响应示例**:
```json
{
  "message": "知识库删除成功"
}
```

**错误响应**:
- `401`: 未授权访问
- `403`: 没有权限删除此知识库（只有上传者和管理员可以删除）
- `404`: 知识库不存在
- `500`: 删除知识库失败

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
content: 人设卡正文（可选）
tags: 标签，逗号分隔或多值（可选）
```

**参数说明**:
- `files` (必填): 人设卡文件列表，至少需要上传一个文件
- `name` (必填): 人设卡名称
- `description` (必填): 人设卡描述
- `copyright_owner` (可选): 版权所有者信息
- `content` (可选): 正文内容，用于直接存储在数据库中
- `tags` (可选): 标签，逗号分隔字符串或多值提交，接口会落库为逗号分隔

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
  "created_at": "2025-11-22T00:00:00",
  "updated_at": "2025-11-22T00:00:00"
}
```

**错误响应**:
- `400`: 名称和描述不能为空、至少需要上传一个文件
- `401`: 未授权访问
- `500`: 上传人设卡失败

### 获取公开人设卡列表
获取所有已审核通过的公开人设卡列表，支持分页、搜索、筛选和排序。

```http
GET /api/persona/public?page=1&page_size=20&name=&uploader_id=&sort_by=created_at&sort_order=desc
```

**查询参数说明**:
- `page` (可选): 页码，从1开始，默认为1
- `page_size` (可选): 每页数量，范围1-100，默认为20
- `name` (可选): 按名称搜索，支持模糊匹配
- `uploader_id` (可选): 按上传者ID筛选
- `sort_by` (可选): 排序字段，可选值：`created_at`、`updated_at`、`star_count`，默认为 `created_at`
- `sort_order` (可选): 排序顺序，可选值：`asc`、`desc`，默认为 `desc`

**响应示例**:
```json
{
  "items": [
    {
      "id": "pc123",
      "name": "公开人设卡",
      "description": "这是一个公开的人设卡",
      "uploader_id": "user123",
      "copyright_owner": "版权所有者",
      "star_count": 8,
      "is_public": true,
      "is_pending": false,
      "created_at": "2025-11-22T00:00:00",
      "updated_at": "2025-11-22T00:00:00"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20
}
```

**错误响应**:
- `400`: 查询参数无效（如page_size超出范围）
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
获取指定用户上传的人设卡，支持分页/筛选/排序；管理员和审核员可以查看他人记录。

```http
GET /api/persona/user/{user_id}?page=1&page_size=20&name=&tag=&status=all&sort_by=created_at&sort_order=desc
Authorization: Bearer {token}
```

**查询参数说明**:
- `user_id` (路径参数): 用户ID
- `page` / `page_size` (可选): 分页参数，默认 `1 / 20`，`page_size` 最大 100
- `name` (可选): 按名称模糊搜索
- `tag` (可选): 按标签模糊搜索
- `status` (可选): `all/pending/approved/rejected`
- `sort_by` (可选): `created_at/updated_at/name/downloads/star_count`
- `sort_order` (可选): `asc/desc`

**响应示例**:
```json
{
  "items": [
    {
      "id": "pc123",
      "name": "我的人设卡",
      "description": "用户人设卡描述",
      "uploader_id": "user123",
      "copyright_owner": "版权所有者",
      "content": "正文内容",
      "tags": ["角色", "冒险"],
      "star_count": 3,
      "downloads": 7,
      "is_public": false,
      "is_pending": true,
      "created_at": "2025-11-22T00:00:00",
      "updated_at": "2025-11-22T00:00:00"
    }
  ],
  "total": 18,
  "page": 1,
  "page_size": 20
}
```

**错误响应**:
- `403`: 没有权限查看其他用户的上传记录（非管理员/审核员）
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

### 检查人设卡Star状态
检查指定人设卡是否已被当前用户Star。

```http
GET /api/persona/{pc_id}/starred
Authorization: Bearer {token}
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID

**响应示例**:
```json
{
  "starred": true
}
```

**错误响应**:
- `401`: 未授权访问
- `404`: 人设卡不存在
- `500`: 检查Star状态失败

### 更新人设卡信息
修改人设卡的基本信息（名称、描述、版权所有者等）。

```http
PUT /api/persona/{pc_id}
Authorization: Bearer {token}
Content-Type: application/x-www-form-urlencoded

name=更新后的人设卡名称&description=更新后的描述&copyright_owner=版权所有者
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID
- `name` (必填): 人设卡名称
- `description` (必填): 人设卡描述
- `copyright_owner` (可选): 版权所有者

**响应示例**:
```json
{
  "id": "pc123",
  "name": "更新后的人设卡名称",
  "description": "更新后的描述",
  "uploader_id": "user123",
  "copyright_owner": "版权所有者",
  "star_count": 3,
  "is_public": true,
  "is_pending": false,
  "created_at": "2025-11-22T00:00:00",
  "updated_at": "2025-11-22T01:00:00"
}
```

**错误响应**:
- `400`: 名称和描述不能为空
- `401`: 未授权访问
- `403`: 没有权限修改此人设卡（只有上传者和管理员可以修改）
- `404`: 人设卡不存在
- `500`: 修改人设卡失败

### 添加人设卡文件
向已存在的人设卡添加新文件。

```http
POST /api/persona/{pc_id}/files
Authorization: Bearer {token}
Content-Type: multipart/form-data

files: [文件1, 文件2, ...]
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID
- `files` (必填): 要添加的文件列表，至少需要上传一个文件

**响应示例**:
```json
{
  "message": "文件添加成功"
}
```

**错误响应**:
- `400`: 至少需要上传一个文件
- `401`: 未授权访问
- `403`: 没有权限向此人设卡添加文件（只有上传者和管理员可以添加）
- `404`: 人设卡不存在
- `500`: 添加文件失败

### 删除人设卡文件
删除人设卡中的指定文件。

```http
DELETE /api/persona/{pc_id}/{file_id}
Authorization: Bearer {token}
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID
- `file_id` (路径参数): 要删除的文件ID

**响应示例**:
```json
{
  "message": "文件删除成功"
}
```

**错误响应**:
- `401`: 未授权访问
- `403`: 没有权限从此人设卡删除文件（只有上传者和管理员可以删除）
- `404`: 人设卡不存在
- `500`: 删除文件失败

### 下载人设卡压缩包
下载人设卡的所有文件压缩包（ZIP格式）。

```http
GET /api/persona/{pc_id}/download
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID

**响应**:
- 返回ZIP文件流，Content-Type: `application/zip`

**错误响应**:
- `404`: 人设卡不存在
- `500`: 下载失败

### 下载人设卡单个文件
下载人设卡中的指定文件。

```http
GET /api/persona/{pc_id}/file/{file_id}
Authorization: Bearer {token}
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID
- `file_id` (路径参数): 文件ID

**响应**:
- 返回文件流，Content-Type: `application/octet-stream`

**错误响应**:
- `401`: 未授权访问
- `403`: 没有权限下载此人设卡（私有人设卡只有上传者和管理员可以下载）
- `404`: 人设卡或文件不存在
- `500`: 下载文件失败

### 删除人设卡
删除整个人设卡及其所有文件。

```http
DELETE /api/persona/{pc_id}
Authorization: Bearer {token}
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID

**响应示例**:
```json
{
  "message": "人设卡删除成功"
}
```

**错误响应**:
- `401`: 未授权访问
- `403`: 没有权限删除此人设卡（只有上传者和管理员可以删除）
- `404`: 人设卡不存在
- `500`: 删除人设卡失败

## 用户Star记录接口

### 获取用户Star的知识库和人设卡
获取当前用户Star的所有公开知识库和人设卡，支持分页、类型过滤与排序。

```http
GET /api/user/stars?includeDetails=false&page=1&page_size=20&sort_by=created_at&sort_order=desc&type=all
Authorization: Bearer {token}
```

**查询参数说明**:
- `includeDetails` (可选): 是否包含完整详情，默认为 `false`
- `page` / `page_size` (可选): 分页参数，默认 `1 / 20`，`page_size` 最大 50
- `sort_by` (可选): `created_at` 或 `star_count`
- `sort_order` (可选): `asc/desc`
- `type` (可选): `knowledge/persona/all`，默认 `all`

**响应示例**:
```json
{
  "items": [
    {
      "id": "star123",
      "type": "knowledge",
      "target_id": "kb123",
      "name": "我的知识库",
      "description": "知识库描述",
      "star_count": 10,
      "created_at": "2025-11-22T00:00:00"
    },
    {
      "id": "star456",
      "type": "persona",
      "target_id": "pc123",
      "name": "我的人设卡",
      "description": "人设卡描述",
      "star_count": 5,
      "created_at": "2025-11-22T00:00:00"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20
}
```

**错误响应**:
- `400`: `type`/`sort_by`/`sort_order` 参数不合法
- `401`: 未授权访问
- `500`: 获取收藏记录失败

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
    "created_at": "2025-11-22T00:00:00",
    "updated_at": "2025-11-22T00:00:00"
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
    "created_at": "2025-11-22T00:00:00",
    "updated_at": "2025-11-22T00:00:00"
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
    "created_at": "2025-11-22T00:00:00"
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

## 管理员接口（需要admin权限）

### 获取广播消息统计
获取系统广播消息的统计数据。

```http
GET /api/admin/broadcast-messages
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "total_broadcasts": 10,
  "total_recipients": 500,
  "recent_broadcasts": [...]
}
```

**错误响应**:
- `403`: 没有管理员权限
- `401`: 未授权访问
- `500`: 获取统计数据失败

### 获取系统统计数据
获取系统的整体统计数据。

```http
GET /api/admin/stats
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "total_users": 100,
  "total_knowledge_bases": 50,
  "total_persona_cards": 30,
  "pending_reviews": 5
}
```

**错误响应**:
- `403`: 没有管理员权限
- `401`: 未授权访问
- `500`: 获取统计数据失败

### 获取最近注册用户
获取最近注册的用户列表。

```http
GET /api/admin/recent-users?limit=10
Authorization: Bearer {token}
```

**查询参数说明**:
- `limit` (可选): 返回数量限制，默认10

**响应示例**:
```json
[
  {
    "id": "user123",
    "username": "newuser",
    "email": "user@example.com",
    "created_at": "2025-11-22T00:00:00"
  }
]
```

**错误响应**:
- `403`: 没有管理员权限
- `401`: 未授权访问
- `500`: 获取用户列表失败

### 获取用户列表
获取所有用户列表，支持分页和搜索。

```http
GET /api/admin/users?page=1&page_size=20&search=
Authorization: Bearer {token}
```

**查询参数说明**:
- `page` (可选): 页码，从1开始，默认为1
- `page_size` (可选): 每页数量，默认20
- `search` (可选): 搜索关键词（用户名或邮箱）

**响应示例**:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

**错误响应**:
- `403`: 没有管理员权限
- `401`: 未授权访问
- `500`: 获取用户列表失败

### 更新用户角色
更新指定用户的角色。

```http
PUT /api/admin/users/{user_id}/role
Authorization: Bearer {token}
Content-Type: application/json

{
  "role": "moderator"
}
```

**参数说明**:
- `user_id` (路径参数): 用户ID
- `role` (请求体): 新角色（user、moderator、admin）

**响应示例**:
```json
{
  "message": "用户角色更新成功"
}
```

**错误响应**:
- `400`: 无效的角色
- `403`: 没有管理员权限
- `404`: 用户不存在
- `500`: 更新用户角色失败

### 删除用户
删除指定用户。

```http
DELETE /api/admin/users/{user_id}
Authorization: Bearer {token}
```

**参数说明**:
- `user_id` (路径参数): 用户ID

**响应示例**:
```json
{
  "message": "用户删除成功"
}
```

**错误响应**:
- `403`: 没有管理员权限
- `404`: 用户不存在
- `500`: 删除用户失败

### 创建新用户
管理员创建新用户。

```http
POST /api/admin/users
Authorization: Bearer {token}
Content-Type: application/json

{
  "username": "newuser",
  "password": "password123",
  "email": "user@example.com",
  "role": "user"
}
```

**参数说明**:
- `username` (必填): 用户名
- `password` (必填): 密码
- `email` (必填): 邮箱地址
- `role` (可选): 角色，默认为user

**响应示例**:
```json
{
  "id": "user123",
  "username": "newuser",
  "email": "user@example.com",
  "role": "user"
}
```

**错误响应**:
- `400`: 参数错误、用户名或邮箱已存在
- `403`: 没有管理员权限
- `500`: 创建用户失败

### 获取所有知识库（管理员）
获取所有知识库，包括待审核和已拒绝的（需要管理员权限）。

```http
GET /api/admin/knowledge/all?page=1&limit=20&status=pending&search=text&uploader=userid-or-name&order_by=created_at&order_dir=desc
Authorization: Bearer {token}
```

**查询参数说明**:
- `page` (可选): 页码，从1开始，默认为1
- `limit` (可选): 每页数量，默认20，最大100
- `status` (可选): 内容状态，可选 `pending` / `approved` / `rejected`
- `search` (可选): 关键字，匹配名称或描述
- `uploader` (可选): 上传者筛选，支持精确ID或用户名模糊匹配
- `order_by` (可选): 排序字段，支持 `created_at`、`updated_at`、`star_count`、`name`、`downloads`、`is_public`，默认为 `created_at`
- `order_dir` (可选): 排序方向，`asc` 或 `desc`，默认为 `desc`

**响应示例**:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

**错误响应**:
- `403`: 没有管理员权限
- `401`: 未授权访问
- `500`: 获取知识库列表失败

### 获取所有人设卡（管理员）
获取所有人设卡，包括待审核和已拒绝的（需要管理员权限）。

```http
GET /api/admin/persona/all?page=1&limit=20&status=approved&uploader=name&order_by=star_count&order_dir=asc
Authorization: Bearer {token}
```

**查询参数说明**:
- `page` (可选): 页码，从1开始，默认为1
- `limit` (可选): 每页数量，默认20，最大100
- `status` (可选): 内容状态，可选 `pending` / `approved` / `rejected`
- `search` (可选): 关键字，匹配名称或描述
- `uploader` (可选): 上传者筛选，支持精确ID或用户名模糊匹配
- `order_by` (可选): 排序字段，支持 `created_at`、`updated_at`、`star_count`、`name`、`downloads`、`is_public`，默认为 `created_at`
- `order_dir` (可选): 排序方向，`asc` 或 `desc`，默认为 `desc`

**响应示例**:
```json
{
  "items": [...],
  "total": 50,
  "page": 1,
  "page_size": 20
}
```

**错误响应**:
- `403`: 没有管理员权限
- `401`: 未授权访问
- `500`: 获取人设卡列表失败

### 恢复知识库审核状态
将知识库的审核状态恢复为待审核（需要管理员权限）。

```http
POST /api/admin/knowledge/{kb_id}/revert
Authorization: Bearer {token}
```

**参数说明**:
- `kb_id` (路径参数): 知识库ID

**响应示例**:
```json
{
  "message": "知识库审核状态已恢复"
}
```

**错误响应**:
- `403`: 没有管理员权限
- `404`: 知识库不存在
- `500`: 恢复审核状态失败

### 恢复人设卡审核状态
将人设卡的审核状态恢复为待审核（需要管理员权限）。

```http
POST /api/admin/persona/{pc_id}/revert
Authorization: Bearer {token}
```

**参数说明**:
- `pc_id` (路径参数): 人设卡ID

**响应示例**:
```json
{
  "message": "人设卡审核状态已恢复"
}
```

**错误响应**:
- `403`: 没有管理员权限
- `404`: 人设卡不存在
- `500`: 恢复审核状态失败

### 获取上传历史记录
获取所有上传历史记录（需要管理员权限）。

```http
GET /api/admin/upload-history?page=1&page_size=20
Authorization: Bearer {token}
```

**查询参数说明**:
- `page` (可选): 页码，从1开始，默认为1
- `page_size` (可选): 每页数量，默认20

**响应示例**:
```json
{
  "items": [...],
  "total": 200,
  "page": 1,
  "page_size": 20
}
```

**错误响应**:
- `403`: 没有管理员权限
- `401`: 未授权访问
- `500`: 获取上传历史失败

### 获取上传统计数据
获取上传相关的统计数据（需要管理员权限）。

```http
GET /api/admin/upload-stats
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "total_uploads": 200,
  "pending_uploads": 10,
  "approved_uploads": 150,
  "rejected_uploads": 40
}
```

**错误响应**:
- `403`: 没有管理员权限
- `401`: 未授权访问
- `500`: 获取统计数据失败

### 删除上传记录
删除指定的上传记录（需要管理员权限）。

```http
DELETE /api/admin/uploads/{upload_id}
Authorization: Bearer {token}
```

**参数说明**:
- `upload_id` (路径参数): 上传记录ID

**响应示例**:
```json
{
  "message": "上传记录删除成功"
}
```

**错误响应**:
- `403`: 没有管理员权限
- `404`: 上传记录不存在
- `500`: 删除上传记录失败

### 重新处理上传
重新处理指定的上传记录（需要管理员权限）。

```http
POST /api/admin/uploads/{upload_id}/reprocess
Authorization: Bearer {token}
```

**参数说明**:
- `upload_id` (路径参数): 上传记录ID

**响应示例**:
```json
{
  "message": "上传记录已重新处理"
}
```

**错误响应**:
- `403`: 没有管理员权限
- `404`: 上传记录不存在
- `500`: 重新处理失败

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

---

## 📚 相关文档

- [端点清单](./端点清单.md) - API端点完整清单
- [更新总结](./更新总结.md) - 更新内容总结
- [CHANGELOG.md](./CHANGELOG.md) - 变更日志
- [数据库模型文档](./database_models.md) - 数据库结构说明

---

**文档版本**: 2.0  
**最后更新**: 2025-11-22  
**维护者**: 开发团队
```
