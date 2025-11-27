# MaiMNP-rereremake-Flutter 后端服务

这是一个基于 FastAPI 构建的后端服务，提供知识库管理、人设卡功能、用户管理、消息系统和审核功能。

## 🚀 功能特性

### 📚 知识库管理
- **文件上传**: 支持知识库文件上传、正文(`content`)与标签(`tags`)入库，附带作者信息
- **审核系统**: 完整的审核流程（待审核、通过、拒绝）
- **搜索筛选**: 支持按标签、关键词搜索和筛选，个人上传记录支持分页/排序/状态过滤
- **Star功能**: 用户可以Star感兴趣的知识库
- **权限控制**: 基于角色的访问控制

### 🎭 人设卡管理
- **文件上传**: 支持人设卡文件上传、正文(`content`)与标签(`tags`)入库，附带作者信息
- **审核系统**: 与知识库相同的审核流程
- **分类管理**: 支持分类和标签系统，个人上传记录支持分页/排序/状态过滤
- **Star功能**: 用户可以Star感兴趣的人设卡
- **个人收藏**: 查看用户已Star的人设卡

### 👥 用户系统
- **用户认证**: JWT token认证机制
- **角色管理**: 支持admin、moderator、user三种角色
- **个人中心**: 查看个人上传记录和收藏（分页/筛选/排序）
- **消息系统**: 审核结果通知和消息管理

### 🔧 管理功能
- **审核面板**: 管理员和审核员可以审核内容
- **用户管理**: 管理员可以管理用户权限
- **内容运营**: 管理端内容列表支持上传者过滤、排序字段/方向配置
- **数据统计**: 查看系统使用情况和统计数据

### 📧 邮件服务
- **邮件发送**: 支持发送邮件通知
- **SMTP配置**: 可配置的SMTP服务器设置
- **邮箱认证**: 支持QQ邮箱等主流邮箱服务

## 🏗️ 技术栈

- **后端框架**: FastAPI (Python)
- **数据存储**: SQLite数据库（轻量级关系型数据库）
- **ORM框架**: SQLAlchemy（Python对象关系映射）
- **认证**: JWT (JSON Web Tokens)
- **密码安全**: bcrypt哈希
- **文件上传**: 支持多种文件格式
- **API文档**: 自动生成Swagger文档

## 📁 项目结构

```
backend-python-remake/
├── main.py              # FastAPI应用入口
├── api_routes.py        # API路由定义
├── database_models.py   # 数据库模型定义
├── database_manager.py  # 数据库管理器
├── file_upload.py       # 文件上传服务
├── user_management.py   # 用户管理模块
├── email_service.py     # 邮件服务模块
├── logger.py           # 日志记录模块
├── requirements.txt    # Python依赖
├── README.md          # 项目文档
├── TODO.md           # 待办事项
├── .gitignore        # Git忽略配置
├── .env               # 环境变量配置
├── .env.template      # 环境变量模板
└── data/             # 数据存储目录
    └── mainnp.db     # SQLite数据库文件
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- pip包管理器

### 1. 克隆项目
```bash
git clone <repository-url>
cd backend-python-remake
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 初始化数据库
首次运行时会自动创建SQLite数据库文件 `data/mainnp.db`

### 4. 启动服务器

#### 开发模式（推荐）
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 9278 --reload
```

#### 生产模式
```bash
# 使用gunicorn
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:9278

# 或使用Docker
docker build -t mainnp-backend .
docker run -p 9278:9278 mainnp-backend
```

### 5. 访问API文档
- Swagger UI: http://localhost:9278/docs
- ReDoc: http://localhost:9278/redoc

### 6. 测试API
可以使用内置的测试用户登录：
- 用户名: testuser
- 密码: testpass

或者通过Swagger UI界面进行交互式测试。

## 📖 API接口文档

### 认证相关
- `POST /api/token` - 用户登录获取token（返回access_token和refresh_token）
- `POST /api/refresh` - 刷新访问令牌
- `POST /api/send_verification_code` - 发送注册验证码
- `POST /api/send_reset_password_code` - 发送重置密码验证码
- `POST /api/reset_password` - 重置密码
- `POST /api/user/register` - 用户注册
- `GET /api/users/me` - 获取当前用户信息
- `PUT /api/users/me/password` - 修改密码
- `POST /api/users/me/avatar` - 上传头像
- `DELETE /api/users/me/avatar` - 删除头像
- `GET /api/users/{user_id}/avatar` - 获取用户头像

### 知识库相关
- `POST /api/knowledge/upload` - 上传知识库（支持正文`content`与标签`tags`）
- `GET /api/knowledge/public` - 获取公开知识库
- `GET /api/knowledge/{kb_id}` - 获取指定知识库详情
- `GET /api/knowledge/user/{user_id}` - 获取用户知识库（分页，支持名称/标签/状态筛选与排序，管理员/审核员可查看他人）
- `PUT /api/knowledge/{kb_id}` - 更新知识库信息
- `POST /api/knowledge/{kb_id}/files` - 添加知识库文件
- `DELETE /api/knowledge/{kb_id}/{file_id}` - 删除知识库文件（删除最后一个文件时自动清理整条知识库）
- `GET /api/knowledge/{kb_id}/download` - 下载知识库全部文件（ZIP）
- `GET /api/knowledge/{kb_id}/file/{file_id}` - 下载知识库单个文件
- `DELETE /api/knowledge/{kb_id}` - 删除知识库
- `POST /api/knowledge/{kb_id}/star` - Star知识库
- `DELETE /api/knowledge/{kb_id}/star` - 取消Star知识库
- `GET /api/knowledge/{kb_id}/starred` - 检查知识库Star状态

### 人设卡相关
- `POST /api/persona/upload` - 上传人设卡（支持正文`content`与标签`tags`）
- `GET /api/persona/public` - 获取公开人设卡
- `GET /api/persona/{pc_id}` - 获取指定人设卡详情
- `GET /api/persona/user/{user_id}` - 获取用户人设卡（分页，支持名称/标签/状态筛选与排序，管理员/审核员可查看他人）
- `PUT /api/persona/{pc_id}` - 更新人设卡信息
- `POST /api/persona/{pc_id}/files` - 添加人设卡文件
- `DELETE /api/persona/{pc_id}/{file_id}` - 删除人设卡文件
- `GET /api/persona/{pc_id}/download` - 下载人设卡全部文件（ZIP）
- `GET /api/persona/{pc_id}/file/{file_id}` - 下载人设卡单个文件
- `DELETE /api/persona/{pc_id}` - 删除人设卡
- `POST /api/persona/{pc_id}/star` - Star人设卡
- `DELETE /api/persona/{pc_id}/star` - 取消Star人设卡
- `GET /api/persona/{pc_id}/starred` - 检查人设卡Star状态

### 审核相关（需要admin/moderator权限）
- `GET /api/review/knowledge/pending` - 获取待审核知识库
- `GET /api/review/persona/pending` - 获取待审核人设卡
- `POST /api/review/knowledge/{kb_id}/approve` - 审核通过知识库
- `POST /api/review/knowledge/{kb_id}/reject` - 审核拒绝知识库（需在请求体中传递 `{"reason": "拒绝原因"}`）
- `POST /api/review/persona/{pc_id}/approve` - 审核通过人设卡
- `POST /api/review/persona/{pc_id}/reject` - 审核拒绝人设卡（需在请求体中传递 `{"reason": "拒绝原因"}`）

### 消息相关
- `POST /api/messages/send` - 发送消息
- `GET /api/messages` - 获取用户消息
- `POST /api/messages/{message_id}/read` - 标记消息为已读

### 邮件服务相关（未实现）
- `POST /api/email/send` - 发送邮件通知（需要管理员权限）**状态：未实现**
- `GET /api/email/config` - 获取邮箱配置信息（需要管理员权限）**状态：未实现**
- `PUT /api/email/config` - 更新邮箱配置（需要管理员权限）**状态：未实现**

**注意**：邮件服务API目前未实现，文档仅提供规划信息。系统内部使用邮件服务发送验证码等功能，但未提供公开的API接口。

### 用户相关
- `GET /api/user/stars` - 获取用户Star的知识库和人设卡（分页，支持类型过滤、排序、可选 `includeDetails`）

### 管理员相关（需要admin权限）
- `GET /api/admin/broadcast-messages` - 获取广播消息统计
- `GET /api/admin/stats` - 获取系统统计数据
- `GET /api/admin/recent-users` - 获取最近注册用户
- `GET /api/admin/users` - 获取用户列表（支持分页和搜索）
- `PUT /api/admin/users/{user_id}/role` - 更新用户角色
- `DELETE /api/admin/users/{user_id}` - 删除用户
- `POST /api/admin/users` - 创建新用户
- `GET /api/admin/knowledge/all` - 获取所有知识库（管理员，支持上传者筛选与排序字段/方向）
- `GET /api/admin/persona/all` - 获取所有人设卡（管理员，支持上传者筛选与排序字段/方向）
- `POST /api/admin/knowledge/{kb_id}/revert` - 恢复知识库审核状态
- `POST /api/admin/persona/{pc_id}/revert` - 恢复人设卡审核状态
- `GET /api/admin/upload-history` - 获取上传历史记录
- `GET /api/admin/upload-stats` - 获取上传统计数据
- `DELETE /api/admin/uploads/{upload_id}` - 删除上传记录
- `POST /api/admin/uploads/{upload_id}/reprocess` - 重新处理上传

## 🔐 权限说明

### 角色定义
- **admin**: 系统管理员，拥有所有权限
- **moderator**: 审核员，可以审核内容
- **user**: 普通用户，可以上传和查看内容

### 权限控制
- 文件上传：所有认证用户
- 内容审核：admin和moderator
- 用户管理：admin
- 数据统计：admin

## 📁 文件存储

### 上传文件结构
```
uploads/
├── knowledge/          # 知识库文件
│   └── {user_id}/      # 按用户ID分类
│       └── {kb_id}/    # 按知识库ID分类
└── persona/           # 人设卡文件
    └── {user_id}/     # 按用户ID分类
        └── {pc_id}/   # 按人设卡ID分类
```

### 数据存储
项目使用SQLite数据库存储所有数据，包括：
- 用户信息（users表）
- 知识库信息（knowledge_bases表）
- 人设卡信息（persona_cards表）
- 消息（messages表）
- Star记录（stars表）

数据库文件位于：`data/mainnp.db`

## 🔧 配置说明

### 环境变量配置
项目使用 `.env` 文件进行配置管理。首次使用时，请复制 `.env.template` 文件为 `.env` 并根据需要修改配置：

```bash
cp .env.template .env
```

#### 主要配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `ADMIN_USERNAME` | 管理员用户名 | STMfan |
| `ADMIN_PWD` | 管理员密码 | @Stickmanfans0805INMMNP |
| `HIGHEST_PASSWORD` | 最高权限密码 | 随机字符串 |
| `EXTERNAL_DOMAIN` | 外部域名 | maimnp.tech |
| `MAIL_HOST` | SMTP服务器地址 | smtp.qq.com |
| `MAIL_USER` | 发件邮箱地址 | 1710537557@qq.com |
| `MAIL_PORT` | SMTP服务器端口 | 465 |
| `MAIL_PWD` | 邮箱授权码/SMTP密码 | 授权码 |
| `PORT` | 服务器端口 | 9278 |
| `HOST` | 服务器主机 | 0.0.0.0 |
| `DATABASE_URL` | 数据库连接URL | sqlite:///data/mainnp.db |
| `JWT_SECRET_KEY` | JWT密钥 | 随机字符串 |
| `JWT_EXPIRATION_HOURS` | JWT过期时间(小时) | 24 |
| `MAX_FILE_SIZE_MB` | 最大文件上传大小(MB) | 100 |
| `UPLOAD_DIR` | 文件上传目录 | uploads |
| `LOG_LEVEL` | 日志级别 | INFO |
| `LOG_FILE` | 日志文件路径 | logs/app.log |

#### 邮箱配置说明
邮件服务支持多种邮箱提供商：

**QQ邮箱配置：**
- 需要在QQ邮箱设置中开启SMTP服务
- 获取授权码（不是QQ密码）
- 使用端口465（SSL）或587（TLS）

**其他邮箱配置：**
- Gmail: smtp.gmail.com, 端口587
- 163邮箱: smtp.163.com, 端口465
- Outlook: smtp-mail.outlook.com, 端口587

### 旧版配置（已弃用）
- 端口配置：默认9278
- 文件上传限制：可配置
- 数据存储路径：可配置

## 📝 开发说明

### 代码规范
- 使用Python类型注解
- 遵循PEP 8编码规范
- 添加必要的注释和文档

### 错误处理
- 统一的错误响应格式
- 详细的错误日志记录
- 友好的错误提示信息

### 安全性
- 密码使用bcrypt哈希
- JWT token认证
- 输入验证和过滤
- 文件上传安全检查

## 🐛 常见问题

### Q: 端口被占用怎么办？
A: 使用以下命令查看并终止占用进程：
```bash
netstat -ano | findstr :9278
taskkill /PID <PID> /F
```

### Q: API接口调用失败？
A: 请确保所有API请求都包含`/api`前缀，例如：
- 登录接口应为 `/api/token` 而不是 `/token`
- 人设卡接口应为 `/api/persona/public` 而不是 `/persona/public`

### Q: 如何添加新用户？
A: 通过API接口或修改users.json文件

### Q: 文件上传失败？
A: 检查uploads目录权限和磁盘空间

### Q: 如何修改默认端口？
A: 修改启动命令中的端口号参数

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交代码更改
4. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 项目Issues
- 邮箱联系

---

**注意**: 这是一个教育项目，请勿在生产环境中直接使用。如需生产部署，请考虑添加数据库、缓存、监控等生产级功能。
